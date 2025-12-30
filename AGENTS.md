# AGENTS.md

This file provides guidance to LLM Agents such as Codex, Gemini, Claude Code (claude.ai/code), etc. when working with code in this repository.

## CRITICAL REQUIREMENTS

### Test Success
- ALL tests MUST pass for code to be considered complete and working
- Never describe code as "working as expected" if there are ANY failing tests
- Even if specific feature tests pass, failing tests elsewhere indicate broken functionality
- Changes that break existing tests must be fixed before considering implementation complete
- A successful implementation must pass linting, type checking, AND all existing tests

## Project Overview

libvcs is a lite, typed Python tool for:
- Detecting and parsing URLs for Git, Mercurial, and Subversion repositories
- Providing command abstractions for git, hg, and svn
- Synchronizing repositories locally
- Creating pytest fixtures for testing with temporary repositories

The library powers [vcspull](https://www.github.com/vcs-python/vcspull/), a tool for managing and synchronizing multiple git, svn, and mercurial repositories.

## Development Environment

This project uses:
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) for dependency management
- [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [mypy](https://github.com/python/mypy) for type checking
- [pytest](https://docs.pytest.org/) for testing

## Common Commands

### Setting Up Environment

```bash
# Install dependencies
uv pip install --editable .
uv pip sync

# Install with development dependencies
uv pip install --editable . -G dev
```

### Running Tests

```bash
# Run all tests
just test
# or directly with pytest
uv run pytest

# Run a single test file
uv run pytest tests/sync/test_git.py

# Run a specific test
uv run pytest tests/sync/test_git.py::test_remotes

# Run tests with test watcher
just start
# or
uv run ptw .
```

### Linting and Type Checking

```bash
# Run ruff for linting
just ruff
# or directly
uv run ruff check .

# Format code with ruff
just ruff-format
# or directly
uv run ruff format .

# Run ruff linting with auto-fixes
uv run ruff check . --fix --show-fixes

# Run mypy for type checking
just mypy
# or directly
uv run mypy src tests

# Watch mode for linting (using entr)
just watch-ruff
just watch-mypy
```

### Development Workflow

Follow this workflow for code changes:

1. **Format First**: `uv run ruff format .`
2. **Run Tests**: `uv run pytest`
3. **Run Linting**: `uv run ruff check . --fix --show-fixes`
4. **Check Types**: `uv run mypy`
5. **Verify Tests Again**: `uv run pytest`

### Documentation

```bash
# Build documentation
just build-docs

# Start documentation server with auto-reload
just start-docs

# Update documentation CSS/JS
just design-docs
```

## Code Architecture

libvcs is organized into three main modules:

1. **URL Detection and Parsing** (`libvcs.url`)
   - Base URL classes in `url/base.py`
   - VCS-specific implementations in `url/git.py`, `url/hg.py`, and `url/svn.py`
   - URL registry in `url/registry.py`
   - Constants in `url/constants.py`

2. **Command Abstraction** (`libvcs.cmd`)
   - Command classes for git, hg, and svn in `cmd/git.py`, `cmd/hg.py`, and `cmd/svn.py`
   - Built on top of Python's subprocess module (via `_internal/subprocess.py`)

3. **Repository Synchronization** (`libvcs.sync`)
   - Base sync classes in `sync/base.py`
   - VCS-specific sync implementations in `sync/git.py`, `sync/hg.py`, and `sync/svn.py`

4. **Internal Utilities** (`libvcs._internal`)
   - Subprocess wrappers in `_internal/subprocess.py`
   - Data structures in `_internal/dataclasses.py` and `_internal/query_list.py`
   - Runtime helpers in `_internal/run.py` and `_internal/shortcuts.py`

5. **pytest Plugin** (`libvcs.pytest_plugin`)
   - Provides fixtures for creating temporary repositories for testing

## Testing Strategy

libvcs uses pytest for testing with many custom fixtures. The pytest plugin (`pytest_plugin.py`) defines fixtures for creating temporary repositories for testing. These include:

- `create_git_remote_repo`: Creates a git repository for testing
- `create_hg_remote_repo`: Creates a Mercurial repository for testing
- `create_svn_remote_repo`: Creates a Subversion repository for testing
- `git_repo`, `svn_repo`, `hg_repo`: Pre-made repository instances
- `set_home`, `gitconfig`, `hgconfig`, `git_commit_envvars`: Environment fixtures

These fixtures handle setup and teardown automatically, creating isolated test environments.

For running tests with actual VCS commands, tests will be skipped if the corresponding VCS binary is not installed.

### Testing Guidelines

1. **Use functional tests only**: Write tests as standalone functions (`test_*`), not classes. Avoid `class TestFoo:` groupings - use descriptive function names and file organization instead. This applies to pytest tests, not doctests.

### Example Fixture Usage

```python
def test_repo_sync(git_repo):
    # git_repo is already a GitSync instance with a clean repository
    # Use it directly in your tests
    assert git_repo.get_revision() == "initial"
```

### Parameterized Tests

Use `typing.NamedTuple` for parameterized tests:

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
def test_sync(
    # Parameters and fixtures...
):
    # Test implementation
```

## Coding Standards

### Imports

- Use namespace imports for stdlib: `import enum` instead of `from enum import Enum`; third-party packages may use `from X import Y`
- For typing, use `import typing as t` and access via namespace: `t.NamedTuple`, etc.
- Use `from __future__ import annotations` at the top of all Python files

### Naming Conventions

Follow Python community conventions (Django, pytest, Sphinx patterns):

**Method naming:**
- Use `get_*` prefix for methods that perform I/O or subprocess calls (e.g., `get_remotes()`, `get_revision()`)
- Use `is_*` prefix for boolean checks (e.g., `is_valid()`)
- Use `has_*` prefix for existence checks (e.g., `has_remote()`)

**Parameter naming:**
- Use descriptive names instead of underscore-prefixed built-in shadows
- BAD: `_all`, `_type`, `_list` (cryptic, non-standard)
- GOOD: `all_remotes`, `include_all`, `file_type`, `path_list` (self-documenting)

**Examples:**
```python
# BAD - cryptic underscore prefix
def fetch(_all: bool = False): ...
def rev_list(_all: bool = False): ...

# GOOD - descriptive parameter names
def fetch(all_remotes: bool = False): ...
def rev_list(include_all: bool = False): ...

# BAD - inconsistent getter naming
def remotes(): ...      # No prefix
def get_revision(): ... # Has prefix

# GOOD - consistent getter naming for subprocess calls
def get_remotes(): ...
def get_revision(): ...
```

**Rationale:** Major Python projects (Django, pytest, Sphinx) don't use `_all` style prefixes. They either use the built-in name directly as a keyword-only argument, or use descriptive alternatives. Underscore prefixes are reserved for private/internal parameters only.

### Docstrings

Follow NumPy docstring style for all functions and methods:

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

### Doctests

**All functions and methods MUST have working doctests.** Doctests serve as both documentation and tests.

**CRITICAL RULES:**
- Doctests MUST actually execute - never comment out `asyncio.run()` or similar calls
- Doctests MUST NOT be converted to `.. code-block::` as a workaround (code-blocks don't run)
- If you cannot create a working doctest, **STOP and ask for help**

**Available tools for doctests:**
- `doctest_namespace` fixtures: `tmp_path`, `asyncio`, `create_git_remote_repo`, `create_hg_remote_repo`, `create_svn_remote_repo`, `example_git_repo`
- Ellipsis for variable output: `# doctest: +ELLIPSIS`
- Update `pytest_plugin.py` to add new fixtures to `doctest_namespace`

**`# doctest: +SKIP` is NOT permitted** - it's just another workaround that doesn't test anything. If a VCS binary might not be installed, pytest already handles skipping via `skip_if_binaries_missing`. Use the fixtures properly.

**Async doctest pattern:**
```python
>>> async def example():
...     result = await some_async_function()
...     return result
>>> asyncio.run(example())
'expected output'
```

**Using fixtures in doctests:**
```python
>>> git = Git(path=tmp_path)  # tmp_path from doctest_namespace
>>> git.run(['status'])
'...'
```

**When output varies, use ellipsis:**
```python
>>> git.clone(url=f'file://{create_git_remote_repo()}')  # doctest: +ELLIPSIS
'Cloning into ...'
```

### Logging Standards

These rules guide future logging changes; existing code may not yet conform.

#### Logger setup

- Use `logging.getLogger(__name__)` in every module
- Add `NullHandler` in library `__init__.py` files
- Never configure handlers, levels, or formatters in library code — that's the application's job

#### Structured context via `extra`

Pass structured data on every log call where useful for filtering, searching, or test assertions.

**Core keys** (stable, scalar, safe at any log level):

| Key | Type | Context |
|-----|------|---------|
| `vcs_cmd` | `str` | VCS command line |
| `vcs_type` | `str` | VCS type (git, svn, hg) |
| `vcs_url` | `str` | repository URL |
| `vcs_exit_code` | `int` | VCS process exit code |
| `vcs_repo_path` | `str` | local repository path |

**Heavy/optional keys** (DEBUG only, potentially large):

| Key | Type | Context |
|-----|------|---------|
| `vcs_stdout` | `list[str]` | VCS stdout lines (truncate or cap; `%(vcs_stdout)s` produces repr) |
| `vcs_stderr` | `list[str]` | VCS stderr lines (same caveats) |

Treat established keys as compatibility-sensitive — downstream users may build dashboards and alerts on them. Change deliberately.

#### Key naming rules

- `snake_case`, not dotted; `vcs_` prefix
- Prefer stable scalars; avoid ad-hoc objects
- Heavy keys (`vcs_stdout`, `vcs_stderr`) are DEBUG-only; consider companion `vcs_stdout_len` fields or hard truncation (e.g. `stdout[:100]`)

#### Lazy formatting

`logger.debug("msg %s", val)` not f-strings. Two rationales:
- Deferred string interpolation: skipped entirely when level is filtered
- Aggregator message template grouping: `"Running %s"` is one signature grouped ×10,000; f-strings make each line unique

When computing `val` itself is expensive, guard with `if logger.isEnabledFor(logging.DEBUG)`.

#### stacklevel for wrappers

Increment for each wrapper layer so `%(filename)s:%(lineno)d` and OTel `code.filepath` point to the real caller. Verify whenever call depth changes.

#### LoggerAdapter for persistent context

For objects with stable identity (Repository, Remote, Sync), use `LoggerAdapter` to avoid repeating the same `extra` on every call. Lead with the portable pattern (override `process()` to merge); `merge_extra=True` simplifies this on Python 3.13+.

#### Log levels

| Level | Use for | Examples |
|-------|---------|----------|
| `DEBUG` | Internal mechanics, VCS I/O | VCS command + stdout, URL parsing steps |
| `INFO` | Repository lifecycle, user-visible operations | Repository cloned, sync completed |
| `WARNING` | Recoverable issues, deprecation, user-actionable config | Deprecated VCS option, unrecognized remote |
| `ERROR` | Failures that stop an operation | VCS command failed, invalid URL |

Config discovery noise belongs in `DEBUG`; only surprising/user-actionable config issues → `WARNING`.

#### Message style

- Lowercase, past tense for events: `"repository cloned"`, `"vcs command failed"`
- No trailing punctuation
- Keep messages short; put details in `extra`, not the message string

#### Exception logging

- Use `logger.exception()` only inside `except` blocks when you are **not** re-raising
- Use `logger.error(..., exc_info=True)` when you need the traceback outside an `except` block
- Avoid `logger.exception()` followed by `raise` — this duplicates the traceback. Either add context via `extra` that would otherwise be lost, or let the exception propagate

#### Testing logs

Assert on `caplog.records` attributes, not string matching on `caplog.text`:
- Scope capture: `caplog.at_level(logging.DEBUG, logger="libvcs.cmd")`
- Filter records rather than index by position: `[r for r in caplog.records if hasattr(r, "vcs_cmd")]`
- Assert on schema: `record.vcs_exit_code == 0` not `"exit code 0" in caplog.text`
- `caplog.record_tuples` cannot access extra fields — always use `caplog.records`

#### Avoid

- f-strings/`.format()` in log calls
- Unguarded logging in hot loops (guard with `isEnabledFor()`)
- Catch-log-reraise without adding new context
- `print()` for diagnostics
- Logging secret env var values (log key names only)
- Non-scalar ad-hoc objects in `extra`
- Requiring custom `extra` fields in format strings without safe defaults (missing keys raise `KeyError`)

### Git Commit Standards

Format commit messages as:
```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.
what:
- Specific technical changes made
- Focused on a single topic
```

Common commit types:
- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (CLAUDE.md)
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
For multi-line commits, use heredoc to preserve formatting:
```bash
git commit -m "$(cat <<'EOF'
feat(Component[method]) add feature description

why: Explanation of the change.
what:
- First change
- Second change
EOF
)"
```

## Documentation Standards

### Code Blocks in Documentation

When writing documentation (README, CHANGES, docs/), follow these rules for code blocks:

**One command per code block.** This makes commands individually copyable. For sequential commands, either use separate code blocks or chain them with `&&` or `;` and `\` continuations (keeping it one logical command).

**Put explanations outside the code block**, not as comments inside.

Good:

Run the tests:

```console
$ uv run pytest
```

Run with coverage:

```console
$ uv run pytest --cov
```

Bad:

```console
# Run the tests
$ uv run pytest

# Run with coverage
$ uv run pytest --cov
```

### Shell Command Formatting

These rules apply to shell commands in documentation (README, CHANGES, docs/), **not** to Python doctests.

**Use `console` language tag with `$ ` prefix.** This distinguishes interactive commands from scripts and enables prompt-aware copy in many terminals.

Good:

```console
$ uv run pytest
```

Bad:

```bash
uv run pytest
```

**Split long commands with `\` for readability.** Each flag or flag+value pair gets its own continuation line, indented. Positional parameters go on the final line.

Good:

```console
$ pipx install \
    --suffix=@next \
    --pip-args '\--pre' \
    --force \
    'libvcs'
```

Bad:

```console
$ pipx install --suffix=@next --pip-args '\--pre' --force 'libvcs'
```

### CHANGES and MIGRATION Files

Maintain `CHANGES` (changelog) and `MIGRATION` (upgrade guide) for all user-facing changes.

**File structure:**
- `CHANGES`: Organized by version with sections in this order of precedence:
  1. `### Breaking changes` - API changes that require user action
  2. `### New features` - New functionality
  3. `### Bug fixes` - Corrections to existing behavior
  4. `### Documentation` - Doc-only changes
  5. `### Development` or `### Internal` - Tooling, CI, refactoring
- `MIGRATION`: Detailed migration instructions with before/after examples

**Maintenance-only releases:**
For releases with no user-facing changes (only internal/development work), use:
```markdown
_Maintenance only, no bug fixes, or new features_
```

**PR references - where to put them:**
- **DO**: Put PR number in section headers or at end of bullet items in the files
- **DON'T**: Put PR number in commit message titles (causes linkback notification noise in the PR)

**For larger changes with dedicated sections:**
```markdown
#### API Naming Consistency (#507)

Renamed parameters and methods...
```

**For smaller changes in a list:**
```markdown
### Bug fixes

- Fix argument expansion in `rev_list` (#455)
- Remove unused command: `Svn.mergelist` (#450)
```

**Commit messages should NOT include PR numbers:**
```bash
# GOOD - no PR in commit message
CHANGES(docs): Document breaking API changes for 0.39.x

# BAD - PR in commit message creates noise
CHANGES(docs): Document breaking API changes for 0.39.x (#507)
```

The PR reference in the file content creates a clean linkback when the PR merges, while keeping commit messages focused and avoiding duplicate notifications.

## Debugging Tips

When stuck in debugging loops:

1. **Pause and acknowledge the loop**
2. **Minimize to MVP**: Remove all debugging cruft and experimental code
3. **Document the issue** comprehensively for a fresh approach
4. **Format for portability** (using quadruple backticks)
