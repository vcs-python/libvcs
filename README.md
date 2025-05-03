# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

libvcs is a lite, [typed](https://docs.python.org/3/library/typing.html), pythonic tool box for
detection and parsing of URLs, commanding, and syncing with `git`, `hg`, and `svn`. Powers
[vcspull](https://www.github.com/vcs-python/vcspull/).

## Overview

### Key Features

- **URL Detection and Parsing**: Validate and parse Git, Mercurial, and Subversion URLs.
- **Command Abstraction**: Interact with VCS systems through a Python API.
- **Repository Synchronization**: Clone and update repositories locally via
  Python API.
- **py.test fixtures**: Create temporary local repositories and working copies for testing for unit tests.

_Supports Python 3.9 and above, Git (including AWS CodeCommit), Subversion, and Mercurial._

To **get started**, see the [quickstart guide](https://libvcs.git-pull.com/quickstart.html) for more information.

```console
$ pip install --user libvcs
```

## URL Detection and Parsing

Easily validate and parse VCS URLs using the
[`libvcs.url`](https://libvcs.git-pull.com/url/index.html) module:

### Validate URLs

```python
>>> from libvcs.url.git import GitURL

>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
```

### Parse and adjust Git URLs:

```python
>>> from libvcs.url.git import GitURL

>>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')

>>> git_location
GitURL(url=git@github.com:vcs-python/libvcs.git,
        user=git,
        hostname=github.com,
        path=vcs-python/libvcs,
        suffix=.git,
        rule=core-git-scp)
```

Switch repo libvcs -> vcspull:

```python
>>> from libvcs.url.git import GitURL

>>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')

>>> git_location.path = 'vcs-python/vcspull'

>>> git_location.to_url()
'git@github.com:vcs-python/vcspull.git'

# Switch them to gitlab:
>>> git_location.hostname = 'gitlab.com'

# Export to a `git clone` compatible URL.
>>> git_location.to_url()
'git@gitlab.com:vcs-python/vcspull.git'
```

See more in the [parser document](https://libvcs.git-pull.com/parse/index.html).

## Command Abstraction

Abstracts CLI commands for `git(1)`, `hg(1)`, `svn(1)` via a lightweight [`subprocess`](https://docs.python.org/3/library/subprocess.html) wrapper.

### Run Git Commands

```python
import pathlib
from libvcs.cmd.git import Git

git = Git(path=pathlib.Path.cwd() / 'my_git_repo')
git.clone(url='https://github.com/vcs-python/libvcs.git')
```

Above: [`libvcs.cmd.git.Git`](https://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git) using
[`Git.clone()`](http://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git.clone).

## Repository Synchronization

Synchronize your repositories using the
[`libvcs.sync`](https://libvcs.git-pull.com/sync/) module.

### Clone and Update Repositories

```python
import pathlib
from libvcs.sync.git import GitSync

repo = GitSync(
   url="https://github.com/vcs-python/libvcs",
   path=pathlib.Path().cwd() / "my_repo",
   remotes={
       'gitlab': 'https://gitlab.com/vcs-python/libvcs'
   }
)

# Update / clone repo:
>>> repo.update_repo()

# Get revision:
>>> repo.get_revision()
u'5c227e6ab4aab44bf097da2e088b0ff947370ab8'
```

Above: [`libvcs.sync.git.GitSync`](https://libvcs.git-pull.com/projects/git.html#libvcs.sync.git.GitSync) repository
object using
[`GitSync.update_repo()`](https://libvcs.git-pull.com/sync/git.html#libvcs.sync.git.GitSync.update_repo)
and
[`GitSync.get_revision()`](https://libvcs.git-pull.com/sync/git.html#libvcs.sync.git.GitSync.get_revision).

## Pytest plugin: Temporary VCS repositories for testing

libvcs [pytest plugin](https://libvcs.git-pull.com/pytest-plugin.html) provides [py.test fixtures] to swiftly create local VCS repositories and working repositories to test with. Repositories are automatically cleaned on test teardown.

[py.test fixtures]: https://docs.pytest.org/en/8.2.x/explanation/fixtures.html

### Use temporary, local VCS in py.test

```python
import pathlib

from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
from libvcs.sync.git import GitSync


def test_repo_git_remote_checkout(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(path=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()
```

Under the hood: fixtures bootstrap a temporary `$HOME` environment in a
[`TmpPathFactory`](https://docs.pytest.org/en/7.1.x/reference/reference.html#tmp-path-factory-factory-api)
for automatic cleanup and `pytest-xdist` compatibility..

## Donations

Your donations fund development of new features, testing and support. Your money will go directly to
maintenance and development of the project. If you are an individual, feel free to give whatever
feels right for the value you get out of the project.

See donation options at <https://tony.sh/support.html>.

## More information

- Python support: 3.9+, pypy
- VCS supported: git(1), svn(1), hg(1)
- Source: <https://github.com/vcs-python/libvcs>
- Docs: <https://libvcs.git-pull.com>
- Changelog: <https://libvcs.git-pull.com/history.html>
- APIs for git, hg, and svn:
  - [`libvcs.url`](https://libvcs.git-pull.com/url/): URL Parser
  - [`libvcs.cmd`](https://libvcs.git-pull.com/cmd/): Commands
  - [`libvcs.sync`](https://libvcs.git-pull.com/sync/): Clone and update
- Issues: <https://github.com/vcs-python/libvcs/issues>
- Test Coverage: <https://codecov.io/gh/vcs-python/libvcs>
- pypi: <https://pypi.python.org/pypi/libvcs>
- Open Hub: <https://www.openhub.net/p/libvcs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/vcs-python/libvcs/workflows/docs/badge.svg)](https://libvcs.git-pull.com/)
[![Build Status](https://github.com/vcs-python/libvcs/workflows/tests/badge.svg)](https://github.com/vcs-python/libvcs/actions?query=workflow%3A%22tests%22)
