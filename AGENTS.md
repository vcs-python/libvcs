# AGENTS.md

libvcs is a typed Python library that detects and parses Git, Mercurial, and
Subversion URLs, wraps their command-line tools, and synchronizes local
checkouts against a remote — plus a pytest plugin for testing against real,
disposable VCS repositories. It powers
[vcspull](https://github.com/vcs-python/vcspull).

Follow the conventions already in the tree, and keep a change scoped to what
was asked for.

## What is here

| Path | What it is |
| ---- | ---------- |
| `src/libvcs/url/` | URL detection and parsing for git, hg, svn; rule registry |
| `src/libvcs/cmd/` | Typed wrappers around the `git`, `hg`, `svn` binaries |
| `src/libvcs/sync/` | Repository sync (clone, update, obtain) built on `cmd/` |
| `src/libvcs/_internal/` | Subprocess runner, dataclasses, `QueryList`; no compatibility guarantee |
| `src/libvcs/pytest_plugin.py` | `pytest11` plugin: fixtures for disposable git/hg/svn repos |
| `tests/` | Test suite, laid out to mirror `src/libvcs/` |
| `docs/` | Sphinx (MyST) site; build with `just build-docs` |
| `CHANGES` | Changelog; rendered as the docs changelog page |
| `README.md` | Project overview; listed in `testpaths` (see below) |
| `justfile` | Task runner for tests, lint, mypy, and docs |

## Which policy applies

- Documentation, user-facing text, `CHANGES`, release notes, commit messages,
  docstrings, and source comments:
  [.github/WRITING.md](.github/WRITING.md)
- Environment, the gates, tests, documentation builds, releases, and pull
  requests: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)

Each of those is the single home for its subject. Where a rule seems to be
stated twice, the file listed above is the one that governs.

## Change discipline

- Make the smallest coherent change that solves the verified problem; keep
  unrelated cleanup out of it.
- Reuse an existing file, helper, API, or test before adding a new one.
- Add a file only for a durable boundary — a distinct responsibility,
  independent reuse, or splitting an oversized module — not for a single-use
  helper or a one-line re-export.
- Add a test for every user-visible behaviour change, and a `CHANGES` entry
  for every change to the public API or pytest fixtures.
- A passing gate is evidence only once it has been shown capable of failing.
  Pair a new test with a deliberate break that proves it bites.

## Domain facts

- `pyproject.toml` runs `--doctest-docutils-modules` over
  `testpaths = ["src/libvcs", "tests", "docs", "README.md"]`. A `>>> `
  prompt anywhere under those paths is a collected, executing test; deleting
  the prompt deletes the test even if the surrounding prose survives.
- A test that shells out to `git`, `hg`, or `svn` skips automatically when
  that binary is not on `PATH` — see `src/libvcs/pytest_plugin.py`.
- libvcs is pre-1.0: a minor version bump may break the public API. See
  [Releasing](.github/CONTRIBUTING.md#releasing).

## References

- Changelog: [`CHANGES`](CHANGES)
- Docs: <https://libvcs.git-pull.com>
- Source: <https://github.com/vcs-python/libvcs>
- Downstream consumer: [vcspull](https://github.com/vcs-python/vcspull)
