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

## Targets and recovery

`SyncTarget(rev=...)` accepts a numeric revision or `HEAD`. The configured
repository URL determines whether synchronization updates or switches the
working copy. Local `resolve_target()` cannot resolve remote `HEAD`; use a
numeric revision for keep/warn comparison without server contact.

Preservation seals a complete physical working copy, including `.svn`,
schedules, properties, unknown and ignored files, and working-tree symlinks.
Recovery creates a separate checkout offline, even after the original source
is deleted or replaced. See the shared {ref}`policy guide <sync-policies>`
and {ref}`token lifecycle <sync-recovery>` for result handling and release.

Preservation admits POSIX format-31 working-copy roots. It rejects externals,
nested working copies, busy or unsupported database schemas, and
administrative symlinks. Missing paths are removed again only after verified
safe native completion; upstream changes remain visible as conflicts.

```{eval-rst}
.. automodule:: libvcs.sync.svn
   :members:
   :show-inheritance:
   :undoc-members:
```
