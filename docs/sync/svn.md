# `libvcs.sync.svn`

Check out and update [Subversion](https://subversion.apache.org/) working
copies through {class}`~libvcs.sync.svn.SvnSync`:
{meth}`~libvcs.sync.svn.SvnSync.obtain` creates the checkout,
{meth}`~libvcs.sync.svn.SvnSync.update_repo` refreshes it, and
{meth}`~libvcs.sync.svn.SvnSync.get_revision` reads the current revision for
[`svn(1)`](https://svnbook.red-bean.com/en/1.7/svn.ref.svn.html).

{class}`~libvcs.sync.svn.SvnOptions` groups authentication, certificate,
external, and ambient-depth settings. Passwords do not appear in its
representation.

```python
>>> from libvcs.sync.svn import SvnOptions, SvnSync
>>> options = SvnOptions(username="reader", password="secret", depth="files")
>>> repo = SvnSync(
...     url="https://example.com/project",
...     path=tmp_path / "project",
...     options=options,
... )
>>> repo.options.depth
'files'
>>> "secret" in repr(repo.options)
False
```

```{eval-rst}
.. automodule:: libvcs.sync.svn
   :members:
   :show-inheritance:
   :undoc-members:
```
