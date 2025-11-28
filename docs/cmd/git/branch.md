# `branch`

For `git-branch(1)`.

## Overview

Manage git branches using {class}`~libvcs.cmd.git.GitBranchManager` (collection-level)
and {class}`~libvcs.cmd.git.GitBranchCmd` (per-branch operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# List all branches
branches = git.branches.ls()

# List remote branches only
remote_branches = git.branches.ls(remotes=True)

# Create a new branch
git.branches.create('feature-branch')

# Get a specific branch and operate on it
branch = git.branches.get(branch_name='feature-branch')
branch.rename('new-feature')
branch.delete()
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitBranchManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitBranchCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
