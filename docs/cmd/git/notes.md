# `notes`

For `git-notes(1)`.

## Overview

Manage git notes using {class}`~libvcs.cmd.git.GitNotesManager` (collection-level)
and {class}`~libvcs.cmd.git.GitNoteCmd` (per-note operations).

### Examples

Add a note to the current commit (`object_sha` defaults to `HEAD`), then list
notes:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.notes.add(message='This is a note')
''
>>> notes = git.notes.ls()
>>> len(notes) >= 1
True
```

Operate on a note through its Cmd object — show it, append to it, remove it:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.notes.add(message='Reviewed by Alice')
''
>>> note = git.notes.ls()[0]
>>> note.show()
'Reviewed by Alice\n'
>>> note.append(message='Additional info')
''
>>> note.remove()  # doctest: +ELLIPSIS
'...'
```

Prune notes attached to objects that no longer exist:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.notes.prune()
''
```

## API Reference

```{eval-rst}
.. autoclass:: libvcs.cmd.git.GitNotesManager
   :members:
   :show-inheritance:
   :undoc-members:

.. autoclass:: libvcs.cmd.git.GitNoteCmd
   :members:
   :show-inheritance:
   :undoc-members:
```
