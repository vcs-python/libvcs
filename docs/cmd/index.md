(cmd)=

# Commands - `libvcs.cmd`

Compare to: [`fabtools.git`](https://fabtools.readthedocs.io/en/0.19.0/api/git.html#git-module),
[`salt.modules.git`](https://docs.saltproject.io/en/latest/ref/modules/all/salt.modules.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

## Overview

The `libvcs.cmd` module provides Python wrappers for VCS command-line tools:

- {mod}`libvcs.cmd.git` - Git commands with Managers for intuitive entity traversal and Commands for targeted execution
- {mod}`libvcs.cmd.hg` - Mercurial commands
- {mod}`libvcs.cmd.svn` - Subversion commands

### When to use `cmd` vs `sync`

| Module | Use Case |
|--------|----------|
| `libvcs.cmd` | Fine-grained control over individual VCS commands |
| `libvcs.sync` | High-level repository cloning and updating |

## Modules

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Git
:link: git/index
:link-type: doc
Full git CLI wrapper with sub-command managers (branch, remote, stash, ...).
:::

:::{grid-item-card} Mercurial
:link: hg
:link-type: doc
Mercurial CLI wrapper.
:::

:::{grid-item-card} Subversion
:link: svn
:link-type: doc
Subversion CLI wrapper.
:::

::::

```{toctree}
:hidden:

git/index
hg
svn
```
