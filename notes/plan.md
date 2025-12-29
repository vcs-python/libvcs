# libvcs Asyncio Support Implementation Plan

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Core Async Subprocess (`async_subprocess.py`) |
| Phase 2 | ✅ Complete | Async Run Function (`async_run.py`) |
| Phase 3 | ✅ Complete | Async Command Classes (`AsyncGit`) |
| Phase 4 | ✅ Complete | Async Sync Classes (`AsyncGitSync`) |
| Phase 5 | ✅ Complete | Async pytest fixtures (`async_git_repo`) |
| Phase 6 | ✅ Complete | Async Mercurial (`AsyncHg`, `AsyncHgSync`) |

---

## Study Sources

The following reference codebases were studied to inform this design:

| Source | Path | Key Learnings |
|--------|------|---------------|
| **CPython asyncio** | `~/study/c/cpython/Lib/asyncio/` | Subprocess patterns, flow control, `communicate()` |
| **pytest** | `~/study/python/pytest/` | Fixture system internals, parametrization |
| **pytest-asyncio** | `~/study/python/pytest-asyncio/` | Async fixture wrapping, event loop management |
| **git** | `~/study/c/git/` | VCS command patterns |

### Key Files Studied

- `cpython/Lib/asyncio/subprocess.py` - High-level async subprocess API
- `cpython/Lib/asyncio/streams.py` - StreamReader/Writer with backpressure
- `cpython/Lib/asyncio/base_subprocess.py` - Protocol/Transport implementation
- `pytest-asyncio/pytest_asyncio/plugin.py` - Fixture wrapping, loop lifecycle

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Scope** | Full stack (subprocess → cmd → sync) | Complete async workflows |
| **Organization** | Separate `_async/` subpackages | Clean separation, maintainable |
| **Callbacks** | Async-only for async APIs | Better DX, typing, no runtime overhead |
| **Testing** | 100% coverage, pytest-asyncio strict mode | Reliability, isolation |
| **Typing** | Fully typed, no `Any` escapes | Type safety, IDE support |

---

## Verification Before Commit

**REQUIRED**: Before committing any phase or making a PR, run the full verification pipeline:

```bash
uv run ruff check . --fix --show-fixes
uv run ruff format .
uv run mypy
uv run pytest --reruns 0 -vvv
```

All checks must pass:
- `ruff check`: No linting errors
- `ruff format`: No formatting changes needed
- `mypy`: Success with no type errors
- `pytest`: All tests pass (0 failures)

---

## DOs

### Subprocess Execution
- **DO** use `communicate()` for all subprocess I/O (prevents deadlocks)
- **DO** use `asyncio.timeout()` context manager for timeouts
- **DO** handle `BrokenPipeError` gracefully (process may exit early)
- **DO** use try/finally for resource cleanup

### API Design
- **DO** keep sync and async APIs parallel in `_async/` subpackages
- **DO** share argument-building logic between sync/async variants
- **DO** use async-only callbacks for async APIs (no `inspect.isawaitable()`)
- **DO** provide `wrap_sync_callback()` helper for users with sync callbacks
- **DO** use `Async` prefix for async classes: `AsyncGit`, `AsyncGitSync`

### Testing
- **DO** use strict mode for pytest-asyncio
- **DO** use function-scoped event loops for test isolation
- **DO** use `@pytest_asyncio.fixture` for async fixtures
- **DO** use `NamedTuple` with `test_id` for parametrized tests
- **DO** mirror sync test structure for async tests

### Typing
- **DO** use `from __future__ import annotations` in all files
- **DO** use `import typing as t` namespace pattern
- **DO** provide explicit return type annotations
- **DO** use Protocol classes for callback types

---

## DON'Ts

### Subprocess Execution
- **DON'T** poll `returncode` - use `await proc.wait()`
- **DON'T** read stdout/stderr manually for bidirectional I/O
- **DON'T** close event loop in user code
- **DON'T** mix blocking `subprocess.run()` in async code
- **DON'T** create new event loops manually

### API Design
- **DON'T** use union types for callbacks (`None | Awaitable[None]`)
- **DON'T** break backward compatibility of sync APIs
- **DON'T** leak event loop details into public APIs

### Testing
- **DON'T** assume tests run concurrently (they're sequential)
- **DON'T** close event loop in tests (pytest-asyncio handles cleanup)
- **DON'T** mismatch fixture scope and loop scope

---

## Implementation Phases

### Phase 1: Core Async Subprocess (Foundation)

**Goal:** Create async subprocess wrapper matching `SubprocessCommand` API.

**Files to create:**
- `src/libvcs/_internal/async_subprocess.py`

**Key patterns:**
```python
@dataclasses.dataclass
class AsyncSubprocessCommand:
    args: list[str]
    cwd: pathlib.Path | None = None
    env: dict[str, str] | None = None

    async def run(self, *, check: bool = True, timeout: float | None = None) -> tuple[str, str, int]:
        proc = await asyncio.create_subprocess_shell(...)
        async with asyncio.timeout(timeout):
            stdout, stderr = await proc.communicate()
        return stdout.decode(), stderr.decode(), proc.returncode
```

**Tests:**
- `tests/_internal/test_async_subprocess.py`

---

### Phase 2: Async Run Function

**Goal:** Async equivalent of `_internal/run.py` with output parsing.

**Files to create:**
- `src/libvcs/_internal/async_run.py`

**Key considerations:**
- Reuse output parsing logic from `run.py`
- Async callback protocol: `async def callback(output: str, timestamp: datetime) -> None`
- Stream output line-by-line using `StreamReader.readline()`

