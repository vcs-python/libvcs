# `notes`

For `git-notes(1)`.

## Overview

Manage git notes using {class}`~libvcs.cmd.git.GitNotesManager` (collection-level)
and {class}`~libvcs.cmd.git.GitNoteCmd` (per-note operations).

### Example

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Add a note to a commit
git.notes.add(object='HEAD', message='This is a note')

# List all notes
notes = git.notes.ls()

# Get a specific note and operate on it
note = git.notes.get(object='HEAD')
note.show()
note.append(message='Additional info')
note.remove()

# Prune notes for non-existent objects
git.notes.prune()
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
