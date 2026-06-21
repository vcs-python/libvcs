(adr-faithful-subprocess-output)=

# ADR 0001: Faithful subprocess output capture

## Status

Proposed. 2026-06-20.

## Context

The legacy command runner `libvcs._internal.run.run` — used by every
`Git`, `Hg`, and `Svn` command class via `.run()` — does not return what
the underlying VCS actually printed. After the process exits it splits
captured stdout into lines, calls `bytes.strip()` on each line, drops any
line that is empty after stripping, and rejoins with `\n` and no trailing
newline. stderr is treated the same way and then rejoined with no
separator at all.

That post-processing corrupts any output where whitespace is
significant:

- Leading indentation is removed from every line.
- Blank lines (including a unified-diff blank context line, which is a
  single space) are dropped.
- The trailing newline is removed.
- Multi-line error messages are concatenated word-against-word, because
  stderr lines are rejoined with an empty separator.

The user-visible consequence: a diff captured through `.run(["diff"])`
cannot be re-applied. `git apply` requires every patch line — including
the final one — to be newline-terminated, so a stripped diff is rejected
as `corrupt patch`. The same corruption silently damages `git show`,
`git cat-file blob` (file contents), `git format-patch`, and any
`--format` output that carries indentation or blank lines. Single-token
reads such as `rev-parse HEAD` are unaffected, which is why the defect
went unnoticed.

This is not a regression. The line-cleanup dates to the project's
original progress-callback code, where it was meant to tidy
human-readable progress lines, not to capture structured output. The
runner's own module docstring already states that it "will be deprecated
by `libvcs._internal.subprocess`".

`libvcs._internal.subprocess.SubprocessCommand` already exists as a thin,
typed wrapper that returns a real `subprocess.CompletedProcess` with
separate, untouched `stdout` and `stderr`. It is bytes-first with opt-in
text decoding, and it is currently wired into nothing.

## Decision

Subprocess output is captured pristine. Any trimming or decoding is a
deliberate transformation applied at the call site, never inside the
capture path. This is implemented in two phases so the stable
`.run() -> str` contract is never broken.

### Phase 1 — stop corrupting in the capture path

- Capture stdout and stderr as raw bytes and decode once, without
  per-line stripping or blank-line dropping. Interior whitespace, blank
  lines, and stream structure are preserved exactly.
- `.run()` returns the captured output **verbatim by default**, including
  the trailing newline, so whitespace-significant output (diffs destined
  for `git apply`, blob contents) round-trips byte-for-byte.
- Add a `trim=True` opt-in that applies a single **whole-output**
  `rstrip()` for the convenient "bare value" reads where a trailing
  newline is just noise (e.g. `rev-parse HEAD`). Trimming is a deliberate
  caller choice, never the capture default.
- Preserve stderr's line structure for error messages, and decode it
  tolerantly: the UTF-8 fallback uses `errors="backslashreplace"`, so an
  undecodable byte surfaces as an escape sequence in
  `libvcs.exc.CommandError.output` instead of raising `UnicodeDecodeError`.

### Phase 2 — pristine structured backend

- Route the `cmd/*` classes through
  `libvcs._internal.subprocess.SubprocessCommand`, which returns a
  `subprocess.CompletedProcess` (bytes-first, separate
  stdout/stderr/returncode).
- Expose a structured accessor that returns the `CompletedProcess` for
  callers that want streams, exit code, and exact bytes. Keep
  `.run() -> str` (verbatim by default, `trim=True` opt-in) as the
  convenience facade over it.
- Retire `libvcs._internal.run.console_to_str` in favor of subprocess's
  own decoding with `errors="backslashreplace"`.
- Let the legacy `libvcs._internal.run.run` deprecate, as its docstring
  already anticipates.

## Alternatives considered

Each candidate was measured against the test suite and a probe checking
whether a captured diff survives `git apply` and whether `cat-file blob`
is byte-identical.

| Approach | diff applies | blob identical | `rev-parse` bare | errors intact | tests failing |
|----------|:------------:|:--------------:|:----------------:|:-------------:|:-------------:|
| Per-line `strip` + drop-blanks (original) | no | no | yes | no | baseline |
| Whole-output `rstrip` default | no | no | yes | yes | 1 |
| Verbatim default + `trim=True` opt-in (chosen, Phase 1) | yes | yes | opt-in | yes | doctests only |
| Structured `CompletedProcess` (Phase 2) | yes | yes | edge decides | yes | 0 (via facade) |

The decisive measurement: flipping the default to verbatim broke only
doctests in `cmd/git.py`, `cmd/hg.py`, and `cmd/svn.py` — example output
that gained a trailing newline. No functional test, sync-layer call, or
downstream consumer broke, because those already strip where they need a
bare value (`vcspull`, like the sync layer, trims defensively). A global
trailing trim, by contrast, cannot produce an applyable patch: the
patch's required final newline is exactly what it strips. So verbatim
becomes the default — fixing the original `git apply` failure for the
plain `.run(["diff"])` call — and trimming is an explicit `trim=True`
opt-in for bare-value reads.

Every affected doctest was updated to show the real verbatim output. The
`Svn.blame` doctest is a notable case: its original expected value had
encoded the old bug (column-padding spaces already stripped), so it now
reflects the true, faithful output.

## Consequences

### Positive

- Captured diffs and patches re-apply by default; blob reads are
  byte-identical; error messages keep their line structure.
- The default now returns output with its trailing newline. Callers that
  want a bare value pass `trim=True`; existing consumers are unaffected
  because the sync layer and `vcspull` already strip defensively before
  comparing.
- The stderr concatenation defect is removed: error lines keep their
  separators. (Phase 2's structured backend additionally avoids the
  pipe-buffer deadlock the legacy poll loop can hit when a child floods
  stdout.)

### Tradeoffs

- Callers that relied on the implicit trailing-newline trim must now pass
  `trim=True` (or strip themselves) for bare-value reads.
- Phase 2 introduces a second return shape (`CompletedProcess`) alongside
  the string facade, and migrates the command classes onto a new backend.

### Risks

- Behavior drift between the `.run()` facade and the structured result.
  Mitigation: the facade decodes the structured result's stdout (verbatim
  by default; `trim=True` applies `rstrip`), not a separate code path.
- Encoding surprises on non-UTF-8 output. Mitigation: strict decode for
  data with a documented `backslashreplace` fallback for diagnostics,
  following the channel-split used by the tools surveyed below.

## Prior art

The decision follows the convergent practice of mature VCS and
subprocess-wrapping tools, none of which trim inside the capture path:

- **pip** added a per-call mode (`stdout_only`) that returns VCS output
  verbatim, and replaced its `console_to_str` helper with
  `errors="backslashreplace"`.
- **uv** captures into a raw `Output { stdout, stderr }` and applies
  `trim_end()` at each call site for scalar reads.
- **mise** relies on whole-output trailing trim for scalars, decodes
  strictly for data and lossily for stderr.
- **Mercurial**, **gitoxide**, and **Jujutsu** are bytes-first and keep
  output verbatim; gitoxide treats newline-stripping as a named, opt-in
  view, and tracks the missing-final-newline case explicitly.
- **git** itself confirms the constraint: its patch parser requires each
  line, including the last, to be newline-terminated.

The lesson shared by all of them: capture pristine, keep streams
separate, and make trimming and decoding explicit edge transformations.
`SubprocessCommand` already embodies that shape inside libvcs.
