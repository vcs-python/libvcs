(states)=

# `libvcs.states`

Compare to:
[`fabtools.require.git`](https://fabtools.readthedocs.io/en/0.19.0/api/require/git.html),
[`salt.states.git`](https://docs.saltproject.io/en/latest/ref/states/all/salt.states.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

```{toctree}
:caption: API

git
hg
svn
base
```

## Create from VCS url

Helper methods are available in `libvcs.shortcuts` which can return a repo object from a single
entry-point.

```{eval-rst}
.. automodule:: libvcs.shortcuts
   :members:
```

See examples below of git, mercurial, and subversion.

## Constants

```{eval-rst}
.. automodule:: libvcs.states.constants
   :members:
```

## Utility stuff

```{eval-rst}
.. automodule:: libvcs.cmd.core
   :members:
```
