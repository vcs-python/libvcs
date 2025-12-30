# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

- Use namespace imports: `import enum` instead of `from enum import Enum`
- For typing, use `import typing as t` and access via namespace: `t.NamedTuple`, etc.
- Use `from __future__ import annotations` at the top of all Python files

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

### Git Commit Standards

Format commit messages as:
```
Component/File(commit-type[Subcomponent/method]): Concise description

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

## Debugging Tips

When stuck in debugging loops:

1. **Pause and acknowledge the loop**
2. **Minimize to MVP**: Remove all debugging cruft and experimental code
3. **Document the issue** comprehensively for a fresh approach
4. **Format for portability** (using quadruple backticks)
