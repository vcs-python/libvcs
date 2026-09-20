(git-partial-clone-filters)=

# Partial-clone filters

{mod}`libvcs.cmd.git_filter` validates Git object filters before a command
creates a checkout or starts a process. The frozen models cover Git's current
filter grammar:

| Model | Git specification | Meaning |
| --- | --- | --- |
| {class}`~libvcs.cmd.git_filter.BlobNone` | `blob:none` | Omit blobs until Git needs them |
| {class}`~libvcs.cmd.git_filter.BlobLimit` | `blob:limit=n[kmg]` | Omit blobs at or above the byte limit |
| {class}`~libvcs.cmd.git_filter.TreeDepth` | `tree:n` | Include trees through depth `n` |
| {class}`~libvcs.cmd.git_filter.ObjectType` | `object:type=TYPE` | Include one of `blob`, `tree`, `commit`, or `tag` |
| {class}`~libvcs.cmd.git_filter.SparseOid` | `sparse:oid=OID` | Read sparse patterns from an object |
| {class}`~libvcs.cmd.git_filter.Auto` | `auto` | Ask Git to choose a server-recommended filter |
| {class}`~libvcs.cmd.git_filter.Combine` | `combine:FILTER+FILTER` | Apply every encoded child filter |

Build a model directly, parse a Git specification, or coerce a kind-tagged
mapping:

```python
>>> from libvcs.cmd.git_filter import BlobLimit, coerce_filter, parse_filter
>>> BlobLimit("4m")
BlobLimit(limit='4m')
>>> parse_filter("tree:2")
TreeDepth(depth=2)
>>> coerce_filter({"kind": "object:type", "type": "commit"})
ObjectType(type='commit')
```

{func}`~libvcs.cmd.git_filter.coerce_filter` turns a nonempty sequence into a
{class}`~libvcs.cmd.git_filter.Combine`. Command methods preserve a top-level
sequence as repeated flags instead:

```python
>>> from libvcs.cmd.git_filter import (
...     BlobNone,
...     TreeDepth,
...     coerce_filter,
...     filter_specs,
... )
>>> coerce_filter([BlobNone(), TreeDepth(1)])
Combine(filters=(BlobNone(), TreeDepth(depth=1)))
>>> filter_specs([BlobNone(), TreeDepth(1)])
('blob:none', 'tree:1')
```

Pass the same accepted values to `_filter` on
{meth}`~libvcs.cmd.git.Git.clone`, {meth}`~libvcs.cmd.git.Git.fetch`,
{meth}`~libvcs.cmd.git.Git.pull`, or
{meth}`~libvcs.cmd.git.GitSubmoduleCmd.update`. Existing string values remain
valid.

## Validation limits

Blob limits and tree depths range from zero through
`18446744073709551615`. A `k`, `m`, or `g` suffix uses powers of 1024, and the
expanded byte count must remain within that range. Boolean values are not
integers for these fields.

Combine filters percent-encode whitespace, percent, plus, and Git's reserved
characters. Parsing rejects malformed escapes, decoded NUL bytes, empty child
filters, and nesting beyond 32 levels. `auto` cannot be combined with another
filter.

`auto` requires Git 2.54 or newer. libvcs passes it only to `git clone` and
`git fetch`; an older Git reports the capability error. `git pull` and `git
submodule update` reject it before starting Git.

```{eval-rst}
.. automodule:: libvcs.cmd.git_filter
   :members:
   :show-inheritance:
```
