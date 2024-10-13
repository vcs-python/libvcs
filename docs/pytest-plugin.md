(pytest_plugin)=

# `pytest` Plugin

With libvcs's pytest plugin for [pytest], you can easily create Git, SVN, and Mercurial repositories on the fly.

```{seealso} Are you using libvcs?

Looking for more flexibility, correctness, or power? Need different defaults? [Connect with us] on GitHub. We'd love to hear about your use case—APIs won't be stabilized until we're confident everything meets expectations.

[connect with us]: https://github.com/vcs-python/libvcs/discussions
```

```{module} libvcs.pytest_plugin

```

[pytest]: https://docs.pytest.org/

## Usage

Install `libvcs` using your preferred Python package manager:

```console
$ pip install libvcs
```

Pytest will automatically detect the plugin, and its fixtures will be available.

## Fixtures

This pytest plugin works by providing {ref}`pytest fixtures <pytest:fixtures-api>`. The plugin's fixtures ensure that a fresh Git, Subversion, or Mercurial repository is available for each test. It utilizes [session-scoped fixtures] to cache initial repositories, improving performance across tests.

[session-scoped fixtures]: https://docs.pytest.org/en/8.3.x/how-to/fixtures.html#fixture-scopes

(recommended-fixtures)=

## Recommended Fixtures

When the plugin is enabled and `pytest` is run, these overridable fixtures are automatically used:

- Create temporary test directories for:
  - `/home/` ({func}`home_path`)
  - `/home/${user}` ({func}`user_path`)
- Set the home directory:
  - Patch `$HOME` to point to {func}`user_path` using ({func}`set_home`)
- Create configuration files:
  - `.gitconfig` via {func}`gitconfig`
  - `.hgrc` via {func}`hgconfig`
- Set default VCS configurations:
  - Use {func}`hgconfig` for [`HGRCPATH`] via {func}`set_hgconfig`
  - Use {func}`gitconfig` for [`GIT_CONFIG`] via {func}`set_gitconfig`
- Set default commit names and emails:
  - Name: {func}`vcs_name`
  - Email: {func}`vcs_email`
  - User (e.g. _`user <email@tld>`_): {func}`vcs_user`
  - For git only: {func}`git_commit_envvars`

These ensure that repositories can be cloned and created without unnecessary warnings.

[`HGRCPATH`]: https://www.mercurial-scm.org/doc/hg.1.html#:~:text=UNIX%2Dlike%20environments.-,HGRCPATH,-If%20not%20set
[`GIT_CONFIG`]: https://git-scm.com/docs/git-config#Documentation/git-config.txt-GITCONFIG

## Bootstrapping pytest in `conftest.py`

To configure the above fixtures with `autouse=True`, add them to your `conftest.py` file or test file, depending on the desired scope.

_Why aren't these fixtures added automatically by the plugin?_ This design choice promotes explicitness, adhering to best practices for pytest plugins and Python packages.

### Setting a Temporary Home Directory

To set a temporary home directory, use the {func}`set_home` fixture with `autouse=True`:

```python
import pytest

@pytest.fixture(autouse=True)
def setup(set_home: None):
    pass
```

### VCS Configuration

#### Git

You can override the default author used in {func}`git_remote_repo` and other
fixtures via {func}`vcs_name`, {func}`vcs_email`, and {func}`vcs_user`:

```
@pytest.fixture(scope="session")
def vcs_name() -> str:
    return "My custom name"
```

Use the {func}`set_gitconfig` fixture with `autouse=True`:

```python
import pytest

@pytest.fixture(autouse=True)
def setup(set_gitconfig: None):
    pass
```

Sometimes, `set_getconfig` via `GIT_CONFIG` doesn't apply as expected. For those
cases, you can use {func}`git_commit_envvars`:

```python
import pytest

@pytest.fixture
def my_git_repo(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    gitconfig: pathlib.Path,
    git_commit_envvars: "_ENV",
) -> pathlib.Path:
    """Copy the session-scoped Git repository to a temporary directory."""
    repo_path = create_git_remote_repo()
    git_remote_repo_single_commit_post_init(
        remote_repo_path=repo_path,
        env=git_commit_envvars,
    )
    return repo_path
```

#### Mercurial

Use the {func}`set_hgconfig` fixture with `autouse=True`:

```python
import pytest

@pytest.fixture(autouse=True)
def setup(set_hgconfig: None):
    pass
```

## Examples

For usage examples, refer to libvcs's own [tests/](https://github.com/vcs-python/libvcs/tree/master/tests).

## API Reference

```{eval-rst}
.. automodule:: libvcs.pytest_plugin
    :members:
    :inherited-members:
    :private-members:
    :show-inheritance:
    :member-order: bysource
```
