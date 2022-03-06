# API Reference

## Create from VCS url

Helper methods are available in `libvcs.shortcuts` which can return a repo object from a single
entry-point.

```{eval-rst}
.. automodule:: libvcs.shortcuts
   :members:
```

See examples below of git, mercurial, and subversion.

## Instantiating a repo by hand

### Git

```{eval-rst}
.. automodule:: libvcs.git
   :members:
   :show-inheritance:
   :inherited-members:
```

### Mercurial

aka `hg(1)`

```{eval-rst}
.. automodule:: libvcs.hg
   :members:
   :show-inheritance:
   :inherited-members:
```

### Subversion

aka `svn(1)`

```{eval-rst}
.. automodule:: libvcs.svn
   :members:
   :show-inheritance:
   :inherited-members:
```

### Under the hood

Adding your own VCS / Extending libvcs can be done through subclassing `BaseRepo`.

```{eval-rst}
.. automodule:: libvcs.base
   :members:
   :show-inheritance:
```

### Utility stuff

```{eval-rst}
.. automodule:: libvcs.util
   :members:
```
