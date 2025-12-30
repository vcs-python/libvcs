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

### Async Variants

Async equivalents are available in `libvcs.cmd._async`:

- {class}`~libvcs.cmd._async.git.AsyncGit` - Async git commands
- {class}`~libvcs.cmd._async.hg.AsyncHg` - Async mercurial commands
- {class}`~libvcs.cmd._async.svn.AsyncSvn` - Async subversion commands

See {doc}`/topics/asyncio` for usage patterns.

### When to use `cmd` vs `sync`

| Module | Use Case |
|--------|----------|
| `libvcs.cmd` | Fine-grained control over individual VCS commands |
| `libvcs.sync` | High-level repository cloning and updating |

```{toctree}
:caption: API

git/index
hg
svn
```
