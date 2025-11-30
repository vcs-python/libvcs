(querylist-filtering)=

# QueryList Filtering

libvcs uses `QueryList` to enable Django-style filtering on git entities.
Every `ls()` method returns a `QueryList`, letting you filter branches, tags,
remotes, and more with a fluent, chainable API.

## Basic Filtering

The `filter()` method accepts keyword arguments with optional lookup suffixes:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> branches = git.branches.ls()
>>> len(branches) >= 1  # At least master branch
True
```

### Exact Match

The default lookup is `exact`:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # These are equivalent
>>> git.branches.ls().filter(branch_name='master')  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=master>]
>>> git.branches.ls().filter(branch_name__exact='master')  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=master>]
```

### Contains and Startswith

Use suffixes for partial matching:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Create branches for this example
>>> git.branches.create(branch='feature-docs')
''
>>> git.branches.create(branch='feature-tests')
''
>>> git.branches.create(branch='bugfix-typo')
''
>>> # Branches containing 'feature'
>>> feature_branches = git.branches.ls().filter(branch_name__contains='feature')
>>> len(feature_branches) >= 2
True
>>> # Branches starting with 'bug'
>>> bugfix_branches = git.branches.ls().filter(branch_name__startswith='bug')
>>> len(bugfix_branches) >= 1
True
```

## Available Lookups

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

## Getting a Single Item

Use `get()` to retrieve exactly one matching item:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> branch = git.branches.get(branch_name='master')
>>> branch.branch_name
'master'
```

If no match or multiple matches are found, `get()` raises an exception.

## Chaining Filters

Filters can be chained for complex queries:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Create branches for this example
>>> git.branches.create(branch='feature-login')
''
>>> git.branches.create(branch='feature-signup')
''
>>> # Multiple conditions in one filter (AND)
>>> git.branches.ls().filter(
...     branch_name__startswith='feature',
...     branch_name__endswith='signup'
... )  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=feature-signup>]
>>> # Chained filters (also AND)
>>> git.branches.ls().filter(
...     branch_name__contains='feature'
... ).filter(
...     branch_name__contains='login'
... )  # doctest: +ELLIPSIS
[<GitBranchCmd ... branch_name=feature-login>]
```

## Working with Tags

The same filtering works on tags:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v1.0.0', message='Release 1.0')
''
>>> git.tags.create(name='v1.1.0', message='Release 1.1')
''
>>> git.tags.create(name='v2.0.0-beta', message='Beta release')
''
>>> # Filter tags by version pattern
>>> v1_tags = git.tags.ls().filter(tag_name__startswith='v1')
>>> len(v1_tags)
2
>>> # Find beta releases
>>> beta_tags = git.tags.ls().filter(tag_name__contains='beta')
>>> len(beta_tags)
1
```

## Regex Filtering

For complex patterns, use regex lookups:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Create tags for regex example
>>> git.tags.create(name='v3.0.0', message='Release 3.0')
''
>>> git.tags.create(name='v3.1.0', message='Release 3.1')
''
>>> # Match semantic version tags
>>> results = git.tags.ls().filter(tag_name__regex=r'^v\d+\.\d+\.\d+$')
>>> len(results) >= 2
True
```

## API Reference

See {class}`~libvcs._internal.query_list.QueryList` for the complete API.
