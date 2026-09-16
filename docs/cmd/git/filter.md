# `filter`

For partial clones with [`git clone --filter=<filter-spec>`](https://git-scm.com/docs/git-clone#Documentation/git-clone.txt---filterltfilter-specgt).

## Overview

A partial clone downloads every commit, and leaves out objects the filter
excludes until a command needs them. `blob:none` keeps full history but
fetches file contents only for the checkout.

{mod}`libvcs.cmd.git_filter` models git's filter grammar as small, typed
objects. Pass one, a spec string, or a list of either as `_filter` to
{meth}`~libvcs.cmd.git.Git.clone`, {meth}`~libvcs.cmd.git.Git.fetch`,
{meth}`~libvcs.cmd.git.Git.pull`, and
{meth}`~libvcs.cmd.git.GitSubmoduleCmd.update`, or as `git_filter` to
{class}`~libvcs.sync.git.GitSync`.

The remote must allow filtering; a server that does not support it sends a
full clone instead, with a warning.

### Examples

Build filters and render them as git spec strings:

```python
>>> from libvcs.cmd.git_filter import BlobLimit, BlobNone, Combine, TreeDepth
>>> str(BlobNone())
'blob:none'
>>> str(Combine(filters=(BlobLimit(size='1m'), TreeDepth(depth=3))))
'combine:blob:limit=1m+tree:3'
```

Turn spec strings and config mappings back into filters:

```python
>>> from libvcs.cmd.git_filter import from_mapping, parse_filter
>>> parse_filter('blob:limit=1k')
BlobLimit(size='1k')
>>> from_mapping({'kind': 'tree', 'depth': 0})
TreeDepth(depth=0)
```

Clone with a filter:

```python
from libvcs.sync.git import GitSync

repo = GitSync(
    url="https://github.com/vcs-python/libvcs",
    path="libvcs",
    git_filter="blob:none",
)
repo.obtain()
```

## API Reference

```{eval-rst}
.. automodule:: libvcs.cmd.git_filter
   :members:
   :show-inheritance:
   :exclude-members: _COMBINE_RESERVED_CHARS,
     _MAPPING_FIELDS,
     _decode_combine_part,
     _encode_combine_part
```
