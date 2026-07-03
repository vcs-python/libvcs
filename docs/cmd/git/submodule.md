# `submodule`

For [`git-submodule(1)`](https://git-scm.com/docs/git-submodule).

## Overview

Manage git submodules using {class}`~libvcs.cmd.git.GitSubmoduleManager` (collection-level)
and {class}`~libvcs.cmd.git.GitSubmoduleEntryCmd` (per-submodule operations).

:::{note}
{class}`~libvcs.cmd.git.GitSubmoduleCmd` is the legacy interface. Use `git.submodules`
({class}`~libvcs.cmd.git.GitSubmoduleManager`) for the new
{ref}`Manager/Cmd pattern <traversing-git-repos>`.
:::

### Examples

List submodules — a repository without any simply returns an empty list — and
sync submodule URLs into `.git/config`:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.submodules.ls()
[]
>>> git.submodules.sync()
''
```

Register a submodule with {meth}`~libvcs.cmd.git.GitSubmoduleManager.add`,
then initialize and fetch it through the entry's
{meth}`~libvcs.cmd.git.GitSubmoduleEntryCmd.init` and
{meth}`~libvcs.cmd.git.GitSubmoduleEntryCmd.update` — each method's API
reference below carries a runnable example.

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
