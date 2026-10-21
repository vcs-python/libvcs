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

## Remotes and checkout policy

Name native fetch and push destinations separately:

```python
>>> from libvcs import HgRemote, HgSync, SyncPolicy, SyncTarget
>>> repo = HgSync(
...     url="https://example.com/project",
...     path=tmp_path / "project",
...     remotes={"upstream": HgRemote(
...         "upstream", "https://example.com/project", "ssh://example.com/publish"
...     )},
... )
>>> target = SyncTarget(branch="default", remote="upstream")
>>> policy = SyncPolicy(dirty="preserve")
```

Pass `target` and `policy` to `update_repo()`. The remote selects the pull
source; its push URL stays separate. The shared {ref}`recovery example <sync-recovery>`
executes an update and checks its result against a disposable repository.
A synthesized `default` alias retains
an existing push destination. An explicitly configured alias supplies both
destinations, with push defaulting to its fetch URL when omitted.

`remotes()` reads effective aliases, including native `%include` files.
`set_remotes(overwrite=True)` writes configured aliases atomically. The method
preserves comments and included files and owns a final `[paths]` block in
`.hg/hgrc`; keep that block last when editing the file manually. Without
`overwrite=True`, existing aliases remain unchanged.

Existing checkouts apply configured remotes after keep/warn and dirty-abort
preflight. New checkouts start at the configured target before drift policy
applies. A method-level target overrides the constructor's revision.
Preservation retains an owned shelf and supplemental native state. Recovery
creates a separate checkout from retained local history; the configured remote
is never contacted during recovery.

## Preservation limits

Named branches, bookmarks, tags, and changesets resolve locally. Native
unshelve conflicts retain both the conflict state and recovery token. Keep
the source history until releasing its tokens: deleting that history prevents
offline recovery. Preservation rejects subrepositories, nested repositories,
shared-store layouts, and unfinished native operations. See the shared
{ref}`token lifecycle <sync-recovery>` for discovery, separate recovery, and
explicit release.

```{eval-rst}
.. automodule:: libvcs.sync.hg
   :members:
   :show-inheritance:
   :undoc-members:
```
