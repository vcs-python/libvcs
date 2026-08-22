# Writing

How libvcs writes prose, for humans and agents alike. It governs `README.md`,
`CHANGES`, docstrings, source comments, Markdown under `docs/`, and commit
messages — every surface a reader reaches.

For environment setup, the gates, and pull request workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Voice

Three surfaces, one voice. A docstring says what a caller may rely on; a
`CHANGES` entry says what changed; prose says what happens. All three are
present tense, lead with the thing being described, and stop. Why it was built
that way belongs in the commit message, which is timestamped and attached to
the diff.

The most useful editing operation is deleting the introductory sentence.

Lead with verbs and name concrete things. Put identifiers in backticks. Prefer
short declarative sentences, one operational fact each. Do not explain Python
to Python developers; do explain libvcs's semantics.

Type annotations describe shape. Documentation describes meaning. A sentence
that restates a signature has said nothing.

Use MUST, SHOULD, and MAY only where the normative sense is meant. Say what
actually happens rather than that something is "supported".

| Instead of                       | Prefer                             |
| --------------------------------- | ---------------------------------- |
| "We added…"                      | "`GitSync.update_repo` now accepts…" |
| "New and improved"               | "`Git.fetch` now…"                 |
| "powerful", "seamless"           | state the capability               |
| "easily", "simply", "just"       | omit                               |
| "simple", "obvious", "intuitive" | omit                               |
| "robust"                         | name the failure that is handled   |
| "comprehensive"                  | name what is covered               |
| "production-ready"               | state the guarantee                |
| "optimized", "blazingly fast"    | give the magnitude                 |
| "various fixes"                  | name the components                |
| "under the hood"                 | omit unless observable             |
| "please note that", "note that"  | state the fact                     |
| "leverage", "utilize"            | "use"                              |
| "delve into"                     | "read", or omit                    |
| "best practices"                 | name the practice                  |
| "in order to"                    | "to"                               |

## Who you are writing for

The default reader writes Python and works with repositories through libvcs's
objects — `GitURL`, `Git`, `GitSync`, and their hg and svn counterparts. They
are fluent in their version control system — clones, remotes, branches,
revisions, checkouts — and comfortable in Python, but you cannot assume they
know libvcs's internals: `QueryList` filtering, the subprocess wrapper under
`_internal`, the URL rule registry, or the pytest plugin's fixture machinery.

A second, smaller reader works *on* libvcs or against its lower layers: custom
URL rules, sync subclasses, tools built on top like vcspull, or contributing.
Serve them too, but mark their material opt-in — "for the rarer cases",
"advanced" — so the default reader knows they can stop. Never make the common
case pay a comprehension tax for the advanced one.

Rules that follow:

- **Second person, present tense, active.** "You parse the URL", not "The URL
  is parsed". Address the reader who is doing the thing.
- **Concept before API surface.** Open by saying what the object or method
  *is* and what it does for the reader. The signature — the parameters, the
  flags — is the last detail they need, not the first. A page that opens with
  a method signature has buried the idea under its mechanics.
- **Say when they can stop.** Lead with the default and the reassurance: most
  readers never reach for the advanced parts, the defaults work. Let a
  skimmer leave after one paragraph.
- **Grant permission, do not demand attention.** "Reach for this when…" tells
  readers they are in the right place without implying they must read on.
- **Progressive disclosure.** Order by how many readers need it: the common
  call, then the one argument a few will tune, then the lower-level
  primitive — running the VCS binary directly via `run()` — last. Each step
  is for a smaller audience than the last.
- **Lean on the layers.** The reader thinks in libvcs's three-module split:
  `libvcs.url` detects and parses, `libvcs.cmd` wraps the git, hg, and svn
  binaries, and `libvcs.sync` manages whole checkouts on top of `cmd`.
  Reinforce that split when explaining where a feature lives or which layer
  the reader should reach for.
- **Name the trade-off.** If a call costs something — a fresh subprocess per
  command, a network round-trip on `obtain()` — say so, and say what it buys
  ("never stale, but each call pays the spawn"). State it; do not sell it.
