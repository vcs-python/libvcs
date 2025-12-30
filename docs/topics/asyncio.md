(asyncio)=

# Async Support

libvcs provides **async equivalents** for all synchronous APIs, enabling
non-blocking VCS operations ideal for managing multiple repositories
concurrently.

## Overview

The async API mirrors the sync API with an `Async` prefix:

| Sync Class | Async Equivalent |
|------------|------------------|
| {class}`~libvcs.cmd.git.Git` | {class}`~libvcs.cmd._async.git.AsyncGit` |
| {class}`~libvcs.cmd.hg.Hg` | {class}`~libvcs.cmd._async.hg.AsyncHg` |
| {class}`~libvcs.cmd.svn.Svn` | {class}`~libvcs.cmd._async.svn.AsyncSvn` |
| {class}`~libvcs.sync.git.GitSync` | {class}`~libvcs.sync._async.git.AsyncGitSync` |
| {class}`~libvcs.sync.hg.HgSync` | {class}`~libvcs.sync._async.hg.AsyncHgSync` |
| {class}`~libvcs.sync.svn.SvnSync` | {class}`~libvcs.sync._async.svn.AsyncSvnSync` |

## Why Async?

Async APIs excel when:

- **Managing multiple repositories** - Clone/update repos concurrently
- **Building responsive applications** - UI remains responsive during VCS operations
- **Integration with async frameworks** - FastAPI, aiohttp, etc.
- **CI/CD pipelines** - Parallel repository operations

## Basic Usage

### Running Git Commands

```python
>>> from libvcs.cmd._async.git import AsyncGit
>>> async def example():
...     git = AsyncGit(path=tmp_path)
...     await git.run(['init'])
...     status = await git.status()
...     return 'On branch' in status
>>> asyncio.run(example())
True
```

### Cloning a Repository

```python
>>> from libvcs.cmd._async.git import AsyncGit
>>> async def clone_example():
...     repo_path = tmp_path / 'myrepo'
...     git = AsyncGit(path=repo_path)
...     url = f'file://{create_git_remote_repo()}'
...     await git.clone(url=url)
...     return (repo_path / '.git').exists()
>>> asyncio.run(clone_example())
True
```

### Repository Synchronization

For higher-level repository management, use the sync classes:

```python
>>> from libvcs.sync._async.git import AsyncGitSync
>>> async def sync_example():
...     url = f'file://{create_git_remote_repo()}'
...     repo_path = tmp_path / 'synced_repo'
...     repo = AsyncGitSync(url=url, path=repo_path)
...     await repo.obtain()  # Clone
...     await repo.update_repo()  # Pull updates
...     return (repo_path / '.git').exists()
>>> asyncio.run(sync_example())
True
```

## Concurrent Operations

The primary advantage of async is running operations concurrently:

```python
>>> from libvcs.sync._async.git import AsyncGitSync
>>> async def concurrent_clone():
...     urls = [
...         f'file://{create_git_remote_repo()}',
...         f'file://{create_git_remote_repo()}',
...     ]
...     tasks = []
...     for i, url in enumerate(urls):
...         repo = AsyncGitSync(url=url, path=tmp_path / f'repo_{i}')
...         tasks.append(repo.obtain())
...     await asyncio.gather(*tasks)  # Clone all concurrently
...     return all((tmp_path / f'repo_{i}' / '.git').exists() for i in range(2))
>>> asyncio.run(concurrent_clone())
True
```

## Progress Callbacks

Async APIs support async progress callbacks for real-time output streaming:

```python
>>> import datetime
>>> from libvcs._internal.async_run import async_run
>>> async def with_progress():
...     output_lines = []
...     async def progress(output: str, timestamp: datetime.datetime) -> None:
...         output_lines.append(output)
...     result = await async_run(['echo', 'hello'], callback=progress)
...     return result.strip()
>>> asyncio.run(with_progress())
'hello'
```

For sync callbacks, use the wrapper:

```python
>>> from libvcs._internal.async_run import wrap_sync_callback
>>> def my_sync_callback(output: str, timestamp: datetime.datetime) -> None:
...     print(output, end='')
>>> async_callback = wrap_sync_callback(my_sync_callback)
```

## Sync vs Async Comparison

### Sync Pattern

```python
from libvcs.sync.git import GitSync

repo = GitSync(url="https://github.com/user/repo", path="/tmp/repo")
repo.obtain()  # Blocks until complete
repo.update_repo()  # Blocks again
```

### Async Pattern

```python
import asyncio
from libvcs.sync._async.git import AsyncGitSync

async def main():
    repo = AsyncGitSync(url="https://github.com/user/repo", path="/tmp/repo")
    await repo.obtain()  # Non-blocking
    await repo.update_repo()

asyncio.run(main())
```

## Error Handling

Async methods raise the same exceptions as sync equivalents:

```python
>>> from libvcs import exc
>>> from libvcs._internal.async_run import async_run
>>> async def error_example():
...     try:
...         await async_run(['git', 'nonexistent-command'], check_returncode=True)
...     except exc.CommandError as e:
...         return 'error caught'
...     return 'no error'
>>> asyncio.run(error_example())
'error caught'
```

### Timeout Handling

```python
>>> from libvcs import exc
>>> from libvcs._internal.async_run import async_run
>>> async def timeout_example():
...     try:
...         # Very short timeout for demo
...         await async_run(['sleep', '10'], timeout=0.1)
...     except exc.CommandTimeoutError:
...         return 'timeout caught'
...     return 'completed'
>>> asyncio.run(timeout_example())
'timeout caught'
```

## Testing with pytest-asyncio

Use the async fixtures for testing:

```python
import pytest

@pytest.mark.asyncio
async def test_repo_operations(async_git_repo):
    # async_git_repo is an AsyncGitSync instance
    status = await async_git_repo.cmd.status()
    assert 'On branch' in status
```

See {doc}`/pytest-plugin` for available async fixtures.

## When to Use Async

| Scenario | Recommendation |
|----------|----------------|
| Single repository, simple script | Sync API (simpler) |
| Multiple repositories concurrently | **Async API** |
| Integration with async framework | **Async API** |
| CI/CD with parallel operations | **Async API** |
| Interactive CLI tool | Either (prefer sync for simplicity) |

## API Reference

### Command Classes

- {class}`~libvcs.cmd._async.git.AsyncGit` - Async git commands
- {class}`~libvcs.cmd._async.hg.AsyncHg` - Async mercurial commands
- {class}`~libvcs.cmd._async.svn.AsyncSvn` - Async subversion commands

### Sync Classes

- {class}`~libvcs.sync._async.git.AsyncGitSync` - Async git repository management
- {class}`~libvcs.sync._async.hg.AsyncHgSync` - Async mercurial repository management
- {class}`~libvcs.sync._async.svn.AsyncSvnSync` - Async subversion repository management

### Internal Utilities

- {func}`~libvcs._internal.async_run.async_run` - Low-level async command execution
- {class}`~libvcs._internal.async_subprocess.AsyncSubprocessCommand` - Async subprocess wrapper
