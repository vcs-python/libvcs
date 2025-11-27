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

#### CLI Flag → Python Parameter Mapping: `ls()` Enhancements

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-a, --all` | `_all: bool` | List all branches (local + remote) |
| `-r, --remotes` | `remotes: bool` | List remote branches only |
| `--merged <commit>` | `merged: str \| None` | Filter merged branches |
| `--no-merged <commit>` | `no_merged: str \| None` | Filter unmerged branches |
| `-v, --verbose` | `verbose: bool` | Show tracking info |
| `--contains <commit>` | `contains: str \| None` | Branches containing commit |
| `--sort=<key>` | `sort: str \| None` | Sort key |

### GitBranchCmd (Per-entity)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, branch_name, cmd)` | Implemented | Constructor with `branch_name` |
| `__repr__()` | Implemented | String representation |
| `run(command, local_flags, quiet, cached)` | Implemented | Run git branch command |
| `checkout()` | Implemented | Checkout this branch |
| `create()` | Implemented | Create this branch |
| `delete(force)` | Implemented | `-d` / `-D` |
| `rename(new_name, force)` | Implemented | `-m` / `-M` |
| `copy(new_name, force)` | Implemented | `-c` / `-C` |
| `set_upstream(upstream)` | Implemented | `--set-upstream-to` |
| `unset_upstream()` | Implemented | `--unset-upstream` |
| `track(remote_branch)` | Implemented | `-t` / `--track` |

#### CLI Flag → Python Parameter Mapping: GitBranchCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `delete()` | `git branch -d/-D` | `force=True` → `-D`, else `-d` |
| `rename(new_name)` | `git branch -m/-M` | `force=True` → `-M`, else `-m` |
| `copy(new_name)` | `git branch -c/-C` | `force=True` → `-C`, else `-c` |
| `set_upstream(upstream)` | `git branch --set-upstream-to=` | `upstream` → `--set-upstream-to={upstream}` |
| `unset_upstream()` | `git branch --unset-upstream` | None |
| `track(remote_branch)` | `git branch -t` | `remote_branch` → `-t {remote_branch}` |

### GitBranchManager Enhancements

| Feature | Status | Description |
|---------|--------|-------------|
| `--all` support | Implemented | List all branches (local + remote) |
| `--remotes` support | Implemented | List remote branches only |
| `--merged` filter | Implemented | Filter merged branches |
| `--no-merged` filter | Implemented | Filter unmerged branches |
| `--verbose` support | Implemented | Show tracking info |

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
| `set_branches(*branches, add)` | Implemented | `set-branches` |
| `set_head(branch, auto, delete)` | Implemented | `set-head` |
| `update(prune)` | Implemented | `update` |

#### CLI Flag → Python Parameter Mapping: Existing Methods

| Method | Parameters → Flags |
|--------|-------------------|
| `rename()` | `progress=True` → `--progress`, `progress=False` → `--no-progress` |
| `show()` | `verbose=True` → `--verbose`, `no_query_remotes=True` → `-n` |
| `prune()` | `dry_run=True` → `--dry-run` |
| `get_url()` | `push=True` → `--push`, `_all=True` → `--all` |
| `set_url()` | `push=True` → `--push`, `add=True` → `--add`, `delete=True` → `--delete` |

#### CLI Flag → Python Parameter Mapping: Additional Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `set_branches(*branches)` | `git remote set-branches` | `add=True` → `--add`, `branches` → positional |
| `set_head(branch)` | `git remote set-head` | `auto=True` → `-a`, `delete=True` → `-d`, `branch` → positional |
| `update()` | `git remote update` | `prune=True` → `-p` |

---

## 3. GitStashManager / GitStashEntryCmd

**Pattern Status**: Implemented

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
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git stash command |
| `ls()` | Implemented | Returns `QueryList[GitStashEntryCmd]` |
| `get(**kwargs)` | Implemented | Get single stash by filter |
| `filter(**kwargs)` | Implemented | Filter stashes |
| `push(message, path, patch, staged, keep_index, include_untracked)` | Implemented | Push to stash |
| `clear()` | Implemented | Clear all stashes |

#### CLI Flag → Python Parameter Mapping: `push()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-p, --patch` | `patch: bool` | Interactive patch selection |
| `-S, --staged` | `staged: bool` | Stash only staged changes |
| `-k, --keep-index` | `keep_index: bool` | Keep index intact |
| `-u, --include-untracked` | `include_untracked: bool` | Include untracked files |
| `-a, --all` | `_all: bool` | Include ignored files |
| `-q, --quiet` | `quiet: bool` | Suppress output |
| `-m, --message <msg>` | `message: str \| None` | Stash message |
| `-- <pathspec>` | `path: list[str] \| None` | Limit to paths |

