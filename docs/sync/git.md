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

```{eval-rst}
.. automodule:: libvcs.sync.git
   :members:
   :show-inheritance:
   :undoc-members:
```
