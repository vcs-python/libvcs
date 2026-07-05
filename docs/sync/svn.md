# `libvcs.sync.svn`

Check out and update [Subversion](https://subversion.apache.org/) working
copies through {class}`~libvcs.sync.svn.SvnSync`:
{meth}`~libvcs.sync.svn.SvnSync.obtain` creates the checkout,
{meth}`~libvcs.sync.svn.SvnSync.update_repo` refreshes it, and
{meth}`~libvcs.sync.svn.SvnSync.get_revision` reads the current revision for
[`svn(1)`](https://svnbook.red-bean.com/en/1.7/svn.ref.svn.html).

```{eval-rst}
.. automodule:: libvcs.sync.svn
   :members:
   :show-inheritance:
   :undoc-members:
```