### Planned GitStashEntryCmd (Per-entity)

Properties: `index: int`, `branch: str`, `message: str`

Parse from: `stash@{0}: On master: my message`

**Parsing pattern**:
```python
stash_pattern = r"stash@\{(?P<index>\d+)\}: On (?P<branch>[^:]+): (?P<message>.+)"
```

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, index, branch, message, cmd)` | Implemented | Constructor |
| `show(stat, patch)` | Implemented | Show stash diff |
| `apply(index)` | Implemented | Apply without removing |
| `pop(index)` | Implemented | Apply and remove |
| `drop()` | Implemented | Delete this stash |
| `branch(branch_name)` | Implemented | Create branch from stash |

#### CLI Flag → Python Parameter Mapping: GitStashEntryCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `show()` | `git stash show` | `stat=True` → `--stat`, `patch=True` → `-p`, `include_untracked=True` → `-u` |
| `apply()` | `git stash apply` | `index=True` → `--index`, `quiet=True` → `-q` |
| `pop()` | `git stash pop` | `index=True` → `--index`, `quiet=True` → `-q` |
| `drop()` | `git stash drop` | `quiet=True` → `-q` |
| `branch(name)` | `git stash branch` | `name` → positional |

---

## 4. GitSubmoduleCmd (Current) → GitSubmoduleManager / GitSubmoduleCmd (Planned)

**Pattern Status**: Implemented

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
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git submodule command |
| `ls()` | Implemented | Returns `QueryList[GitSubmoduleCmd]` |
| `get(**kwargs)` | Implemented | Get single submodule by filter |
| `filter(**kwargs)` | Implemented | Filter submodules |
| `add(url, path, branch, name, force)` | Implemented | Add submodule |
| `foreach(command, recursive)` | Implemented | Execute in each submodule |
| `sync(recursive)` | Implemented | Sync submodule URLs |
| `summary(commit, files, cached)` | Implemented | Summarize changes |

#### CLI Flag → Python Parameter Mapping: GitSubmoduleManager Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `add()` | `git submodule add` | `branch` → `-b`, `force=True` → `-f`, `name` → `--name`, `depth` → `--depth` |
| `foreach()` | `git submodule foreach` | `recursive=True` → `--recursive` |
| `sync()` | `git submodule sync` | `recursive=True` → `--recursive` |
| `summary()` | `git submodule summary` | `cached=True` → `--cached`, `files=True` → `--files`, `summary_limit` → `-n` |

### Planned GitSubmoduleCmd (Per-entity)

Properties: `name`, `path`, `url`, `branch`, `sha`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, name, submodule_path, url, branch, cmd)` | Implemented | Constructor |
| `init()` | Implemented | Initialize this submodule |
| `update(init, force, checkout, rebase, merge, recursive)` | Implemented | Update this submodule |
| `deinit(force)` | Implemented | Unregister submodule |
| `set_branch(branch)` | Implemented | Set branch |
| `set_url(url)` | Implemented | Set URL |
| `status()` | Implemented | Show status |
| `absorbgitdirs()` | Implemented | Absorb gitdir |

#### CLI Flag → Python Parameter Mapping: GitSubmoduleCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `init()` | `git submodule init` | None |
| `update()` | `git submodule update` | `init=True` → `--init`, `force=True` → `-f`, `recursive=True` → `--recursive`, `checkout/rebase/merge` → mode flags |
| `deinit()` | `git submodule deinit` | `force=True` → `-f`, `_all=True` → `--all` |
| `set_branch(branch)` | `git submodule set-branch` | `branch` → `-b`, `default=True` → `-d` |
| `set_url(url)` | `git submodule set-url` | `url` → positional |
| `status()` | `git submodule status` | `recursive=True` → `--recursive` |
| `absorbgitdirs()` | `git submodule absorbgitdirs` | None |

---

## 5. GitTagManager / GitTagCmd (New)

**Pattern Status**: Implemented

### Planned GitTagManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git tag command |
| `ls(pattern, sort, contains, no_contains, merged, no_merged)` | Implemented | Returns `QueryList[GitTagCmd]` |
| `get(**kwargs)` | Implemented | Get single tag by filter |
| `filter(**kwargs)` | Implemented | Filter tags |
| `create(name, ref, message, annotate, sign, force)` | Implemented | Create tag |

#### CLI Flag → Python Parameter Mapping: `create()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-a, --annotate` | `annotate: bool` | Create annotated tag |
| `-s, --sign` | `sign: bool` | Create GPG-signed tag |
| `-u <key-id>` | `local_user: str \| None` | Use specific GPG key |
| `-f, --force` | `force: bool` | Replace existing tag |
| `-m <msg>` | `message: str \| None` | Tag message |
| `-F <file>` | `file: str \| None` | Read message from file |

