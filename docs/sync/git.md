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

Pass any {ref}`validated Git filter <git-partial-clone-filters>` through
{class}`~libvcs.sync.git.GitOptions`. The filter applies to the initial clone
and to submodules created during that obtain. An existing checkout keeps its
configured partial-clone filter during updates.

```python
>>> from libvcs.cmd.git_filter import BlobNone
>>> from libvcs.sync.git import GitOptions, GitSync
>>> repo = GitSync(
...     url="https://example.com/project.git",
...     path=tmp_path / "project",
...     options=GitOptions(filter=BlobNone()),
... )
>>> repo.options.filter
('blob:none',)
```

{class}`~libvcs.cmd.git_filter.Auto` is available for the initial clone with
Git 2.54 or newer. After cloning, `GitSync` checks the index for submodule
gitlinks. With no gitlinks, the empty submodule update runs without a filter.
If gitlinks exist, obtain raises `ValueError` before initializing them and
leaves the parent clone at the destination. Existing checkout updates do not
change their configured filter.

```{eval-rst}
.. automodule:: libvcs.sync.git
   :members:
   :show-inheritance:
   :undoc-members:
```
