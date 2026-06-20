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
- `.run()` keeps returning a convenience string. By default it applies a
  single **whole-output** `rstrip()` (trailing whitespace only),
  matching the established "bare value" behavior callers already rely on
  for reads like `rev-parse HEAD`.
- Add an opt-in for verbatim output (e.g. `trim=False`) so callers that
  need byte-accurate output — diffs destined for `git apply`, blob
  contents — get exactly what the VCS produced, trailing newline
  included.
- Decode stderr for error messages with `errors="backslashreplace"` and
  preserve its line structure, so `libvcs.exc.CommandError.output` is
  readable and never hides an undecodable byte.

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
| Per-line `strip` + drop-blanks (current) | no | no | yes | no | baseline |
| Verbatim string everywhere | yes | yes | no (`+\n`) | yes | 77 |
| Whole-output `rstrip` | no | no | yes | yes | 1 |
| Per-call `trim` flag (chosen, Phase 1) | yes (opt-in) | yes (opt-in) | yes (default) | yes | 1 |
| Structured `CompletedProcess` (chosen, Phase 2) | yes | yes | edge decides | yes | 0 (via facade) |

Two results are decisive. Returning fully verbatim output as the default
fixes fidelity but breaks 77 tests, because the project's own doctests
and downstream consumers expect `.run()` to return a value with no
trailing newline. A global trailing trim keeps that contract but cannot
produce an applyable patch, since the patch's required final newline is
exactly what gets trimmed. Only a per-call choice satisfies both, and a
structured result removes the choice from the runner entirely by handing
the caller pristine bytes plus separate streams.

The single failing test under the chosen approaches is a `Svn.blame`
doctest whose expected value had encoded the bug (column-padding spaces
already stripped). It is corrected to expect the faithful output.

## Consequences

### Positive

- Captured diffs and patches re-apply; blob reads are byte-identical;
  error messages keep their line structure.
- The default `.run()` contract (no trailing newline) is preserved, so
  existing callers and the downstream `vcspull`, which strips defensively
  before comparing, are unaffected.
- Two latent defects are removed: stderr lines are no longer concatenated
  without a separator, and routing through `subprocess.run` avoids the
  pipe-buffer deadlock the legacy poll loop can hit when a child floods
  stdout.

### Tradeoffs

- Callers that need pristine output must opt in (Phase 1) or use the
  structured accessor (Phase 2); the convenience default still trims.
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