#### CLI Flag → Python Parameter Mapping: `ls()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-l <pattern>` | `pattern: str \| None` | List tags matching pattern |
| `--sort=<key>` | `sort: str \| None` | Sort by key |
| `--contains <commit>` | `contains: str \| None` | Tags containing commit |
| `--no-contains <commit>` | `no_contains: str \| None` | Tags not containing commit |
| `--merged <commit>` | `merged: str \| None` | Tags merged into commit |
| `--no-merged <commit>` | `no_merged: str \| None` | Tags not merged |
| `-n<num>` | `lines: int \| None` | Print annotation lines |

### Planned GitTagCmd (Per-entity)

Properties: `tag_name`, `ref`, `message` (for annotated)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, tag_name, ref, message, cmd)` | Implemented | Constructor |
| `show()` | Implemented | Show tag details |
| `delete()` | Implemented | Delete tag (`-d`) |
| `verify()` | Implemented | Verify signed tag (`-v`) |

#### CLI Flag → Python Parameter Mapping: GitTagCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `delete()` | `git tag -d` | None |
| `verify()` | `git tag -v` | None |
| `show()` | `git show` | (uses git show, not git tag) |

---

## 6. GitWorktreeManager / GitWorktreeCmd (New)

**Pattern Status**: Implemented

### Planned GitWorktreeManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git worktree command |
| `ls()` | Implemented | Returns `QueryList[GitWorktreeCmd]` |
| `get(**kwargs)` | Implemented | Get single worktree by filter |
| `filter(**kwargs)` | Implemented | Filter worktrees |
| `add(path, branch, detach, checkout, lock, force)` | Implemented | Add worktree |
| `prune(dry_run, verbose, expire)` | Implemented | Prune worktrees |

#### CLI Flag → Python Parameter Mapping: `add()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-f, --force` | `force: bool` | Force creation |
| `--detach` | `detach: bool` | Detach HEAD |
| `--checkout` | `checkout: bool` | Checkout after add |
| `--lock` | `lock: bool` | Lock worktree |
| `--reason <string>` | `reason: str \| None` | Lock reason |
| `-b <branch>` | `new_branch: str \| None` | Create new branch |
| `-B <branch>` | `new_branch_force: str \| None` | Force create branch |
| `--orphan` | `orphan: bool` | Create orphan branch |
| `--track` | `track: bool` | Track remote |

#### CLI Flag → Python Parameter Mapping: `prune()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-n, --dry-run` | `dry_run: bool` | Dry run |
| `-v, --verbose` | `verbose: bool` | Verbose output |
| `--expire <time>` | `expire: str \| None` | Expire time |

#### CLI Flag → Python Parameter Mapping: `ls()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-v` | `verbose: bool` | Verbose output |
| `--porcelain` | `porcelain: bool` | Machine-readable |

### Planned GitWorktreeCmd (Per-entity)

Properties: `worktree_path`, `branch`, `head`, `locked`, `prunable`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, worktree_path, branch, head, locked, prunable, cmd)` | Implemented | Constructor |
| `remove(force)` | Implemented | Remove worktree |
| `lock(reason)` | Implemented | Lock worktree |
| `unlock()` | Implemented | Unlock worktree |
| `move(new_path)` | Implemented | Move worktree |
| `repair()` | Implemented | Repair worktree |

#### CLI Flag → Python Parameter Mapping: GitWorktreeCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `remove()` | `git worktree remove` | `force=True` → `-f` |
| `lock()` | `git worktree lock` | `reason` → `--reason` |
| `unlock()` | `git worktree unlock` | None |
| `move(new_path)` | `git worktree move` | `force=True` → `-f` |
| `repair()` | `git worktree repair` | None |

---

## 7. GitNotesManager / GitNoteCmd (New)

**Pattern Status**: Implemented

### Planned GitNotesManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git notes command |
| `ls(ref)` | Implemented | Returns `QueryList[GitNoteCmd]` |
| `get(**kwargs)` | Implemented | Get single note by filter |
| `filter(**kwargs)` | Implemented | Filter notes |
| `add(object, message, file, force, allow_empty)` | Implemented | Add note |
| `prune(dry_run, verbose)` | Implemented | Prune notes |
| `merge(notes_ref, strategy, commit, abort, quiet)` | Implemented | Merge notes |
| `get_ref()` | Implemented | Get notes ref |

