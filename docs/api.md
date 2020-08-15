# API Reference

## Create from VCS url

Helper methods are available in ``libvcs.shortcuts`` which
can return a repo object from a single entry-point.

```eval_rst
.. automodule:: libvcs.shortcuts
   :members:
```

See examples below of git, mercurial, and subversion.

## Instantiating a repo by hand

### Git

```eval_rst
.. automodule:: libvcs.git
   :members:
   :show-inheritance:
   :inherited-members:
```

### Mercurial

aka ``hg(1)``

```eval_rst
.. automodule:: libvcs.hg
   :members:
   :show-inheritance:
   :inherited-members:
```

### Subversion

aka ``svn(1)``

```eval_rst
.. automodule:: libvcs.svn
   :members:
   :show-inheritance:
   :inherited-members:
```

### Under the hood

Adding your own VCS / Extending libvcs can be done through subclassing ``BaseRepo``.

```eval_rst
.. automodule:: libvcs.base
   :members:
   :show-inheritance:
```

### Utility stuff

```eval_rst
.. automodule:: libvcs.util
   :members:
```
