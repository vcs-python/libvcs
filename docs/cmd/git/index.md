# `libvcs.cmd.git`

For `git(1)`.

_Compare to: [`fabtools.git`](https://fabtools.readthedocs.io/en/0.19.0/api/git.html#git-module),
[`salt.modules.git`](https://docs.saltproject.io/en/latest/ref/modules/all/salt.modules.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)_

## Managers and Commands

libvcs provides **Managers** and **Commands** for git subcommands:

- **Managers** (`git.branches`, `git.tags`, etc.) let you traverse repository
  entities intuitively with ORM-like filtering via QueryList
- **Commands** are contextual ways to run git commands against a specific target entity

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

### Quick Example

List branches, rename one through its Cmd object, and manage tags:

```python
>>> from libvcs.cmd.git import Git
>>> git = Git(path=example_git_repo.path)
>>> branches = git.branches.ls()
>>> len(branches) >= 1
True
>>> git.branches.create(branch='old-name')
''
>>> branch = git.branches.get(branch_name='old-name')
>>> branch.rename('new-name')
''
>>> git.tags.create(name='v1.0.0', message='Release 1.0')
''
>>> tag = git.tags.get(tag_name='v1.0.0')
>>> tag.delete()  # doctest: +ELLIPSIS
"Deleted tag 'v1.0.0' ..."
```

```{toctree}
:caption: Subcommands
:maxdepth: 1

submodule
remote
stash
branch
tag
worktree
notes
reflog
```

```{eval-rst}
.. automodule:: libvcs.cmd.git
   :members:
   :show-inheritance:
   :undoc-members:
   :exclude-members: GitSubmoduleCmd,
     GitSubmoduleManager,
     GitSubmodule,
     GitSubmoduleEntryCmd,
     GitRemoteCmd,
     GitRemoteManager,
     GitStashCmd,
     GitStashManager,
     GitStashEntryCmd,
     GitBranchCmd,
     GitBranchManager,
     GitTagCmd,
     GitTagManager,
     GitWorktreeCmd,
     GitWorktreeManager,
     GitNoteCmd,
     GitNotesManager,
     GitReflogEntry,
     GitReflogEntryCmd,
     GitReflogManager
```