#### CLI Flag → Python Parameter Mapping: `add()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-f, --force` | `force: bool` | Overwrite existing note |
| `--allow-empty` | `allow_empty: bool` | Allow empty note |
| `-m <msg>` | `message: str \| None` | Note message |
| `-F <file>` | `file: str \| None` | Read message from file |
| `-c <object>` | `reuse_message: str \| None` | Reuse message from note |
| `-C <object>` | `reedit_message: str \| None` | Re-edit message |

#### CLI Flag → Python Parameter Mapping: `prune()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-n, --dry-run` | `dry_run: bool` | Dry run |
| `-v, --verbose` | `verbose: bool` | Verbose output |

#### CLI Flag → Python Parameter Mapping: `merge()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `-s <strategy>` | `strategy: str \| None` | Merge strategy |
| `--commit` | `commit: bool` | Finalize merge |
| `--abort` | `abort: bool` | Abort merge |
| `-q, --quiet` | `quiet: bool` | Quiet mode |
| `-v, --verbose` | `verbose: bool` | Verbose mode |

### Planned GitNoteCmd (Per-entity)

Properties: `object`, `note_ref`

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, object, note_ref, cmd)` | Implemented | Constructor |
| `show()` | Implemented | Show note |
| `edit()` | Implemented | Edit note (non-interactive) |
| `append(message)` | Implemented | Append to note |
| `copy(from_object)` | Implemented | Copy note |
| `remove()` | Implemented | Remove note |

#### CLI Flag → Python Parameter Mapping: GitNoteCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `show()` | `git notes show` | None |
| `edit()` | `git notes edit` | `allow_empty=True` → `--allow-empty` |
| `append(message)` | `git notes append` | `-m` → message, `-F` → file |
| `copy(from_object)` | `git notes copy` | `force=True` → `-f` |
| `remove()` | `git notes remove` | `ignore_missing=True` → `--ignore-missing` |

---

## 8. GitReflogManager / GitReflogCmd (New)

**Pattern Status**: Implemented

### Planned GitReflogManager (Collection-level)

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, cmd)` | Implemented | Constructor |
| `run(command, local_flags)` | Implemented | Run git reflog command |
| `ls(ref)` | Implemented | Returns `QueryList[GitReflogCmd]` |
| `get(**kwargs)` | Implemented | Get single entry by filter |
| `filter(**kwargs)` | Implemented | Filter entries |
| `expire(ref, _all, dry_run, rewrite, updateref, stale_fix, verbose)` | Implemented | Expire entries |
| `exists(ref)` | Implemented | Check if reflog exists |

#### CLI Flag → Python Parameter Mapping: `ls()` / `show()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `<ref>` | `ref: str` | Reference (default: HEAD) |
| `-n <number>` | `number: int \| None` | Limit entries |
| `--date=<format>` | `date: str \| None` | Date format |

#### CLI Flag → Python Parameter Mapping: `expire()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `--all` | `_all: bool` | Process all refs |
| `-n, --dry-run` | `dry_run: bool` | Dry run |
| `--rewrite` | `rewrite: bool` | Rewrite entries |
| `--updateref` | `updateref: bool` | Update ref |
| `--stale-fix` | `stale_fix: bool` | Fix stale entries |
| `-v, --verbose` | `verbose: bool` | Verbose output |
| `--expire=<time>` | `expire: str \| None` | Expire unreachable older than |
| `--expire-unreachable=<time>` | `expire_unreachable: str \| None` | Expire unreachable |

#### CLI Flag → Python Parameter Mapping: `delete()`

| Git CLI Flag | Python Parameter | Description |
|--------------|------------------|-------------|
| `--rewrite` | `rewrite: bool` | Rewrite entries |
| `--updateref` | `updateref: bool` | Update ref |
| `-n, --dry-run` | `dry_run: bool` | Dry run |

### Planned GitReflogCmd (Per-entity)

Properties: `ref`, `index`, `action`, `message`, `sha`

Parse from: `abc1234 HEAD@{0}: commit: message`

**Parsing pattern**:
```python
reflog_pattern = r"(?P<sha>[a-f0-9]+) (?P<ref>[^@]+)@\{(?P<index>\d+)\}: (?P<action>[^:]+): (?P<message>.+)"
```

| Method | Status | Description |
|--------|--------|-------------|
| `__init__(path, ref, index, action, message, sha, cmd)` | Implemented | Constructor |
| `show()` | Implemented | Show entry details |
| `delete()` | Implemented | Delete entry |

#### CLI Flag → Python Parameter Mapping: GitReflogCmd Methods

| Method | Git CLI | Parameters → Flags |
|--------|---------|-------------------|
| `show()` | `git reflog show` | (show this entry) |
| `delete()` | `git reflog delete` | `rewrite=True` → `--rewrite`, `updateref=True` → `--updateref` |

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
