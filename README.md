# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

**Stop struggling with VCS command-line tools in Python.** libvcs gives you a clean, typed API to work with Git, Mercurial, and SVN repositories - parse URLs, run commands, and sync repos with just a few lines of code.

## Why Use libvcs?

- 🔄 **Manage multiple repos** without shell scripts or subprocess calls
- 🔍 **Parse and transform VCS URLs** between different formats
- 🧪 **Test code that interacts with repositories** using included pytest fixtures
- 🔒 **Type-safe operations** with full typing support

*Supports Python 3.9 and above, Git (including AWS CodeCommit), Subversion, and Mercurial.*

```console
$ pip install --user libvcs
```

---

## Quick Examples

### Parse and transform Git URLs
```python
>>> from libvcs.url.git import GitURL
>>> # Transform a GitHub URL to GitLab with one line
>>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')
>>> git_location.hostname = 'gitlab.com'  # Change is this simple!
>>> git_location.to_url()
'git@gitlab.com:vcs-python/libvcs.git'
```

### Clone and update repositories
```python
>>> from libvcs.sync.git import GitSync
>>> import pathlib
>>> # Set up our repository with options
>>> repo = GitSync(
...    url="https://github.com/vcs-python/libvcs",
...    path=pathlib.Path.cwd() / "my_repo",
...    remotes={
...        'gitlab': 'https://gitlab.com/vcs-python/libvcs'
...    }
... )
>>> # Operations are simple to understand
>>> # repo.obtain()  # Clone if needed
>>> # repo.update_repo()  # Pull latest changes
>>> # repo.get_revision()
>>> # '5c227e6ab4aab44bf097da2e088b0ff947370ab8'
```

### Validate repository URLs
```python
>>> from libvcs.url.git import GitURL
>>> # Quickly validate if a URL is a proper Git URL
>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
```

---

## Core Features

### 1. URL Detection and Parsing

Easily validate and parse VCS URLs using the [`libvcs.url`](https://libvcs.git-pull.com/url/index.html) module:

Parse URLs and modify them programmatically:

```python
>>> from libvcs.url.git import GitURL
>>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')
>>> git_location.path = 'vcs-python/vcspull'
>>> git_location.to_url()
'git@github.com:vcs-python/vcspull.git'
```

See more in the [parser documentation](https://libvcs.git-pull.com/parse/index.html).

### 2. Command Abstraction

Abstracts CLI commands for `git(1)`, `hg(1)`, `svn(1)` via a lightweight [`subprocess`](https://docs.python.org/3/library/subprocess.html) wrapper.

```python
import pathlib
from libvcs.cmd.git import Git

git = Git(path=pathlib.Path.cwd() / 'my_git_repo')
git.clone(url='https://github.com/vcs-python/libvcs.git')
```

Above: [`libvcs.cmd.git.Git`](https://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git) using
[`Git.clone()`](http://libvcs.git-pull.com/cmd/git.html#libvcs.cmd.git.Git.clone).

### 3. Repository Synchronization

Synchronize repositories using the [`libvcs.sync`](https://libvcs.git-pull.com/sync/) module.

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
# repo.update_repo()

# Get revision:
# repo.get_revision()
# '5c227e6ab4aab44bf097da2e088b0ff947370ab8'
```

### 4. Pytest Fixtures for Testing

libvcs [pytest plugin](https://libvcs.git-pull.com/pytest-plugin.html) provides [py.test fixtures] to create temporary VCS repositories for testing. Repositories are automatically cleaned on test teardown.

[py.test fixtures]: https://docs.pytest.org/en/8.2.x/explanation/fixtures.html

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
[`TempPathFactory`](https://docs.pytest.org/en/8.3.x/reference/reference.html#pytest.TempPathFactory)
for automatic cleanup and `pytest-xdist` compatibility.

---

## Documentation & Resources

- **Getting Started**: [Quickstart Guide](https://libvcs.git-pull.com/quickstart.html)
- **Full Documentation**: [libvcs.git-pull.com](https://libvcs.git-pull.com)
- **Changelog**: [History](https://libvcs.git-pull.com/history.html)
- **Source Code**: [GitHub](https://github.com/vcs-python/libvcs)
- **PyPI Package**: [libvcs](https://pypi.python.org/pypi/libvcs)

## API References

- [`libvcs.url`](https://libvcs.git-pull.com/url/): URL Parser
- [`libvcs.cmd`](https://libvcs.git-pull.com/cmd/): Commands
- [`libvcs.sync`](https://libvcs.git-pull.com/sync/): Clone and update

## Support

Your donations fund development of new features, testing and support. Your money will go directly to
maintenance and development of the project.

See donation options at <https://tony.sh/support.html>.

## About

- **Python support**: 3.9+, pypy
- **VCS supported**: git(1), svn(1), hg(1)
- **Issues**: <https://github.com/vcs-python/libvcs/issues>
- **Test Coverage**: <https://codecov.io/gh/vcs-python/libvcs>
- **License**: [MIT](https://opensource.org/licenses/MIT)

[![Docs](https://github.com/vcs-python/libvcs/workflows/docs/badge.svg)](https://libvcs.git-pull.com/)
[![Build Status](https://github.com/vcs-python/libvcs/workflows/tests/badge.svg)](https://github.com/vcs-python/libvcs/actions?query=workflow%3A%22tests%22)
