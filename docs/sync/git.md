# `libvcs.sync.git`

Clone and update git repositories through
{class}`~libvcs.sync.git.GitSync`: {meth}`~libvcs.sync.git.GitSync.obtain`
creates the checkout, {meth}`~libvcs.sync.git.GitSync.update_repo` refreshes
it, and {meth}`~libvcs.sync.git.GitSync.get_revision` reads the current
revision for
[`git(1)`](https://git-scm.com/docs/git).

Compare to:
[`fabtools.require.git`](https://fabtools.readthedocs.io/en/0.19.0/api/require/git.html),
[`salt.states.git`](https://docs.saltproject.io/en/latest/ref/states/all/salt.states.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

## Partial clones

Pass any {ref}`validated Git filter <git-partial-clone-filters>` as
`git_filter` when constructing {class}`~libvcs.sync.git.GitSync`. The filter
applies to the initial clone and to submodules created during that obtain. An
existing checkout keeps its configured partial-clone filter during updates.

```python
>>> from libvcs.cmd.git_filter import BlobNone
>>> from libvcs.sync.git import GitSync
>>> repo = GitSync(
...     url="https://example.com/project.git",
...     path=tmp_path / "project",
...     git_filter=BlobNone(),
... )
>>> repo.git_filter
('blob:none',)
```

{class}`~libvcs.cmd.git_filter.Auto` cannot be used with `GitSync`: obtain
forwards the configured filter to `git submodule update`, and that command has
no `auto` mode. Use {meth}`~libvcs.cmd.git.Git.clone` or
{meth}`~libvcs.cmd.git.Git.fetch` directly when server-selected filtering is
required.

```{eval-rst}
.. automodule:: libvcs.sync.git
   :members:
   :show-inheritance:
   :undoc-members:
```
