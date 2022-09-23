# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

libvcs is a lite, [typed](https://docs.python.org/3/library/typing.html), pythonic tool box for
detection and parsing of URLs, commanding, and syncing with `git`, `hg`, and `svn`. Powers
[vcspull](https://www.github.com/vcs-python/vcspull/).

## Overview

Features for Git, Subversion, and Mercurial:

- **Detect and parse** VCS URLs
- **Command** VCS via python API
- **Sync** repos locally
- **Test fixtures** for temporary local repos and working copies

To **get started**, see the [quickstart](https://libvcs.git-pull.com/quickstart.html) for more.

```console
$ pip install --user libvcs
```

## URL Parser

You can validate and parse Git, Mercurial, and Subversion URLs through
[`libvcs.url`](https://libvcs.git-pull.com/url/index.html):

Validate:

```python
>>> from libvcs.url.git import GitURL

>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
```

Parse and adjust a Git URL:

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

## Commands

Simple [`subprocess`](https://docs.python.org/3/library/subprocess.html) wrappers around `git(1)`,
`hg(1)`, `svn(1)`. Here is [`Git`](https://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git) w/
[`Git.clone`](http://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git.clone):

```python
import pathlib
from libvcs.cmd.git import Git

git = Git(dir=pathlib.Path.cwd() / 'my_git_repo')
git.clone(url='https://github.com/vcs-python/libvcs.git')
```

## Sync

Create a [`GitSync`](https://libvcs.git-pull.com/projects/git.html#libvcs.sync.git.GitProject)
object of the project to inspect / checkout / update:

```python
import pathlib
from libvcs.sync.git import GitSync

repo = GitSync(
   url="https://github.com/vcs-python/libvcs",
   dir=pathlib.Path().cwd() / "my_repo",
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

## Pytest plugin

libvcs also provides a test rig for local repositories. It automatically can provide clean local
repositories and working copies for git, svn, and mercurial. They are automatically cleaned up after
each test.

It works by bootstrapping a temporary `$HOME` environment in a
[`TmpPathFactory`](https://docs.pytest.org/en/7.1.x/reference/reference.html#tmp-path-factory-factory-api)
for automatic cleanup.

```python
import pathlib

from libvcs.pytest_plugin import CreateProjectCallbackFixtureProtocol
from libvcs.sync.git import GitSync


def test_repo_git_remote_checkout(
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(dir=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()
```

Learn more on the docs at https://libvcs.git-pull.com/pytest-plugin.html

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
