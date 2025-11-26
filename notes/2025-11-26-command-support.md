# Git Command Support Audit - 2025-11-26

This document provides a comprehensive audit of git command support in libvcs, documenting existing implementations and planned additions following the Manager/Cmd pattern.

## Pattern Overview

```
Manager (collection-level)              Cmd (per-entity)
├── ls() -> QueryList[Cmd]              ├── run()
├── get(**kwargs) -> Cmd | None         ├── show()
├── filter(**kwargs) -> list[Cmd]       ├── remove()/delete()
├── add() / create()                    ├── rename()
└── run()                               └── entity-specific operations
```

---

## 1. GitBranchManager / GitBranchCmd

**Pattern Status**: Implemented

### GitBranchManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, quiet, cached)` | Implemented | Run git branch command |
| `checkout(branch)` | Implemented | Checkout a branch |
| `create(branch)` | Implemented | Create new branch via `checkout -b` |
| `_ls()` | Implemented | Internal raw listing |
| `ls()` | Implemented | Returns `QueryList[GitBranchCmd]` |
| `get(**kwargs)` | Implemented | Get single branch by filter |
| `filter(**kwargs)` | Implemented | Filter branches |

### GitBranchCmd (Per-entity)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, branch_name, cmd)` | Implemented | Constructor with `branch_name` |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, quiet, cached)` | Implemented | Run git branch command |
| `checkout()` | Implemented | Checkout this branch |
| `create()` | Implemented | Create this branch |
| `delete(force)` | **Missing** | `-d` / `-D` |
| `rename(new_name, force)` | **Missing** | `-m` / `-M` |
| `copy(new_name, force)` | **Missing** | `-c` / `-C` |
| `set_upstream(upstream)` | **Missing** | `--set-upstream-to` |
| `unset_upstream()` | **Missing** | `--unset-upstream` |
| `track(remote_branch)` | **Missing** | `-t` / `--track` |

### GitBranchManager Enhancements Needed

| Feature | Status | Description |
|---------|--------|-------------|
| `--all` support | **Missing** | List all branches (local + remote) |
| `--remotes` support | **Missing** | List remote branches only |
| `--merged` filter | **Missing** | Filter merged branches |
| `--no-merged` filter | **Missing** | Filter unmerged branches |
| `--verbose` support | **Missing** | Show tracking info |

---

## 2. GitRemoteManager / GitRemoteCmd

**Pattern Status**: Implemented

### GitRemoteManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags)` | Implemented | Run git remote command |
| `add(name, url, fetch, track, master, mirror)` | Implemented | Add new remote |
| `show(name, verbose, no_query_remotes)` | Implemented | Show remotes |
| `_ls()` | Implemented | Internal raw listing |
| `ls()` | Implemented | Returns `QueryList[GitRemoteCmd]` |
| `get(**kwargs)` | Implemented | Get single remote by filter |
| `filter(**kwargs)` | Implemented | Filter remotes |

### GitRemoteCmd (Per-entity)

Properties: `remote_name`, `fetch_url`, `push_url`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, remote_name, fetch_url, push_url, cmd)` | Implemented | Constructor |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, verbose)` | Implemented | Run git remote command |
| `rename(old, new, progress)` | Implemented | Rename remote |
| `remove()` | Implemented | Delete remote |
| `show(verbose, no_query_remotes)` | Implemented | Show remote details |
| `prune(dry_run)` | Implemented | Prune stale branches |
| `get_url(push, _all)` | Implemented | Get remote URL |
| `set_url(url, old_url, push, add, delete)` | Implemented | Set remote URL |
| `set_branches(*branches, add)` | **Missing** | `set-branches` |
| `set_head(branch, auto, delete)` | **Missing** | `set-head` |
| `update(prune)` | **Missing** | `update` |

---

## 3. GitStashCmd (Current) → GitStashManager / GitStashEntryCmd (Planned)

**Pattern Status**: Not implemented - needs refactoring

