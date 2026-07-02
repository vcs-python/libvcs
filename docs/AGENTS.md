# Documentation voice

This file covers the *voice* of prose under `docs/` — how to frame a
page so a reader meets the idea before its API surface. It complements
the repository-root `AGENTS.md`, which already governs code blocks,
shell-command formatting, doctests, changelog conventions, and MyST
roles. When the two overlap, the root file wins; this one only answers
the question it leaves open: how should the prose sound?

## Who you are writing for

The default reader writes Python and works with repositories through
libvcs's objects — `GitURL`, `Git`, `GitSync`, and their hg and svn
counterparts. They are fluent in their version control system —
clones, remotes, branches, revisions, checkouts — and comfortable in
Python, but you cannot assume they know libvcs's internals:
`QueryList` filtering, the subprocess wrapper under `_internal`, the
URL rule registry, or the pytest plugin's fixture machinery.

A second, smaller reader works *on* libvcs or against its lower
layers: custom URL rules, sync subclasses, tools built on top like
vcspull, or contributing. Serve them too, but mark their material
opt-in ("for the rarer cases", "advanced") so the default reader
knows they can stop. Never make the common case pay a comprehension
tax for the advanced one.

## Voice

- **Second person, present tense, active.** "You parse the URL", not
  "The URL is parsed". Address the reader who is doing the thing.
- **Concept before API surface.** Open by saying what the object or
  method *is* and what it does for the reader. The signature — the
  parameters, the flags — is the last detail they need, not the
  first. A page that opens with a method signature has buried the
  idea under its mechanics.
- **Say when they can stop.** Lead with the default and the
  reassurance: most readers never reach for this, the defaults work,
  the advanced parts are optional. Let a skimmer leave after one paragraph.
- **Grant permission, don't demand attention.** "Reach for this
  when…", "for the rarer cases" — tell readers they're in the right
  place without implying they must read on.
- **Progressive disclosure.** Order by how many readers need it: the
  common call → the one argument a few will tune → the lower-level
  primitive → running the VCS binary directly via `run()`. Each step
  is for a smaller audience than the last.
- **Lean on the layers.** The reader thinks in libvcs's three-module
  split: `libvcs.url` detects and parses, `libvcs.cmd` wraps the git,
  hg, and svn binaries, and `libvcs.sync` manages whole checkouts on
  top of `cmd`. Reinforce that split when you explain where a feature
  lives or which layer the reader should reach for.
- **Name the trade-off.** If a call costs something — a fresh
  subprocess per command, a network round-trip on `obtain()` — say
  so, and say what it buys ("never stale, but each call pays the
  spawn"). State it; don't sell it.
- **Frame by concept, not by mechanism.** Don't headline a feature by
  its git flag or matcher pattern in prose; that names the
  implementation surface, which is the reader's last concern. Name
  the concept. The mechanics vocabulary — a parameter table, a
  `--force` flag, a regex pattern — belongs in a reference table or
  the API docs, and only there.

## Examples that run

Prose examples under `docs/` are doctests, and the root `AGENTS.md`
requires them to actually execute — `testpaths` includes `docs/` (and
`README.md`), so pytest runs every fenced `>>>` block. Lead with a
small, runnable example early rather than after paragraphs of prose;
libvcs is code-first.

- Use the `doctest_namespace` fixtures — `tmp_path`,
  `example_git_repo`, `create_git_remote_repo`,
  `create_hg_remote_repo`, `create_svn_remote_repo` (each with a
  `_bare` variant) — instead of building repositories by hand. A
  VCS's fixtures only appear when its binary is installed.
- Fence a `>>>` session as a ```` ```python ```` block, and reach for
  `# doctest: +ELLIPSIS` when output varies (clone messages, tmp
  paths). Use a ```` ```console ```` block for shell commands at a
  `$` prompt.
- Keep each code block self-contained — re-import and re-create
  objects (`git = Git(path=example_git_repo.path)`) rather than rely
  on state from an earlier block; every existing page does.

## What stays precise

Warm the framing, never the facts. Resolution-order lists, value
tables, exact error strings, matcher patterns, and class or method
cross-references carry meaning in their exact form — leave them
alone. The friendly voice belongs in the sentences *around* a precise
block, introducing it, not inside it paraphrasing it into vagueness.

## Cross-references

Point the advanced reader at the deep-dive rather than inlining it,
and put the link where their interest peaks — on the phrase that made
them curious ("write your own URL rule", "run git directly") — not as
a standalone footnote the eye skips. Use the MyST roles listed in the
root `AGENTS.md` (`{class}`, `{meth}`, `{func}`, `{exc}`, `{attr}`,
`{ref}`, `{doc}`). A `{ref}` must match its target's anchor exactly —
anchors mix underscore and hyphen forms across pages
(`pytest_plugin`, `url-parsing`). `just build-docs` catches a broken
cross-reference; the doctests do not — so build the docs before you
commit.

Link the first prose mention of any symbol that has a useful
destination on that page. This includes Python objects, libvcs APIs,
topic pages, and external tools or projects. Use the most specific
target available: `{class}`, `{meth}`, `{func}`, `{mod}`, `{exc}`, or
`{attr}` for API objects; `{ref}` or `{doc}` for documentation pages
and section anchors; and a Markdown link or reference link for
external projects. After the first linked mention on a page, later
mentions can stay plain unless the distance or context makes another
link useful.

Do not rely on a later reference section to satisfy the first-mention
rule. If the first occurrence would be a heading, grid-card teaser,
or introductory sentence, link that occurrence or retitle the heading
so the first prose mention can carry the link. Leave command
examples, code blocks, and literal configuration values as code; link
the surrounding prose instead.

## A page that does this

`docs/topics/traversing_git.md` is the worked example: a concept-first
intro that says what Managers and Commands *are* before any signature,
the manager tree laid out up front, a runnable example first, sections
ordered by shrinking audience, an honest before/after against parsing
raw `git` output, and the "When to Use" and manager reference tables
left exact, with `{class}` cross-references. Read it before reshaping
another page.

## Before you commit

- Does the page open with what the feature *is*, or how to call it?
- Can a reader who needs only the common case stop after the first
  paragraph?
- Is anything framed by its git flag or matcher pattern that should
  be named by concept instead?
- Are the advanced and lower-level parts clearly marked opt-in?
- Do the doctests run (`just test`), and did you leave every code
  block, table, error string, and cross-reference exact?
- Did `just build-docs` stay clean — no new warning, no broken
  cross-reference?
