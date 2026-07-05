# `reflog`

For [`git-reflog(1)`](https://git-scm.com/docs/git-reflog).

## Overview

Manage git reflog using {class}`~libvcs.cmd.git.GitReflogManager`
(collection-level), {class}`~libvcs.cmd.git.GitReflogEntry` (entry data), and
{class}`~libvcs.cmd.git.GitReflogEntryCmd` (per-entry operations).

### Examples

List reflog entries and look one up by refspec:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> entries = git.reflog.ls()
>>> len(entries) >= 1
True
>>> entry = git.reflog.get(refspec='HEAD@{0}')
>>> entry.refspec
'HEAD@{0}'
```

Check whether a ref has a reflog:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.reflog.exists('HEAD')
True
```

Expire old reflog entries:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.reflog.expire(expire='90.days.ago')
''
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
