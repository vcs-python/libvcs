(api)=

# API Reference

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
.. automodule:: libvcs.constants
   :members:
```

## Utility stuff

```{eval-rst}
.. automodule:: libvcs.util
   :members:
```
