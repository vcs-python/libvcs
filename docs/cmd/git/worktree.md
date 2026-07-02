# `worktree`

For `git-worktree(1)`.

## Overview

Manage git worktrees using {class}`~libvcs.cmd.git.GitWorktreeManager` (collection-level)
and {class}`~libvcs.cmd.git.GitWorktreeCmd` (per-worktree operations).

### Examples

Add a worktree checked out at `HEAD`, then look it up — the main worktree
always exists, so the list grows to two:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.worktrees.add(path=tmp_path / 'example-worktree', commit_ish='HEAD')  # doctest: +ELLIPSIS
'HEAD is now at ...'
>>> worktrees = git.worktrees.ls()
>>> len(worktrees) >= 2
True
>>> wt = git.worktrees.get(worktree_path=worktrees[0].worktree_path)
>>> wt.worktree_path == worktrees[0].worktree_path
True
```

Prune stale worktree metadata:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.worktrees.prune()
''
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitWorktreeManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitWorktreeCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
