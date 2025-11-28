# `submodule`

For `git-submodule(1)`.

## Overview

Manage git submodules using {class}`~libvcs.cmd.git.GitSubmoduleManager` (collection-level)
and {class}`~libvcs.cmd.git.GitSubmoduleEntryCmd` (per-submodule operations).

:::{note}
{class}`~libvcs.cmd.git.GitSubmoduleCmd` is the legacy interface. Use `git.submodules`
({class}`~libvcs.cmd.git.GitSubmoduleManager`) for the new Manager/Cmd pattern.
:::

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Add a submodule
git.submodules.add(url='https://github.com/org/lib.git', path='vendor/lib')

# List all submodules
submodules = git.submodules.ls()

# Get a specific submodule and operate on it
submodule = git.submodules.get(path='vendor/lib')
submodule.init()
submodule.update()
submodule.deinit()

# Sync submodule URLs
git.submodules.sync()
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitSubmoduleManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitSubmodule
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitSubmoduleEntryCmd
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitSubmoduleCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
