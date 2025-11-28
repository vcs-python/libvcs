(quickstart)=

# Quickstart

## Installation

For latest official version:

```console
$ pip install --user libvcs
```

Upgrading:

```console
$ pip install --user --upgrade libvcs
```

(developmental-releases)=

### Developmental releases

New versions of libvcs are published to PyPI as alpha, beta, or release candidates.
In their versions you will see notification like `a1`, `b1`, and `rc1`, respectively.
`1.10.0b4` would mean the 4th beta release of `1.10.0` before general availability.

- [pip]\:

  ```console
  $ pip install --user --upgrade --pre libvcs
  ```

- [uv]\:

  ```console
  $ uv add libvcs --prerelease allow
  ```

via trunk (can break easily):

- [pip]\:

  ```console
  $ pip install --user -e git+https://github.com/vcs-python/libvcs.git#egg=libvcs
  ```

- [uv]\:

  ```console
  $ uv add "git+https://github.com/vcs-python/libvcs.git"
  ```

[pip]: https://pip.pypa.io/en/stable/
[uv]: https://docs.astral.sh/uv/

## Basic Usage

### Commands

Run git commands directly using {class}`~libvcs.cmd.git.Git`:

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Initialize a new repository
git.init()

# Clone a repository
git.clone(url='https://github.com/vcs-python/libvcs.git')

# Check status
git.status()
```

### Subcommand Managers

Work with branches, tags, remotes, and more using the Manager/Cmd pattern:

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# List and filter branches
branches = git.branches.ls()
remote_branches = git.branches.ls(remotes=True)

# Create and manage tags
git.tags.create(name='v1.0.0', message='Release 1.0')
tag = git.tags.get(tag_name='v1.0.0')

# Work with remotes
remotes = git.remotes.ls()
origin = git.remotes.get(remote_name='origin')
origin.prune()
```

See {doc}`/cmd/git/index` for the full API reference.
