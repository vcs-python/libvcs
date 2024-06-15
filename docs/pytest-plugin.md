(pytest_plugin)=

# `pytest` plugin

Create git, svn, and hg repos on the fly in [pytest].

```{seealso} Using libvcs?

Do you want more flexibility? Correctness? Power? Defaults changed? [Connect with us] on the tracker, we want to know
your case, we won't stabilize APIs until we're sure everything is by the book.

[connect with us]: https://github.com/vcs-python/libvcs/discussions

```

```{module} libvcs.pytest_plugin

```

[pytest]: https://docs.pytest.org/

## Usage

Install `libvcs` via the python package manager of your choosing, e.g.

```console
$ pip install libvcs
```

The pytest plugin will automatically be detected via pytest, and the fixtures will be added.

## Fixtures

`pytest-vcs` works through providing {ref}`pytest fixtures <pytest:fixtures-api>` - so read up on
those!

The plugin's fixtures guarantee a fresh git repository every test.

(recommended-fixtures)=

## Recommended fixtures

These fixtures are automatically used when the plugin is enabled and `pytest` is run.

- Creating temporary, test directories for:
  - `/home/` ({func}`home_path`)
  - `/home/${user}` ({func}`user_path`)
- Setting your home directory
  - Patch `$HOME` to point to {func}`user_path` ({func}`set_home`)
- Set default configuration

  - `.gitconfig`, via {func}`gitconfig`:
  - `.hgrc`, via {func}`hgconfig`:

  These are set to ensure you can correctly clone and create repositories without without extra
  warnings.

## Bootstrapping pytest in your `conftest.py`

The most common scenario is you will want to configure the above fixtures with `autouse`.

_Why doesn't the plugin automatically add them?_ It's part of being a decent pytest plugin and
python package: explicitness.

(set_home)=

### Setting a temporary home directory

```python
import pytest

@pytest.fixture(autouse=True)
def setup(
    set_home: None,
):
    pass
```

## See examples

View libvcs's own [tests/](https://github.com/vcs-python/libvcs/tree/master/tests)

## API reference

```{eval-rst}
.. automodule:: libvcs.pytest_plugin
    :members:
    :inherited-members:
    :private-members:
    :show-inheritance:
    :member-order: bysource
```
