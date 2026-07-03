# `tag`

For [`git-tag(1)`](https://git-scm.com/docs/git-tag).

## Overview

Manage git tags using {class}`~libvcs.cmd.git.GitTagManager` (collection-level)
and {class}`~libvcs.cmd.git.GitTagCmd` (per-tag operations).

### Examples

Create a tag, then list tags — optionally narrowed to a pattern:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v1.0.0', message='Release 1.0.0')
''
>>> tags = git.tags.ls()
>>> len(tags) >= 1
True
>>> release_tags = git.tags.ls(pattern='v*')  # doctest: +ELLIPSIS
>>> release_tags[0].tag_name
'v1.0.0'
```

Get a specific tag and operate on it through its Cmd object:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v2.0.0', message='Release 2.0.0')
''
>>> tag = git.tags.get(tag_name='v2.0.0')
>>> tag.show()  # doctest: +ELLIPSIS
'tag v2.0.0...'
>>> tag.delete()  # doctest: +ELLIPSIS
"Deleted tag 'v2.0.0' ..."
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
