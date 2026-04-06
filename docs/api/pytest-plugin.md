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
