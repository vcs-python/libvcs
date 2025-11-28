# List querying - `libvcs._internal.query_list`

`QueryList` is the backbone of the Manager/Cmd pattern. Every `ls()` method in
libvcs returns a `QueryList`, enabling chainable filtering on the results.

## How It's Used

All Manager classes return `QueryList` from their `ls()` methods:

```python
from libvcs.cmd.git import Git

git = Git(path='/path/to/repo')

# Each ls() returns a QueryList
branches = git.branches.ls()    # QueryList[GitBranchCmd]
tags = git.tags.ls()            # QueryList[GitTagCmd]
remotes = git.remotes.ls()      # QueryList[GitRemoteCmd]
stashes = git.stashes.ls()      # QueryList[GitStashEntryCmd]
worktrees = git.worktrees.ls()  # QueryList[GitWorktreeCmd]
```

## Filtering

`QueryList` extends Python's built-in `list` with Django-style lookups:

```python
# Exact match
branches.filter(name='main')

# Case-insensitive contains
branches.filter(name__icontains='feature')

# Nested attribute access
branches.filter(commit__sha__startswith='abc123')
```

### Available Lookups

| Lookup | Description |
|--------|-------------|
| `exact` | Exact match (default) |
| `iexact` | Case-insensitive exact match |
| `contains` | Substring match |
| `icontains` | Case-insensitive substring |
| `startswith` | Prefix match |
| `istartswith` | Case-insensitive prefix |
| `endswith` | Suffix match |
| `iendswith` | Case-insensitive suffix |
| `in` | Value in list |
| `nin` | Value not in list |
| `regex` | Regular expression match |
| `iregex` | Case-insensitive regex |

### Chaining

Filters can be chained and combined:

```python
# Multiple conditions (AND)
branches.filter(name__startswith='feature', is_remote=False)

# Get single result
branches.get(name='main')

# Chain filters
branches.filter(is_remote=True).filter(name__contains='release')
```

## API Reference

```{eval-rst}
.. automodule:: libvcs._internal.query_list
   :members:
```
