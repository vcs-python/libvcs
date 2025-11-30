(traversing-git-repos)=

# Traversing Git Repos

libvcs provides **Managers** and **Commands** for intuitively traversing and
navigating entities in a git repository—branches, tags, remotes, stashes, and
more—with ORM-like convenience via {class}`~libvcs._internal.query_list.QueryList`.

## Overview

The pattern consists of two types of classes:

- **Managers** (`git.branches`, `git.tags`, etc.) let you traverse repository
  entities intuitively, listing, filtering, and retrieving them with ORM-like
  convenience
- **Commands** are contextual ways to run git commands against a specific target
  entity (e.g., delete a branch, rename a tag, set a remote's URL)

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

Without Managers and Commands, you'd parse raw output:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Raw output requires parsing
>>> raw_output = git.run(['tag', '-l'])
>>> tag_names = [t for t in raw_output.strip().split('\\n') if t]
```

### After: Typed Objects

With Managers and Commands, you get typed objects:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> tags = git.tags.ls()
>>> for tag in tags:  # doctest: +SKIP
...     print(f"{tag.tag_name}")
```

## Working with Remotes

Add and configure remote repositories:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.remotes.add(name='upstream', url='https://github.com/vcs-python/libvcs.git')
''
>>> remotes = git.remotes.ls()
>>> len(remotes) >= 1
True
```

Get a remote and update its URL:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.remotes.add(name='backup', url='https://example.com/old.git')
''
>>> remote = git.remotes.get(remote_name='backup')
>>> remote.remote_name
'backup'
>>> remote.set_url(url='https://example.com/new.git')
''
```

## Branch Operations

Beyond creating and deleting, branches support rename and upstream tracking:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='old-name')
''
>>> branch = git.branches.get(branch_name='old-name')
>>> branch.rename('new-name')  # doctest: +ELLIPSIS
''
```

Copy a branch:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.branches.create(branch='source-branch')
''
>>> branch = git.branches.get(branch_name='source-branch')
>>> branch.copy('copied-branch')  # doctest: +ELLIPSIS
''
```

## Stash Workflow

Save work in progress and restore it later:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # Push returns message (or "No local changes to save")
>>> git.stashes.push(message='WIP: feature work')  # doctest: +ELLIPSIS
'...'
```

List and inspect stashes:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> stashes = git.stashes.ls()
>>> isinstance(stashes, list)
True
```

## Worktree Management

Create additional working directories for parallel development:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> worktrees = git.worktrees.ls()
>>> len(worktrees) >= 1  # Main worktree always exists
True
```

## Notes

Attach metadata to commits:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> git.notes.add(message='Reviewed by Alice')
''
```

## Filtering with ls() Parameters

Manager `ls()` methods accept parameters to narrow results:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> # All local branches
>>> local = git.branches.ls()
>>> isinstance(local, list)
True
>>> # Branches merged into HEAD
>>> merged = git.branches.ls(merged='HEAD')
>>> isinstance(merged, list)
True
```

## Error Handling

When `get()` finds no match, it raises `ObjectDoesNotExist`:

```python
>>> from libvcs.cmd.git import Git
>>> from libvcs._internal.query_list import ObjectDoesNotExist
>>> git = Git(path=example_git_repo.path)
>>> try:
...     git.branches.get(branch_name='nonexistent-branch-xyz')
... except ObjectDoesNotExist:
...     print('Branch not found')
Branch not found
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
