# `stash`

For `git-stash(1)`.

## Overview

Manage git stashes using {class}`~libvcs.cmd.git.GitStashManager` (collection-level)
and {class}`~libvcs.cmd.git.GitStashEntryCmd` (per-stash operations).

:::{note}
{class}`~libvcs.cmd.git.GitStashCmd` is the legacy interface. Use `git.stashes`
({class}`~libvcs.cmd.git.GitStashManager`) for the new Manager/Cmd pattern.
:::

### Examples

Stash work in progress, inspect it, restore it, then clear the stash list:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> _ = (example_git_repo.path / 'testfile.test').write_text('wip', encoding='utf-8')
>>> git.stashes.push(message='Work in progress')  # doctest: +ELLIPSIS
'Saved working directory and index state ...'
>>> stashes = git.stashes.ls()
>>> len(stashes)
1
>>> stash = git.stashes.get(index=0)
>>> stash.show()  # doctest: +ELLIPSIS
'...testfile.test...'
>>> stash.apply()  # doctest: +ELLIPSIS
'...'
>>> git.stashes.clear()
''
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
