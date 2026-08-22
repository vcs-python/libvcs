# Contributing

Thanks for looking. libvcs accepts contributions through
[GitHub](https://github.com/vcs-python/libvcs). libvcs is pre-1.0: bug
reports with a reproduction, and reports of where the API or the
documentation misled you, are the most useful contributions right now.

How this project writes prose — README, `CHANGES`, commit messages,
docstrings, and source comments — is set out separately in
[WRITING.md](WRITING.md). Read that before changing any of it. The
constraints every change is held to, and the map of what is where, are in
[AGENTS.md](../AGENTS.md).

## Getting set up

Development requires [uv](https://github.com/astral-sh/uv).

```console
$ git clone https://github.com/vcs-python/libvcs.git
```

```console
$ cd libvcs
```

```console
$ uv sync --all-extras --dev
```

## The gates

[ruff](https://ruff.rs) formats and lints in a single tool. The full rule
set is declared in `pyproject.toml` under `[tool.ruff]`.

Format:

```console
$ uv run ruff format .
```

Lint:

```console
$ uv run ruff check . --fix --show-fixes
```

[mypy](http://mypy-lang.org/) runs in strict mode (`[tool.mypy] strict =
true`):

```console
$ uv run mypy .
```

Test:

```console
$ uv run pytest
```

Documentation is a gate, not a courtesy. Examples in docstrings,
documentation pages under `docs/`, and `README.md` are executed by
`pytest`; the doctest flags live in `pyproject.toml`, so there is no
separate doctest step and a green `pytest` is the proof. Which blocks
qualify, and the one mistake that silently removes a test, are in
[WRITING.md](WRITING.md#documented-examples-that-run).

Before claiming a test or a gate works, show it failing. A gate that has
never been red is an assumption.

### Imports

- `from __future__ import annotations` at the top of every file.
- Standard-library modules use namespace imports: `import pathlib`, not
  `from pathlib import Path`. Third-party packages may use
  `from X import Y`.
- Typing: `import typing as t`, then access via namespace —
  `t.NamedTuple`, `t.Any`.

### Logging

These rules guide future logging changes; existing code may not yet
conform.

**Setup.** Use `logging.getLogger(__name__)` in every module. Add a
`NullHandler` in library `__init__.py` files. Never configure handlers,
levels, or formatters in library code — that is the application's job.

**Structured context via `extra`.** Pass structured data on every log call
where useful for filtering, searching, or test assertions. Core keys are
stable, scalar, and safe at any log level: `vcs_cmd` (`str`, the VCS command
line), `vcs_type` (`str`, git/svn/hg), `vcs_url` (`str`), `vcs_exit_code`
(`int`), `vcs_repo_path` (`str`). Heavy keys — `vcs_stdout`, `vcs_stderr`
(`list[str]`) — are DEBUG-only; truncate or cap them (`stdout[:100]`).
Names are `snake_case` with a `vcs_` prefix. Treat established keys as
compatibility-sensitive — downstream users may build dashboards and alerts
on them.

**Lazy formatting.** `logger.debug("msg %s", val)`, not f-strings: the
interpolation is skipped entirely when the level is filtered, and a
log-aggregator's message-template grouping treats `"Running %s"` as one
signature instead of one per f-string value. Guard an expensive `val` with
`if logger.isEnabledFor(logging.DEBUG)`.

**`stacklevel` for wrappers.** Increment it for each wrapper layer so
`%(filename)s:%(lineno)d` and OTel `code.filepath` point to the real
caller. Verify whenever call depth changes.

**`LoggerAdapter` for persistent context.** For objects with stable
identity (Repository, Remote, Sync), use `LoggerAdapter` instead of
repeating the same `extra` on every call.

**Log levels.** `DEBUG` for internal mechanics and VCS I/O; `INFO` for
repository lifecycle and user-visible operations; `WARNING` for recoverable
issues, deprecations, and user-actionable config; `ERROR` for failures that
stop an operation. Config-discovery noise is `DEBUG`; only a surprising or
user-actionable config issue escalates to `WARNING`.

**Message style.** Lowercase, past tense for events — `"repository
cloned"`, `"vcs command failed"` — no trailing punctuation. Keep the
message short; put details in `extra`.

**Exception logging.** Use `logger.exception()` only inside an `except`
block when not re-raising. Use `logger.error(..., exc_info=True)` for a
traceback outside an `except` block. Avoid `logger.exception()` followed by
`raise` — it duplicates the traceback.

**Testing logs.** Assert on `caplog.records` attributes, not string
matching on `caplog.text`: scope capture with
`caplog.at_level(logging.DEBUG, logger="libvcs.cmd")`, filter records by
attribute rather than position, and assert on schema
(`record.vcs_exit_code == 0`, not `"exit code 0" in caplog.text`).
`caplog.record_tuples` cannot access extra fields.

**Avoid:** f-strings or `.format()` in log calls; unguarded logging in hot
loops; catch-log-reraise without adding context; `print()` for
diagnostics; logging secret env var values; non-scalar objects in `extra`;
custom `extra` fields referenced in a format string without a safe default
(a missing key raises `KeyError`).

## Tests

The suite spawns real `git`, `hg`, and `svn` processes. A test that needs a
VCS binary is skipped automatically when that binary is not on `PATH` — you
do not need all three installed to contribute.

**Write tests as standalone functions** (`test_*`), not classes. Avoid
`class TestFoo:` groupings; use descriptive function names and file
organization instead. This applies to pytest tests, not doctests.

**Parameterized tests** use `typing.NamedTuple` for the fixture shape:

```python
class RepoFixture(t.NamedTuple):
    test_id: str  # For test naming
    repo_args: dict[str, t.Any]
    expected_result: str


@pytest.mark.parametrize(
    list(RepoFixture._fields),
    REPO_FIXTURES,
    ids=[test.test_id for test in REPO_FIXTURES],
)
def test_sync(...): ...
```

**Fixtures.** `src/libvcs/pytest_plugin.py` (registered as a `pytest11`
entry point) provides:

- `create_git_remote_repo`, `create_hg_remote_repo`, `create_svn_remote_repo`
  — build a temporary remote repository, each gated on its VCS binary being
  installed.
- `git_repo`, `hg_repo`, `svn_repo` — a ready-to-use sync instance checked
  out from a session-cached remote; every consumer gets an isolated copy, so
  a test may mutate it freely, including under parallel runs.
- `set_home`, `vcs_gitconfig`, `vcs_hgconfig`, `git_commit_envvars` —
  environment fixtures that isolate `$HOME` and VCS configuration from the
  host running the tests.

The full reference, including the doctest-only helpers each fixture backs,
is at
[the pytest plugin API page](https://libvcs.git-pull.com/api/pytest-plugin/).

**Running in parallel.** On a multi-core machine, [pytest-xdist](https://pytest-xdist.readthedocs.io/)
spreads the real-subprocess tests across workers:

```console
$ just test-parallel
```

This runs `uv run py.test -n auto`, where `auto` sizes the worker pool to
the machine's cores. Parallelism is opt-in — `just test` and `uv run pytest`
stay serial by default.

**Order independence.** Tests must pass regardless of the order they run
in. Keep fixtures self-contained and reset any global state in teardown.
Check locally with a shuffled run:

```console
$ uv run --with pytest-randomly py.test -p randomly
```

**Debugging.** When stuck in a debugging loop: pause and name the loop out
loud, strip the reproduction down to its minimum, and write down what you
tried before changing approach. Guessing repeatedly at the same fix wastes
more time than the pause does.

## Documentation

```console
$ just build-docs
```

runs Sphinx and fails the build on a broken cross-reference — the doctests
do not catch that, so build the docs before committing a page that adds or
moves a `{ref}`, `{doc}`, or other role target.

```console
$ just start-docs
```

starts [sphinx-autobuild](https://github.com/executablebooks/sphinx-autobuild)
at <http://localhost:8068>, rebuilding on file changes.

## Releasing

Never create tags. Never push tags. The owner handles tagging and tag
pushes, because a tag triggers the publish workflow. See
[Release commits](WRITING.md#release-commits).

libvcs is pre-1.0: a minor version bump (0.39 to 0.40) may contain breaking
changes; a patch bump (0.39.0 to 0.39.1) is reserved for bug fixes and
documentation. The version is set in `src/libvcs/__about__.py` and
`pyproject.toml`. The maintainer's full release checklist is published at
[Releasing](https://libvcs.git-pull.com/project/releasing/).

## Pull requests

One subject per pull request. Unrelated cleanup found along the way belongs
in its own commit, and usually in its own pull request.

Discuss a substantial change via an issue before making it.

Commit format is in [WRITING.md](WRITING.md#commits).

## Decorum

- Participants will be tolerant of opposing views.
- Participants must ensure that their language and actions are free of
  personal attacks and disparaging personal remarks.
- When interpreting the words and actions of others, participants should
  always assume good intentions.
- Behaviour which can be reasonably considered harassment will not be
  tolerated.

Based on [Ruby's Community Conduct Guideline](https://www.ruby-lang.org/en/conduct/).

## Security

Please do not open a public issue for a vulnerability. Report it privately
through the repository's
[security advisories](https://github.com/vcs-python/libvcs/security).
