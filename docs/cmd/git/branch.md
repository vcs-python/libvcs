# `branch`

For [`git-branch(1)`](https://git-scm.com/docs/git-branch).

## Overview

Manage git branches using {class}`~libvcs.cmd.git.GitBranchManager` (collection-level)
and {class}`~libvcs.cmd.git.GitBranchCmd` (per-branch operations).

### Examples

List branches — local by default, remote with `remotes=True`:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> branches = git.branches.ls()
>>> len(branches) >= 1
True
>>> remote_branches = git.branches.ls(remotes=True)
>>> isinstance(remote_branches, list)
True
```

Create a branch, then look it up:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='feature-branch')
''
>>> branch = git.branches.get(branch_name='feature-branch')
>>> branch.branch_name
'feature-branch'
```

Rename or delete a branch through its Cmd object:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='old-name')
''
>>> branch = git.branches.get(branch_name='old-name')
>>> branch.rename('new-feature')
''
>>> renamed = git.branches.get(branch_name='new-feature')
>>> renamed.delete()  # doctest: +ELLIPSIS
'Deleted branch new-feature ...'
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
