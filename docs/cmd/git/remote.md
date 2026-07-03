# `remote`

For [`git-remote(1)`](https://git-scm.com/docs/git-remote).

## Overview

Manage git remotes using {class}`~libvcs.cmd.git.GitRemoteManager` (collection-level)
and {class}`~libvcs.cmd.git.GitRemoteCmd` (per-remote operations).

### Examples

List remotes — a freshly cloned repository has its `origin`:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.remotes.ls()  # doctest: +ELLIPSIS
[<GitRemoteCmd path=... remote_name=origin>]
```

Add a remote:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.remotes.add(name='upstream', url='https://github.com/org/repo.git')
''
```

Get a specific remote and operate on it through its Cmd object:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> origin = git.remotes.get(remote_name='origin')
>>> 'origin' in origin.show()
True
>>> origin.prune()
''
>>> origin.set_url(url='https://example.com/new.git')
''
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitRemoteManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitRemoteCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
