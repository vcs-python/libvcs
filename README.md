# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

libvcs is an abstraction layer for vcs systems. powers
[vcspull](https://www.github.com/vcs-python/vcspull/).

## Setup

```console
$ pip install --user libvcs
```

Open up python:

```console
$ python

// or for nice autocomplete and syntax highlighting
$ pip install --user ptpython
$ ptpython
```

## Usage

Create a [Repo](https://libvcs.git-pull.com/api.html#creating-a-repo-object) object of the project
to inspect / checkout / update:

```python
>>> from libvcs.shortcuts import create_repo_from_pip_url, create_repo

# repo is an object representation of a vcs repository.
>>> r = create_repo(url='https://www.github.com/vcs-python/libtmux',
...                 vcs='git',
...                 repo_dir='/tmp/libtmux')

# or via pip-style URL
>>> r = create_repo_from_pip_url(
...         pip_url='git+https://www.github.com/vcs-python/libtmux',
...         repo_dir='/tmp/libtmux')
```

Update / clone repo:

```python
# it may or may not be checked out/cloned on the system yet
>>> r.update_repo()
```

Get revision:

```python
>>> r.get_revision()
u'5c227e6ab4aab44bf097da2e088b0ff947370ab8'
```

## Donations

Your donations fund development of new features, testing and support. Your money will go directly to
maintenance and development of the project. If you are an individual, feel free to give whatever
feels right for the value you get out of the project.

See donation options at <https://www.git-pull.com/support.html>.

## More information

- Python support: 3.9+, pypy
- VCS supported: git(1), svn(1), hg(1)
- Source: <https://github.com/vcs-python/libvcs>
- Docs: <https://libvcs.git-pull.com>
- Changelog: <https://libvcs.git-pull.com/history.html>
- API: <https://libvcs.git-pull.com/api.html>
- Issues: <https://github.com/vcs-python/libvcs/issues>
- Test Coverage: <https://codecov.io/gh/vcs-python/libvcs>
- pypi: <https://pypi.python.org/pypi/libvcs>
- Open Hub: <https://www.openhub.net/p/libvcs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/vcs-python/libvcs/workflows/docs/badge.svg)](https://libvcs.git-pull.com/)
[![Build Status](https://github.com/vcs-python/libvcs/workflows/tests/badge.svg)](https://github.com/vcs-python/libvcs/actions?query=workflow%3A%22tests%22)
