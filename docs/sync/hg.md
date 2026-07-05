# `libvcs.sync.hg`

Clone and update [Mercurial](https://www.mercurial-scm.org/) repositories
through {class}`~libvcs.sync.hg.HgSync`: {meth}`~libvcs.sync.hg.HgSync.obtain`
creates the checkout, {meth}`~libvcs.sync.hg.HgSync.update_repo` refreshes it,
and {meth}`~libvcs.sync.hg.HgSync.get_revision` reads the current revision for
[`hg(1)`](https://www.mercurial-scm.org/doc/hg.1.html).

```{eval-rst}
.. automodule:: libvcs.sync.hg
   :members:
   :show-inheritance:
   :undoc-members:
```