- **Frame by concept, not by mechanism.** Do not headline a feature by its
  git flag or matcher pattern in prose; that names the implementation
  surface, which is the reader's last concern. Name the concept. The
  mechanics vocabulary — a parameter table, a `--force` flag, a regex
  pattern — belongs in a reference table or the API docs, and only there.

## README

A README is the shortest path from "what is this?" to competent use, not the
project's autobiography.

The first sentence is a contract. It says what abstraction the reader has
been handed, concretely enough to tell libvcs apart from the neighbouring
package.

Get to a runnable command or snippet before anything the reader can skip. A
logo, a mission statement, a comparison matrix and three paragraphs of
history in front of the install line all cost the same thing.

State the minimum Python version and meaningful platform constraints in
prose, not only in badges. `requires-python` in `pyproject.toml` is the
authority; the README must agree with it.

Examples are executable, not illustrative fiction. Never
`your-command <some-options>`. See
[Documented examples that run](#documented-examples-that-run) for which
blocks are executed and how to write one that qualifies.

Document the semantic model, not the flag list. Say what a sync call returns,
what an `obtain()` does on a repository that already exists, and what a
failed sync looks like — that is what a signature cannot say.

State defaults explicitly — defaults are API. State negative guarantees
where they exist: "does not modify your configuration file", "no network
access", "never writes outside the destination". They establish boundaries
faster than any amount of description.

Headings stay conventional and stable, because people deep-link them. Badges
are few and load-bearing.

## Documented examples that run

Examples in libvcs are tests. This section is the contract for writing one
the test suite can actually see, and it describes libvcs's real mechanism —
read it before touching any fenced code block.

**A fence tag is cosmetic. Only a `>>> ` prompt executes.** A block written as

    ```python
    server = Git(path=".")
    ```

is prose that looks like a test. Nothing collects it, nothing runs it, and it
can be wrong for years. The same block written with prompts is a test:

    ```python
    >>> server = Git(path=".")
    ```

This is the single most expensive mistake available when editing
documentation, because removing the prompts leaves a green test suite and a
silently deleted test. When editing a file that contains examples, count the
prompts before and after.

**The fence tag is `python`.** Not `pycon`, not bare.

**Where examples run.** `pyproject.toml`'s `[tool.pytest.ini_options]` sets
`addopts = ["--doctest-docutils-modules", "-p no:doctest", ...]` and
`testpaths = ["src/libvcs", "tests", "docs", "README.md"]`. That combination
means:

- Every docstring `Examples` block under `src/libvcs/` runs.
- Every `>>> ` block in a Markdown or reStructuredText file under `docs/`
  runs, because `--doctest-docutils-modules` collects docutils sources, not
  only Python modules.
- `README.md` is itself in `testpaths`, so a `>>> ` block there would run
  too — the current README has none; if you add one, it becomes a test.
- `doctest_optionflags = ["ELLIPSIS", "NORMALIZE_WHITESPACE"]` is set
  globally, so `...` elides variable output and whitespace differences do
  not fail a comparison. Reach for an inline `# doctest: +FLAG` only for the
  block that needs something beyond that.

**Fixtures available inside a doctest.** The root `conftest.py` requests
`add_doctest_fixtures` for every collected doctest item, and
`src/libvcs/pytest_plugin.py` populates `doctest_namespace` from it. A block
may use these names without importing or constructing them:

- `tmp_path` — always available.
- `example_git_repo` and `create_git_remote_repo` (plus
  `create_git_remote_repo_bare`) — only when `git` is on `PATH`.
- `create_svn_remote_repo` (plus `create_svn_remote_repo_bare`) — only when
  both `svn` and `svnadmin` are on `PATH`.
- `create_hg_remote_repo` (plus `create_hg_remote_repo_bare`) — only when
  `hg` is on `PATH`.

Each VCS's helpers appear only when its binary is present, so an example
using `create_hg_remote_repo` is silently absent from the namespace on a
machine without Mercurial rather than failing every other VCS's examples.
Write one example per VCS instead of branching inside a block. The full
fixture reference — including the non-doctest fixtures like `git_repo`,
`svn_repo`, and `hg_repo` — is at
[the pytest plugin API page](https://libvcs.git-pull.com/api/pytest-plugin/).

**`# doctest: +SKIP` is not permitted.** It is a workaround that tests
nothing. If a VCS binary might be missing, the fixtures above already handle
it — an example that needs `hg` and finds `create_hg_remote_repo` absent from
the namespace fails loudly, which is the signal to gate the example on the
right fixture, not to skip it.

**Do not downgrade a doctest to a non-executed block to make it pass.** A
`` ```{eval-rst}`` block, a `.. code-block::`, or an unprompted fence does not
run. If an example cannot pass, fix the example or fix the code.

**Docstring examples** use the NumPy `Examples` section:

    Examples
    --------
    >>> git = Git(path=tmp_path)
    >>> git.get_git_version()  # doctest: +ELLIPSIS
    '...'

**Room to grow.** The docutils collector reads `.md` and `.rst` whenever it
is loaded, which is everywhere in this repository. A prompted block added to
a documentation page is executed from that moment with no configuration
change. Other formats the collector supports — the MyST `{doctest}`
directive and the reStructuredText `.. doctest::` directive — are available
if a case ever needs an explicitly marked block.

## MyST roles and cross-references

Any class, method, function, exception, or attribute that has its own
rendered API page must be cited with the matching role — `{class}`, `{meth}`,
`{func}`, `{exc}`, `{attr}` — never with plain backticks. A documentation
page without an explicit ref label uses `{doc}`; an anchor inside a page uses
`{ref}`. Plain backticks are correct for code syntax, environment variables,
parameter names, and file paths that are not doc pages — anything without an
autodoc destination.

A `{ref}` target must match its anchor exactly — anchors mix underscore and
hyphen forms across pages (`pytest_plugin`, `url-parsing`).

Link the first prose mention of any symbol that has a useful destination on
that page. Use the most specific target available. After the first linked
mention on a page, later mentions can stay plain unless distance or context
makes another link useful. Do not rely on a later reference section to
satisfy the first-mention rule: if the first occurrence would be a heading, a
grid-card teaser, or an introductory sentence, link that occurrence or
retitle the heading so the first prose mention can carry the link. Leave
code blocks and literal configuration values as code; link the surrounding
prose instead.

`just build-docs` catches a broken cross-reference; the doctests do not — so
build the docs before committing a page that adds or moves one.

## What stays precise

Warm the framing, never the facts. Resolution-order lists, value tables,
exact error strings, matcher patterns, and class or method cross-references
carry meaning in their exact form — leave them alone. The friendly voice
belongs in the sentences *around* a precise block, introducing it, not
inside it paraphrasing it into vagueness.

`docs/topics/traversing_git.md` is the worked example: a concept-first intro
that says what Managers and Commands *are* before any signature, a runnable
example first, sections ordered by shrinking audience, and the reference
tables left exact with `{class}` cross-references. Read it before reshaping
another page.

## The changelog

`CHANGES` is the changelog, rendered as the Sphinx changelog page. It is
modeled on Django's release-notes shape — deliverables get titles and prose,
not bullets.

A ledger, not a narrative. It is scanned, and the question a reader is
asking is whether an entry affects them.

**Release entry boilerplate.** Every release header is
`## libvcs X.Y.Z (YYYY-MM-DD)`. The file opens with a
`## libvcs X.Y.Z (unreleased)` placeholder block fenced by
`<!-- KEEP THIS PLACEHOLDER ... -->` and `<!-- END PLACEHOLDER ... -->` HTML
comments — new release entries land immediately below the END marker, never
above it.

**Open with a multi-sentence lead paragraph.** Plain prose, no italic. Open
with the version as sentence subject ("libvcs X.Y.Z ships …") so the lead is
self-contained when excerpted. Two to four sentences telling the reader what
shipped and who cares — user-visible takeaways, not internal mechanism.
Cross-reference detail docs with `{ref}` to keep the lead compact.

**Lead paragraphs are release-time material — off-limits to branches and
pull requests.** The unreleased entry carries no lead paragraph and no
version summary: sections only. Speaking for the release — what the version
"is", "ships", or "focuses on" — is presumptuous before its scope is final;
only the person cutting the release writes that. Never write or edit a lead
paragraph from a feature branch, and never ask or imply that a release
should happen.

**Each deliverable is a section, not a bullet.** Inside `### What's new`,
every distinct deliverable gets a `#### Deliverable title (#NN)` heading
naming it in user vocabulary, followed by one to three prose paragraphs
explaining what shipped. Do not wrap a paragraph in `- ` — bullets are for
enumerable lists, not paragraph containers. Cross-link detail docs
("See {ref}\`foo\` for details.") so prose stays focused.

**The deliverable test.** Before writing an entry, ask: "What's the
deliverable, in user vocabulary?" If you cannot answer in one sentence, the
entry is not ready. Mechanism — helper internals, byte counters, schema
validation locations — belongs in pull request descriptions and code
comments, not the changelog.

**Fixed subheadings**, in this order when present: `### Breaking changes`,
`### Dependencies`, `### What's new`, `### Fixes`, `### Documentation`,
`### Development`. Dev tooling (helper scripts, internal automation) lives
under `### Development`. For breaking changes, show the migration path with
concrete inline code (a `# Before` / `# After` fenced code block).
Dependency floor bumps use the form
``Minimum `pkg>=X.Y.Z` (was `>=X.Y.W`)``.

**PR refs `(#NN)`** sit in each deliverable's `####` heading.

**When bullets are appropriate.** Catch-all sections (`### Fixes`,
occasionally `### Documentation`) with three or more genuinely small items
use bullets — one line each, never paragraphs. If a bullet swells past two
lines, promote it to a `#### Title (#NN)` heading with a prose body.

**Anti-patterns.** Fragile metrics that go stale silently — token ceilings,
third-party version pins, percent benchmarks, exact byte counts. Describe
the capability, not the math. Private symbols and internal jargon
(leading-underscore identifiers, algorithm names exposed for the first
time). Walls of text dressed up as bullets. Breaking changes buried mid-entry
instead of given their own subheading at the top.

## Docstrings

The prime directive: never restate the type. The annotation is the source of
truth; the docstring carries what the annotation cannot.

All public functions and methods use **NumPy-style** docstrings, enforced by
`ruff`'s `pydocstyle` (`convention = "numpy"`):

```python
"""Short description of the function or class.

Detailed description using reStructuredText format.

Parameters
----------
param1 : type
    Description of param1
param2 : type
    Description of param2

Returns
-------
type
    Description of return value
"""
```

**Classes with fields** — `NamedTuple`, dataclasses — document every field
in an `Attributes` section:

```python
class VCSLocation(t.NamedTuple):
    """Generic VCS Location (URL and optional revision).

    Attributes
    ----------
    url : str
        Repository URL, with any revision suffix stripped.
    rev : str | None
        Revision to check out, or ``None`` when unspecified.
    """
```

Autodoc renders every field whether or not you describe it, so an
undocumented `NamedTuple` field ships to the API docs as "Alias for field
number 0" and a dataclass field ships bare. Document all of them — a class
with three fields and two documented still ships a stub for the third.

Document instead the dimensions the type system cannot encode: mutation,
ownership, ordering, timing, failure, idempotence, concurrency, units and
ranges, boundary behaviour, platform differences, and security boundary
(what is executed versus only read). The ambiguity worth resolving by
example: whether "retry three times" means three attempts or four. State it.

The first sentence stands alone; tooling truncates there. PEP 257 applies:
triple double quotes, an imperative one-line summary ending in a period, a
blank line before any extended description. Do not repeat an introspectable
signature.

`Parameters`, `Returns`, and `Attributes` entries are exempt from the loss
gate in [Source comments](#source-comments) below — see the documentation
exception there.

## Source comments

A comment ships only if it passes all three gates. Fail any: delete or
rewrite. Borderline: delete — borderline means the information is
reconstructible, which is what makes deletion cheap.

**Loss.** Three years from now, would losing this cost a maintainer real
time rediscovering intent, an invariant, a constraint, or a failure mode the
code and tests do not already make obvious?

**Elite.** Would SQLite, Redis, the Go standard library, or CPython write
this comment, at this length? Those projects state the constraint and stop.
They do not argue with an imagined objector.

**Upkeep.** Will it stay true without maintenance? A comment that hand-syncs
a value the code owns — a count, an offset, a line reference, a duplicated
constant — is false the first time that value moves.

### Ceiling

One or two lines. A comment reaching four is either carrying several facts,
in which case split it, or arguing, in which case cut it to the fact.

Rationale, alternatives weighed, and the story of how the code got here
belong in the commit message: timestamped, attached to the exact diff, and
free to maintain.

A comment often holds both a constraint and the deliberation that found it.
Keep the constraint, cut the deliberation. "Runs at most once per second"
survives; "this is the right trade for now" does not.

### Keep

- Why over how: upstream quirks, protocol and compatibility constraints,
  performance tradeoffs still part of the contract.
- Invariants, preconditions, ordering, lifetime, and concurrency
  requirements that types and tests cannot express.
- Code that looks wrong but is not, so a later cleanup does not reintroduce
  the bug.
- A high-level sketch of an algorithm whose local operations do not reveal
  the whole.

### Delete

- Narration of the next lines; code translated into English.
- Restated names, types, defaults, or control flow.
- Values duplicated from the code and hand-synced.
- Justification, hedging, or apology for a choice.
- Speculation about future requirements.
- History version control already holds, including commented-out code.
- Ticket and issue numbers. They say nothing to a reader without tracker
  access, and they rot when the tracker moves. Unfinished work goes in the
  tracker, not the source.
- Transient observations — "currently", "for now", "the latest release" —
  that go stale with no nearby edit.

### The upkeep gate in practice

It reaches values that track our own code. It does not reach frozen external
facts.

Bad (Delete):

```python
# There are 321 tests to complete for servers.
```

Good (Keep):

```python
# `SvnSync.url_rev` scrapes `svn info --xml`, so whether it yields a URL
# depends on the installed svn and the working copy layout.
```

### Documentation exception

Doctests, minimal usage examples, and `Parameters`, `Returns`, and `Raises`
entries on public API are exempt from the loss gate — they serve the caller,
not the maintainer. They are exempt from nothing else. Ceiling: a good man
page entry. NumPy-style `Parameters`, `Returns`, and `Attributes` sections
fall under this exception for the same reason autodoc ships every field
whether or not you describe it, and a doctest that runs is also a test.

## Terminology and capitalization

Pick the domain noun and keep it. If the code calls something a remote, do
not call it an origin in one paragraph and a mirror in the next. If the
method is `obtain()`, write "obtain" everywhere rather than alternating with
"clone", "fetch", and "sync" — those are separate operations elsewhere in
the API.

Stable vocabulary is what makes search, deep links, and an agent's retrieval
work at all.

Python and PyPI keep their own capitalisation. Distribution names are
written as they are published.

Do not write counts into prose — how many symbols exist, how many tests
there are. They go stale silently and no reader needs them. Counts that pin
a fixture or guard an invariant are different, and belong in code.

## Markdown

Prose wraps at 80 columns. Table rows, badge lines, and long links are
exempt, because breaking them harms rendering. A pull request or issue body
does not wrap at all: GitHub renders a single newline as a space in a file
and as a line break in a comment, so a wrapped comment body arrives as
ragged stubs.

GitHub alert blocks — `> [!NOTE]`, `> [!WARNING]` — render as literal text
outside GitHub, so reserve them for at most one load-bearing warning per
document. Write the sentence so it carries the fact on its own, and a
renderer that drops the marker loses nothing.

Do not use a local absolute path or an email address in anything published.

## Code blocks

Code blocks are paste-and-run units: pasting one block runs exactly one
intended action. Doctests and other executed examples are exempt — the test
suite runs them, nobody pastes them.

- **One command per block.** Multiple steps may share a block only when
  explicitly chained with `&&`, `;`, or `\` continuations — the chain is
  then one logical command.
- **Explanations go in prose above the block**, never as `#` comments
  inside it.
- **Command menus are per-command blocks with prose lead-ins**, not tables.
- **Shell commands use the `console` tag with a `$ ` prefix.** This
  separates interactive commands from scripts and enables prompt-aware copy.
- **Split long commands with `\`** — one flag or flag+value pair per
  indented continuation line, positional arguments last.

Good — show the last ten commits as a graph:

```console
$ git log \
    --max-count=10 \
    --graph \
    --oneline
```

Bad:

```console
# Show the last ten commits as a graph
$ git log --max-count=10 --graph --oneline
```

## Commits

```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

Keep the subject to 50 characters or fewer, excluding any trailing `(#NN)`
pull request reference, and wrap body lines at 72. Separate the `why:` and
`what:` blocks with a blank line.

Routine maintenance commits drop the colon and take a capitalised
description, which is what distinguishes them at a glance in
`git log --oneline`:

```
py(deps[dev]) Bump dev packages
ai(rules[AGENTS]) Judge comments by three gates
```

Everything that changes behaviour keeps the colon.

Common types:

- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **ci**: Workflow and pipeline changes
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev dependencies
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (`CLAUDE.md`)
- **ai(claude[command])**: Claude Code command changes

Example:

```
url/git(feat[GitURL]): Add support for custom SSH port syntax

why: Enable parsing of Git URLs with custom SSH ports

what:
- Add port capture to SCP_REGEX pattern
- Update GitURL.to_url() to include port if specified
- Add tests for the new functionality
```

For a multi-line message, use a heredoc so the formatting survives:

```console
$ git commit -m "$(cat <<'EOF'
Scope(feat[detail]): Concise description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

### Release commits

Never create tags. Never push tags. The owner handles tagging and tag
pushes, because a tag triggers the publish workflow.

A release commit subject is plain and short: `Tag v<version>`. The detailed
why and what go in the body. Do not use the `Scope(type[detail]):` format
for a release — it buries the lede.

## Slop prevention

Treat AI slop as review-hostile noise, not as proof that text or code is
wrong. The goal is to maximise information density.

- **AI signatures.** No "Generated by", no conversational filler, no
  unexplained emoji, no tool metadata.
- **Brittle references.** No hard-coded line numbers, fragile file or test
  counts, dated "as of" claims, bare SHAs, or local absolute paths — unless
  they are strict evidentiary artefacts such as a benchmark log.
- **Diff narration.** Do not restate what moved, was renamed, or was
  removed in anything the reader holds alongside the diff: code, docstrings,
  README, `CHANGES`, or a pull request description. The diff and commit
  message already carry it.
- **Branch-internal narrative.** Do not mention intermediate states,
  abandoned approaches, or "no longer" behaviour unless users of a
  published release actually experienced the old state (the
  published-release test below).
- **Low-value scaffolding.** No ownerless TODOs, unused future-proofing,
  debug artefacts, or defensive wrappers around failure modes nothing can
  reach.
- **Prose inflation.** The diction table under [Voice](#voice) governs;
  replace an inflated word with a concrete description of behaviour,
  constraints, or trade-offs.
- **Coded labels.** Write rules and findings as plain imperatives. No
  `[R1]`, `Option B`, or any index a reader has to decode in shipped text.

Preserve the "why". Never delete a comment documenting an invariant, a
protocol constraint, a platform quirk, or an upstream workaround — those are
the facts [Source comments](#source-comments) keeps, and every other comment
is judged by it.

### Durable source links

Link to a pinned revision, never to trunk. A pinned permalink is not a
brittle reference; an unlinked SHA dropped into prose is. `blob/master/…`
links rot silently — the file moves, lines shift, and the anchor lands on
unrelated code while still resolving.

- Prefer a release tag (`blob/v0.45.1/…`). Most durable, and it tells the
  reader which released version the claim held for.
- Otherwise use a 7-character commit ref (`blob/9a29b1a/…`) reachable from
  trunk. Use when there is no tag or the claim is about unreleased code.
  Never a pull-request-head SHA — it can be rebased or garbage-collected.
- Reserve `blob/master/…` for living documents meant to always show the
  latest state, such as a contributing guide.
- Line anchors (`#L120-L145`) are only safe on a pinned ref.

### The published-release test

Long-running branches accumulate tactical decisions — renames, refactors,
attempts then reverts. When deciding what counts as branch-internal, use
trunk or the parent branch as the baseline, not intermediate states inside
the current branch. Ask: did users of the most recently published release
ever experience this old name, old behaviour, or bug? If the answer is no,
it is branch-internal narrative — it belongs in the commit message, not the
artefact.

Keep in shipped artefacts: deprecations and migration guides for symbols
that actually shipped; `### Fixes` entries for bugs that affected users of a
published release; comments explaining why the current code looks this way
that make sense to a reader who never saw the previous version.
