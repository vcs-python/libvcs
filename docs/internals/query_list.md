# List querying - `libvcs._internal.query_list`

`QueryList` is the backbone of the Manager/Cmd pattern. Every `ls()` method in
libvcs returns a `QueryList`, enabling chainable filtering on the results.

## How It's Used

All Manager classes return `QueryList` from their `ls()` methods —
`git.branches.ls()` yields `QueryList[GitBranchCmd]`, `git.tags.ls()` yields
`QueryList[GitTagCmd]`, and so on:

```python
>>> from libvcs.cmd.git import Git
>>> from libvcs._internal.query_list import QueryList
>>> git = Git(path=example_git_repo.path)
>>> isinstance(git.branches.ls(), QueryList)
True
>>> isinstance(git.tags.ls(), QueryList)
True
>>> isinstance(git.remotes.ls(), QueryList)
True
```

## Filtering

`QueryList` extends Python's built-in `list` with Django-style lookups.
Filter on any attribute of the contained objects — exact by default, or with
a lookup suffix:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='feature-a')
''
>>> git.branches.ls().filter(branch_name='master')  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=master>]
>>> git.branches.ls().filter(branch_name__icontains='FEATURE')  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=feature-a>]
```

Lookups traverse nested structures with `__` as well:

```python
>>> from libvcs._internal.query_list import QueryList
>>> cities = QueryList([
...     {'city': 'Tampa', 'weather': {'sky': 'sunny'}},
...     {'city': 'Chicago', 'weather': {'sky': 'windy'}},
... ])
>>> cities.filter(weather__sky='sunny')
[{'city': 'Tampa', 'weather': {'sky': 'sunny'}}]
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

Filters can be chained and combined — multiple conditions in one call AND
together, and `get()` retrieves exactly one match:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='feature-login')
''
>>> git.branches.create(branch='feature-signup')
''
>>> git.branches.ls().filter(
...     branch_name__startswith='feature',
...     branch_name__endswith='login',
... )  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=feature-login>]
>>> git.branches.ls().filter(
...     branch_name__contains='feature'
... ).filter(branch_name__contains='signup')  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=feature-signup>]
>>> branch = git.branches.get(branch_name='master')
>>> branch.branch_name
'master'
```

## API Reference

```{eval-rst}
.. automodule:: libvcs._internal.query_list
   :members:
```
