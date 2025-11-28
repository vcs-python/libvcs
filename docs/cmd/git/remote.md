# `remote`

For `git-remote(1)`.

## Overview

Manage git remotes using {class}`~libvcs.cmd.git.GitRemoteManager` (collection-level)
and {class}`~libvcs.cmd.git.GitRemoteCmd` (per-remote operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# List all remotes
remotes = git.remotes.ls()

# Add a new remote
git.remotes.add(name='upstream', url='https://github.com/org/repo.git')

# Get a specific remote and operate on it
origin = git.remotes.get(remote_name='origin')
origin.show()
origin.prune()
origin.set_url('https://new-url.git')
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
