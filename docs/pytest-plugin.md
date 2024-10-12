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

When the plugin is enabled and `pytest` is run, these fixtures are automatically used:

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

### Setting a Default VCS Configuration

#### Git

Use the {func}`set_gitconfig` fixture with `autouse=True`:

```python
import pytest

@pytest.fixture(autouse=True)
def setup(set_gitconfig: None):
    pass
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
