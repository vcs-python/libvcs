(traversing-git-repos)=

# Traversing Git Repos

libvcs provides **Manager** and **Cmd** classes for navigating the "object graph"
of your git repository. These aren't just convenient abstractions—they're also
simulacra of the git commands themselves, giving you typed Python objects instead
of raw strings.

## Overview

The pattern consists of two types of classes:

- **Manager** classes handle collection-level operations (`ls()`, `get()`,
  `filter()`, `add()`/`create()`)
- **Cmd** classes handle per-entity operations (`show()`, `remove()`,
  `rename()`)

```
Git instance
├── branches: GitBranchManager
│   ├── ls() -> QueryList[GitBranchCmd]
│   ├── get() -> GitBranchCmd
│   └── create()
├── tags: GitTagManager
├── remotes: GitRemoteManager
├── stashes: GitStashManager
├── worktrees: GitWorktreeManager
├── notes: GitNotesManager
├── submodules: GitSubmoduleManager
└── reflog: GitReflogManager
```

## Basic Usage

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
```

### Listing Items

All Manager classes have an `ls()` method that returns a
{class}`~libvcs._internal.query_list.QueryList`:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> branches = git.branches.ls()
>>> isinstance(branches, list)
True
>>> tags = git.tags.ls()
>>> remotes = git.remotes.ls()
```

### Getting a Single Item

Use `get()` with filter criteria to retrieve a single item:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v1.0.0', message='Release 1.0')
''
>>> tag = git.tags.get(tag_name='v1.0.0')
>>> tag.tag_name
'v1.0.0'
```

### Creating Items

Manager classes provide `create()` or `add()` methods:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v2.0.0', message='Release 2.0')
''
>>> git.branches.create(branch='feature-branch')
''
```

### Per-Entity Operations

Cmd objects have methods for mutating or inspecting that entity:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.tags.create(name='v3.0.0', message='Release 3.0')
''
>>> tag = git.tags.get(tag_name='v3.0.0')
>>> tag.delete()  # doctest: +ELLIPSIS
"Deleted tag 'v3.0.0' ..."
>>> git.branches.create(branch='temp-branch')
''
>>> branch = git.branches.get(branch_name='temp-branch')
>>> branch.delete()  # doctest: +ELLIPSIS
'Deleted branch temp-branch ...'
```

## Comparison to Raw Commands

### Before: Parsing Strings

Without the Manager/Cmd pattern, you'd parse raw output:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Raw output requires parsing
>>> raw_output = git.run(['tag', '-l'])
>>> tag_names = [t for t in raw_output.strip().split('\\n') if t]
```

### After: Typed Objects

With the Manager/Cmd pattern, you get typed objects:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> tags = git.tags.ls()
>>> for tag in tags:  # doctest: +SKIP
...     print(f"{tag.tag_name}")
```

## When to Use

| Use Case | Approach |
|----------|----------|
| List/filter/get entities | Manager class (`git.branches.ls()`) |
| Mutate a specific entity | Cmd class (`branch.delete()`) |
| Run arbitrary git commands | Direct methods (`git.run([...])`) |
| Complex pipelines | Mix of both |

## Available Managers

| Manager | Access | Operations |
|---------|--------|------------|
| {class}`~libvcs.cmd.git.GitBranchManager` | `git.branches` | List, create, checkout branches |
| {class}`~libvcs.cmd.git.GitTagManager` | `git.tags` | List, create tags |
| {class}`~libvcs.cmd.git.GitRemoteManager` | `git.remotes` | List, add, configure remotes |
| {class}`~libvcs.cmd.git.GitStashManager` | `git.stashes` | List, push, clear stashes |
| {class}`~libvcs.cmd.git.GitWorktreeManager` | `git.worktrees` | List, add, prune worktrees |
| {class}`~libvcs.cmd.git.GitNotesManager` | `git.notes` | List, add, prune notes |
| {class}`~libvcs.cmd.git.GitSubmoduleManager` | `git.submodules` | List, add, sync submodules |
| {class}`~libvcs.cmd.git.GitReflogManager` | `git.reflog` | List, expire reflog entries |

See {doc}`/cmd/git/index` for the complete API reference.
