(projects)=

# Sync - `libvcs.sync`

Compare to:
[`fabtools.require.git`](https://fabtools.readthedocs.io/en/0.19.0/api/require/git.html),
[`salt.states.git`](https://docs.saltproject.io/en/latest/ref/states/all/salt.states.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

## Async Variants

Async equivalents are available in `libvcs.sync._async`:

- {class}`~libvcs.sync._async.git.AsyncGitSync` - Async git repository management
- {class}`~libvcs.sync._async.hg.AsyncHgSync` - Async mercurial repository management
- {class}`~libvcs.sync._async.svn.AsyncSvnSync` - Async subversion repository management

See {doc}`/topics/asyncio` for usage patterns.

## Modules

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Git Sync
:link: git
:link-type: doc
Clone, fetch, and update Git repositories.
:::

:::{grid-item-card} Hg Sync
:link: hg
:link-type: doc
Clone and update Mercurial repositories.
:::

:::{grid-item-card} SVN Sync
:link: svn
:link-type: doc
Checkout and update Subversion working copies.
:::

:::{grid-item-card} Base
:link: base
:link-type: doc
Abstract base class for all sync backends.
:::

::::

## Constants

```{eval-rst}
.. automodule:: libvcs.sync.constants
   :members:
```

```{toctree}
:hidden:

git
hg
svn
base
```
