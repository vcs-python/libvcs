(pytest_plugin)=

# `pytest` Plugin

:::{doc-pytest-plugin} libvcs.pytest_plugin
:project: libvcs
:package: libvcs
:summary: libvcs ships a pytest plugin for creating isolated Git, Mercurial, and Subversion repositories during tests.
:tests-url: https://github.com/vcs-python/libvcs/tree/master/tests

Use these fixtures when your tests need disposable repositories, config files,
and home-directory setup without repeating bootstrap code in every suite.

## Recommended fixtures

These fixtures are the usual starting point when enabling the plugin:

- {fixture}`set_home` patches `$HOME` to point at {fixture}`user_path`.
- {fixture}`set_gitconfig` and {fixture}`set_hgconfig` apply stable VCS
  configuration.
- {fixture}`vcs_name`, {fixture}`vcs_email`, and {fixture}`vcs_user` let you
  override commit identity defaults.
- {fixture}`git_commit_envvars` helps when Git ignores `GIT_CONFIG` in a
  subprocess-heavy test.

## Bootstrapping in `conftest.py`

Keep autouse setup explicit in your own `conftest.py` instead of having the
plugin force global side effects.

```python
import pytest


@pytest.fixture(autouse=True)
def setup(
    set_home: None,
    set_gitconfig: None,
    set_hgconfig: None,
) -> None:
    pass
```
:::

## Async Fixtures

For async testing with [pytest-asyncio], libvcs provides async fixture variants:

[pytest-asyncio]: https://pytest-asyncio.readthedocs.io/

### Configuration

Add pytest-asyncio to your test dependencies and configure strict mode:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

### Available Async Fixtures

- {func}`async_git_repo` - An {class}`~libvcs.sync._async.git.AsyncGitSync` instance ready for testing
- `async_create_git_remote_repo` - Factory to create temporary git repositories

### Usage Example

```python
import pytest

@pytest.mark.asyncio
async def test_async_repo_operations(async_git_repo):
    """Test async repository operations."""
    # async_git_repo is an AsyncGitSync instance
    status = await async_git_repo.cmd.status()
    assert 'On branch' in status

    # Update the repo
    await async_git_repo.update_repo()
```

### Creating Repositories in Async Tests

```python
import pytest
from libvcs.sync._async.git import AsyncGitSync

@pytest.mark.asyncio
async def test_clone_repo(tmp_path, create_git_remote_repo):
    """Test cloning a repository asynchronously."""
    remote = create_git_remote_repo()
    repo = AsyncGitSync(
        url=f'file://{remote}',
        path=tmp_path / 'clone',
    )
    await repo.obtain()
    assert (tmp_path / 'clone' / '.git').exists()
```

See {doc}`/topics/asyncio` for more async patterns.

## Types

```{eval-rst}
.. autodata:: libvcs.pytest_plugin.GitCommitEnvVars

.. autoclass:: libvcs.pytest_plugin.CreateRepoFn
   :special-members: __call__
   :exclude-members: __init__, _abc_impl, _is_protocol

.. autoclass:: libvcs.pytest_plugin.CreateRepoPostInitFn
   :special-members: __call__
   :exclude-members: __init__, _abc_impl, _is_protocol
```
