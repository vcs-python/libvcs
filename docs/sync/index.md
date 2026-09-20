(projects)=

# Sync - `libvcs.sync`

Keep a local checkout in sync with its remote: {meth}`~libvcs.sync.git.GitSync.obtain`
and its Mercurial and Subversion counterparts clone the repository when it
doesn't exist yet and update it when it does, through
{class}`~libvcs.sync.git.GitSync`, {class}`~libvcs.sync.hg.HgSync`, and
{class}`~libvcs.sync.svn.SvnSync` — built on top of {mod}`libvcs.cmd`.

Compare to:
[`fabtools.require.git`](https://fabtools.readthedocs.io/en/0.19.0/api/require/git.html),
[`salt.states.git`](https://docs.saltproject.io/en/latest/ref/states/all/salt.states.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

## Read the checkout position

Use `get_position()` to inspect the checkout before choosing an update policy.
It returns an immutable {class}`~libvcs.sync.base.WorkingCopyPosition` from
local metadata. It does not fetch or contact a server.

```python
>>> position = example_git_repo.get_position()
>>> position.ref_kind
'branch'
>>> position.revision == example_git_repo.get_revision()
True
>>> position.follows
True
```

Git reports an attached branch or a detached commit. Mercurial reports its
active bookmark when present, otherwise its named branch. Subversion reports
the checkout URL and root base revision; `mixed` and `switched` identify
working copies whose children cannot be described by the root alone.

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
