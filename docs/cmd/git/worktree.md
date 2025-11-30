# `worktree`

For `git-worktree(1)`.

## Overview

Manage git worktrees using {class}`~libvcs.cmd.git.GitWorktreeManager` (collection-level)
and {class}`~libvcs.cmd.git.GitWorktreeCmd` (per-worktree operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# List all worktrees
worktrees = git.worktrees.ls()

# Add a new worktree
git.worktrees.add(path='/path/to/worktree', branch='feature-branch')

# Get a specific worktree and operate on it
wt = git.worktrees.get(worktree_path='/path/to/worktree')
wt.lock(reason='Do not delete')
wt.unlock()
wt.remove()

# Prune stale worktrees
git.worktrees.prune()
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
