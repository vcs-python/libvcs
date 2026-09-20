# `libvcs.sync.hg`

Clone and update [Mercurial](https://www.mercurial-scm.org/) repositories
through {class}`~libvcs.sync.hg.HgSync`: {meth}`~libvcs.sync.hg.HgSync.obtain`
creates the checkout, {meth}`~libvcs.sync.hg.HgSync.update_repo` refreshes it,
and {meth}`~libvcs.sync.hg.HgSync.get_revision` reads the current revision for
[`hg(1)`](https://www.mercurial-scm.org/doc/hg.1.html).

{class}`~libvcs.sync.hg.HgOptions` groups Mercurial transport and clone
settings. The default verifies TLS certificates.

```python
>>> from libvcs.sync.hg import HgOptions, HgSync
>>> repo = HgSync(
...     url="https://example.com/project",
...     path=tmp_path / "project",
...     options=HgOptions(stream=True),
... )
>>> repo.options.stream
True
```

```{eval-rst}
.. automodule:: libvcs.sync.hg
   :members:
   :show-inheritance:
   :undoc-members:
```
