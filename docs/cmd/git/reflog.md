# `reflog`

For `git-reflog(1)`.

## Overview

Manage git reflog using {class}`~libvcs.cmd.git.GitReflogManager` (collection-level)
and {class}`~libvcs.cmd.git.GitReflogEntryCmd` (per-entry operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# List reflog entries
entries = git.reflog.ls()

# List entries for a specific ref
head_entries = git.reflog.ls(ref='HEAD')

# Check if reflog exists for a ref
git.reflog.exists(ref='main')

# Expire old reflog entries
git.reflog.expire(ref='HEAD', expire='90.days.ago')
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitReflogManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitReflogEntryCmd
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitReflogEntry
   :members:
   :show-inheritance:
   :undoc-members:
```