**Tests:**
- `tests/_internal/test_async_run.py`

---

### Phase 3: Async Command Classes

**Goal:** Async equivalents of `Git`, `Hg`, `Svn` command classes.

**Files to create:**
- `src/libvcs/cmd/_async/__init__.py`
- `src/libvcs/cmd/_async/git.py` - `AsyncGit`
- `src/libvcs/cmd/_async/hg.py` - `AsyncHg`
- `src/libvcs/cmd/_async/svn.py` - `AsyncSvn`

**Strategy:**
- Extract argument-building to shared functions
- Async methods call `await self.run()` instead of `self.run()`
- Manager classes (GitRemoteManager, etc.) get async variants

**Tests:**
- `tests/cmd/_async/test_git.py`
- `tests/cmd/_async/test_hg.py`
- `tests/cmd/_async/test_svn.py`

---

### Phase 4: Async Sync Classes

**Goal:** Async equivalents of `GitSync`, `HgSync`, `SvnSync`.

**Files to create:**
- `src/libvcs/sync/_async/__init__.py`
- `src/libvcs/sync/_async/base.py` - `AsyncBaseSync`
- `src/libvcs/sync/_async/git.py` - `AsyncGitSync`
- `src/libvcs/sync/_async/hg.py` - `AsyncHgSync`
- `src/libvcs/sync/_async/svn.py` - `AsyncSvnSync`

**Key patterns:**
```python
class AsyncGitSync(AsyncBaseSync):
    async def obtain(self, ...) -> None:
        await self.cmd.clone(...)

    async def update_repo(self, ...) -> None:
        await self.cmd.fetch(...)
        await self.cmd.checkout(...)
```

**Tests:**
- `tests/sync/_async/test_git.py`
- `tests/sync/_async/test_hg.py`
- `tests/sync/_async/test_svn.py`

---

### Phase 5: Async pytest Plugin

**Goal:** Async fixture variants for testing.

**Files to modify:**
- `src/libvcs/pytest_plugin.py` - Add async fixtures

**New fixtures:**
- `async_create_git_remote_repo`
- `async_create_hg_remote_repo`
- `async_create_svn_remote_repo`
- `async_git_repo`, `async_hg_repo`, `async_svn_repo`

**Pattern:**
```python
@pytest_asyncio.fixture(loop_scope="function")
async def async_git_repo(tmp_path: Path) -> t.AsyncGenerator[AsyncGitSync, None]:
    repo = AsyncGitSync(url="...", path=tmp_path / "repo")
    await repo.obtain()
    yield repo
```

---

## Test Strategy

### pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

### Parametrized Test Pattern

```python
class CloneFixture(t.NamedTuple):
    test_id: str
    clone_kwargs: dict[str, t.Any]
    expected: list[str]

CLONE_FIXTURES = [
    CloneFixture("basic", {}, [".git"]),
    CloneFixture("shallow", {"depth": 1}, [".git"]),
]

@pytest.mark.parametrize(
    list(CloneFixture._fields),
    CLONE_FIXTURES,
    ids=[f.test_id for f in CLONE_FIXTURES],
)
@pytest.mark.asyncio
async def test_clone(test_id: str, clone_kwargs: dict, expected: list, ...) -> None:
    ...
```

### Coverage Goal

- **Target:** 100% coverage for all async code
- **Approach:** Mirror sync tests, add async-specific edge cases
- **Tools:** pytest-cov, pytest-asyncio

---

## Type Strategy

### Callback Types

```python
# Sync callback (unchanged)
ProgressCallback = Callable[[str, datetime], None]

# Async callback (for async APIs only)
AsyncProgressCallback = Callable[[str, datetime], Awaitable[None]]

# Protocol for type checking
class AsyncProgressProtocol(t.Protocol):
    async def __call__(self, output: str, timestamp: datetime) -> None: ...
```

### Helper for Sync Callback Users

```python
def wrap_sync_callback(
    sync_cb: Callable[[str, datetime], None]
) -> AsyncProgressProtocol:
    """Wrap a sync callback for use with async APIs."""
    async def wrapper(output: str, timestamp: datetime) -> None:
        sync_cb(output, timestamp)
    return wrapper
```

---

## File Structure

```
src/libvcs/
├── _internal/
│   ├── subprocess.py         # Existing sync
│   ├── async_subprocess.py   # NEW: Async subprocess
│   ├── run.py                # Existing sync
│   └── async_run.py          # NEW: Async run
├── cmd/
│   ├── git.py                # Existing sync
│   ├── hg.py
│   ├── svn.py
│   └── _async/               # NEW
│       ├── __init__.py
│       ├── git.py            # AsyncGit
│       ├── hg.py             # AsyncHg
│       └── svn.py            # AsyncSvn
├── sync/
│   ├── base.py               # Existing sync
│   ├── git.py
│   ├── hg.py
│   ├── svn.py
│   └── _async/               # NEW
│       ├── __init__.py
│       ├── base.py           # AsyncBaseSync
│       ├── git.py            # AsyncGitSync
│       ├── hg.py             # AsyncHgSync
│       └── svn.py            # AsyncSvnSync
└── pytest_plugin.py          # Add async fixtures
```

---

## Success Criteria

1. All async APIs pass mypy with strict mode
2. 100% test coverage for async code
3. All existing sync tests continue to pass
4. Documentation updated with async examples
5. pytest-asyncio strict mode works without warnings
