# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

libvcs is a lite, [typed](https://docs.python.org/3/library/typing.html), pythonic tool box for
detection and parsing of URLs, commanding, and syncing with `git`, `hg`, and `svn`. Powers
[vcspull](https://www.github.com/vcs-python/vcspull/).

## Overview

Features for git, Subversion, and Mercurial:

- **Detect and parse** VCS URLs
- **Command** VCS via python API
- **Sync** repos locally

To **get started**, see the [quickstart](https://libvcs.git-pull.com/quickstart.html) for more.

```console
$ pip install --user libvcs
```

## URL Parsing (experimental)

You can validate and parse git, Mercurial, and Subversion URLs through
[`libvcs.parse`](https://libvcs.git-pull.com/parse/index.html):

Validate:

```python
>>> from libvcs.parse.git import GitUrl

>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
```

Parse and adjust a git url:

```
from libvcs.parse.git import GitUrl

>>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')

>>> git_location
GitURL(url=git@github.com:vcs-python/libvcs.git,
        hostname=github.com,
        path=vcs-python/libvcs,
        user=git,
        suffix=.git,
        matcher=core-git-scp)
```

Switch repo libvcs -> vcspull:

```python
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

## Commands (experimental)

Simple [`subprocess`](https://docs.python.org/3/library/subprocess.html) wrappers around `git(1)`,
`hg(1)`, `svn(1)`. Here is [`Git`](https://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git) w/
[`Git.clone`](http://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git.clone):

```python
import pathlib
from libvcs.cmd.git import Git

git = Git(dir=pathlib.Path.cwd() / 'my_git_repo')
git.clone(url='https://github.com/vcs-python/libvcs.git')
```

## Projects

Create a
[`GitProject`](https://libvcs.git-pull.com/projects/git.html#libvcs.projects.git.GitProject) object
of the project to inspect / checkout / update:

```python
import pathlib
from libvcs.projects.git import GitProject

repo = GitProject(
   url="https://github.com/vcs-python/libvcs",
   dir=pathlib.Path().cwd() / "my_repo",
   remotes={
       'gitlab': 'https://gitlab.com/vcs-python/libvcs'
   }
)
```

Update / clone repo:

```python
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
- API:
  - [`libvcs.cmd`](https://libvcs.git-pull.com/cmd/): Commands
  - [`libvcs.projects`](https://libvcs.git-pull.com/projects/): High-level synchronization commands
- Issues: <https://github.com/vcs-python/libvcs/issues>
- Test Coverage: <https://codecov.io/gh/vcs-python/libvcs>
- pypi: <https://pypi.python.org/pypi/libvcs>
- Open Hub: <https://www.openhub.net/p/libvcs>
- License: [MIT](https://opensource.org/licenses/MIT).

[![Docs](https://github.com/vcs-python/libvcs/workflows/docs/badge.svg)](https://libvcs.git-pull.com/)
[![Build Status](https://github.com/vcs-python/libvcs/workflows/tests/badge.svg)](https://github.com/vcs-python/libvcs/actions?query=workflow%3A%22tests%22)
