# `stash`

For `git-stash(1)`.

## Overview

Manage git stashes using {class}`~libvcs.cmd.git.GitStashManager` (collection-level)
and {class}`~libvcs.cmd.git.GitStashEntryCmd` (per-stash operations).

:::{note}
{class}`~libvcs.cmd.git.GitStashCmd` is the legacy interface. Use `git.stashes`
({class}`~libvcs.cmd.git.GitStashManager`) for the new Manager/Cmd pattern.
:::

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Push changes to stash
git.stashes.push(message='Work in progress')

# List all stashes
stashes = git.stashes.ls()

# Get a specific stash and operate on it
stash = git.stashes.get(index=0)
stash.show()
stash.apply()
stash.drop()

# Clear all stashes
git.stashes.clear()
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitStashManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitStashEntryCmd
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitStashCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