### Current GitStashCmd

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, quiet, cached)` | Implemented | Run git stash command |
| `ls()` | Implemented | List stashes (returns string) |
| `push(path, patch, staged)` | Implemented | Push to stash |
| `pop(stash, index, quiet)` | Implemented | Pop from stash |
| `save(message, staged, keep_index, patch, include_untracked, _all, quiet)` | Implemented | Save to stash |

### Planned GitStashManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git stash command |
| `ls()` | **Planned** | Returns `QueryList[GitStashEntryCmd]` |
| `get(**kwargs)` | **Planned** | Get single stash by filter |
| `filter(**kwargs)` | **Planned** | Filter stashes |
| `push(message, path, patch, staged, keep_index, include_untracked)` | **Planned** | Push to stash |
| `clear()` | **Planned** | Clear all stashes |

### Planned GitStashEntryCmd (Per-entity)

Properties: `index: int`, `branch: str`, `message: str`

Parse from: `stash@{0}: On master: my message`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, index, branch, message, cmd)` | **Planned** | Constructor |
| `show(stat, patch)` | **Planned** | Show stash diff |
| `apply(index)` | **Planned** | Apply without removing |
| `pop(index)` | **Planned** | Apply and remove |
| `drop()` | **Planned** | Delete this stash |
| `branch(branch_name)` | **Planned** | Create branch from stash |

---

## 4. GitSubmoduleCmd (Current) → GitSubmoduleManager / GitSubmoduleCmd (Planned)

**Pattern Status**: Not implemented - needs refactoring

### Current GitSubmoduleCmd

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, quiet, cached)` | Implemented | Run git submodule command |
| `init(path)` | Implemented | Initialize submodules |
| `update(path, init, force, checkout, rebase, merge, recursive, _filter)` | Implemented | Update submodules |

### Planned GitSubmoduleManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git submodule command |
| `ls()` | **Planned** | Returns `QueryList[GitSubmoduleCmd]` |
| `get(**kwargs)` | **Planned** | Get single submodule by filter |
| `filter(**kwargs)` | **Planned** | Filter submodules |
| `add(url, path, branch, name, force)` | **Planned** | Add submodule |
| `foreach(command, recursive)` | **Planned** | Execute in each submodule |
| `sync(recursive)` | **Planned** | Sync submodule URLs |
| `summary(commit, files, cached)` | **Planned** | Summarize changes |

### Planned GitSubmoduleCmd (Per-entity)

Properties: `name`, `path`, `url`, `branch`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, name, submodule_path, url, branch, cmd)` | **Planned** | Constructor |
| `init()` | **Planned** | Initialize this submodule |
| `update(init, force, checkout, rebase, merge, recursive)` | **Planned** | Update this submodule |
| `deinit(force)` | **Planned** | Unregister submodule |
| `set_branch(branch)` | **Planned** | Set branch |
| `set_url(url)` | **Planned** | Set URL |
| `status()` | **Planned** | Show status |
| `absorbgitdirs()` | **Planned** | Absorb gitdir |

---

## 5. GitTagManager / GitTagCmd (New)

**Pattern Status**: Not implemented

### Planned GitTagManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git tag command |
| `ls(pattern, sort, contains, no_contains, merged, no_merged)` | **Planned** | Returns `QueryList[GitTagCmd]` |
| `get(**kwargs)` | **Planned** | Get single tag by filter |
| `filter(**kwargs)` | **Planned** | Filter tags |
| `create(name, ref, message, annotate, sign, force)` | **Planned** | Create tag |

### Planned GitTagCmd (Per-entity)

Properties: `tag_name`, `ref`, `message` (for annotated)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, tag_name, ref, message, cmd)` | **Planned** | Constructor |
| `show()` | **Planned** | Show tag details |
| `delete()` | **Planned** | Delete tag (`-d`) |
| `verify()` | **Planned** | Verify signed tag (`-v`) |

---

## 6. GitWorktreeManager / GitWorktreeCmd (New)

**Pattern Status**: Not implemented

### Planned GitWorktreeManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git worktree command |
| `ls()` | **Planned** | Returns `QueryList[GitWorktreeCmd]` |
| `get(**kwargs)` | **Planned** | Get single worktree by filter |
| `filter(**kwargs)` | **Planned** | Filter worktrees |
| `add(path, branch, detach, checkout, lock, force)` | **Planned** | Add worktree |
| `prune(dry_run, verbose, expire)` | **Planned** | Prune worktrees |

### Planned GitWorktreeCmd (Per-entity)

Properties: `worktree_path`, `branch`, `head`, `locked`, `prunable`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, worktree_path, branch, head, locked, prunable, cmd)` | **Planned** | Constructor |
| `remove(force)` | **Planned** | Remove worktree |
| `lock(reason)` | **Planned** | Lock worktree |
| `unlock()` | **Planned** | Unlock worktree |
| `move(new_path)` | **Planned** | Move worktree |
| `repair()` | **Planned** | Repair worktree |

