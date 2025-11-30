# `tag`

For `git-tag(1)`.

## Overview

Manage git tags using {class}`~libvcs.cmd.git.GitTagManager` (collection-level)
and {class}`~libvcs.cmd.git.GitTagCmd` (per-tag operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Create a tag
git.tags.create(name='v1.0.0', message='Release 1.0.0')

# List all tags
tags = git.tags.ls()

# Filter tags
release_tags = git.tags.ls(pattern='v*')

# Get a specific tag and operate on it
tag = git.tags.get(tag_name='v1.0.0')
tag.show()
tag.delete()
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitTagManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitTagCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