---

## 7. GitNotesManager / GitNoteCmd (New)

**Pattern Status**: Not implemented

### Planned GitNotesManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git notes command |
| `ls(ref)` | **Planned** | Returns `QueryList[GitNoteCmd]` |
| `get(**kwargs)` | **Planned** | Get single note by filter |
| `filter(**kwargs)` | **Planned** | Filter notes |
| `add(object, message, file, force, allow_empty)` | **Planned** | Add note |
| `prune(dry_run, verbose)` | **Planned** | Prune notes |
| `merge(notes_ref, strategy, commit, abort, quiet)` | **Planned** | Merge notes |
| `get_ref()` | **Planned** | Get notes ref |

### Planned GitNoteCmd (Per-entity)

Properties: `object`, `note_ref`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, object, note_ref, cmd)` | **Planned** | Constructor |
| `show()` | **Planned** | Show note |
| `edit()` | **Planned** | Edit note (non-interactive) |
| `append(message)` | **Planned** | Append to note |
| `copy(from_object)` | **Planned** | Copy note |
| `remove()` | **Planned** | Remove note |

---

## 8. GitReflogManager / GitReflogCmd (New)

**Pattern Status**: Not implemented

### Planned GitReflogManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | **Planned** | Constructor |
| `run(command, local_flags)` | **Planned** | Run git reflog command |
| `ls(ref)` | **Planned** | Returns `QueryList[GitReflogCmd]` |
| `get(**kwargs)` | **Planned** | Get single entry by filter |
| `filter(**kwargs)` | **Planned** | Filter entries |
| `expire(ref, _all, dry_run, rewrite, updateref, stale_fix, verbose)` | **Planned** | Expire entries |
| `exists(ref)` | **Planned** | Check if reflog exists |

### Planned GitReflogCmd (Per-entity)

Properties: `ref`, `index`, `action`, `message`, `sha`

Parse from: `abc1234 HEAD@{0}: commit: message`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, ref, index, action, message, sha, cmd)` | **Planned** | Constructor |
| `show()` | **Planned** | Show entry details |
| `delete()` | **Planned** | Delete entry |

---

## Git Class Exposure

### Current

```python
class Git:
    submodule: GitSubmoduleCmd
    remotes: GitRemoteManager      # ✓ Manager pattern
    stash: GitStashCmd
    branches: GitBranchManager     # ✓ Manager pattern
```

### Planned

```python
class Git:
    submodules: GitSubmoduleManager    # Renamed + Manager pattern
    remotes: GitRemoteManager          # ✓ Already done
    stash: GitStashManager             # Refactored to Manager pattern
    branches: GitBranchManager         # ✓ Already done
    tags: GitTagManager                # New
    worktrees: GitWorktreeManager      # New
    notes: GitNotesManager             # New
    reflog: GitReflogManager           # New
```

---

## Implementation Order

1. Complete GitBranchCmd (add missing methods)
2. Complete GitRemoteCmd (add missing methods)
3. Implement GitTagManager/GitTagCmd
4. Refactor GitStashCmd → GitStashManager/GitStashEntryCmd
5. Implement GitWorktreeManager/GitWorktreeCmd
6. Implement GitNotesManager/GitNoteCmd
7. Refactor GitSubmoduleCmd → GitSubmoduleManager/GitSubmoduleCmd
8. Implement GitReflogManager/GitReflogCmd
9. Update Git class to expose all managers

---

## Test Coverage

Currently **no direct unit tests** exist for:
- GitBranchManager / GitBranchCmd
- GitRemoteManager / GitRemoteCmd
- GitStashCmd
- GitSubmoduleCmd

Tests use pytest fixtures from `libvcs.pytest_plugin`:
- `create_git_remote_repo` - Creates temporary git repo
- `git_repo` - Pre-made GitSync instance
- `example_git_repo` - Example repo for doctests

All new tests will:
- Use real git commands (no mocks)
- Use pytest fixtures for setup/teardown
- Follow TDD approach
