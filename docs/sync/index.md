(projects)=

# Sync - `libvcs.sync`

Keep a local checkout in sync with its remote: {meth}`~libvcs.sync.git.GitSync.update_repo`
and its Mercurial and Subversion counterparts create the checkout when it
doesn't exist yet and update it when it does, through
{class}`~libvcs.sync.git.GitSync`, {class}`~libvcs.sync.hg.HgSync`, and
{class}`~libvcs.sync.svn.SvnSync` — built on top of {mod}`libvcs.cmd`.
Use `obtain()` only to create the initial checkout.

`update_repo()` returns a {class}`~libvcs.sync.base.SyncResult`. Check its
`ok` flag before proceeding; failed results retain ordered errors with the
operation that failed. These examples use disposable repositories from
libvcs's {doc}`pytest fixtures </api/pytest-plugin>`.

```python
>>> result = example_git_repo.update_repo()
>>> result.ok
True
>>> [(error.step, error.message) for error in result.errors]
[]
```

Compare to:
[`fabtools.require.git`](https://fabtools.readthedocs.io/en/0.19.0/api/require/git.html),
[`salt.states.git`](https://docs.saltproject.io/en/latest/ref/states/all/salt.states.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

## Read the checkout position

Use `get_position()` to inspect the checkout before choosing an update policy.
It returns an immutable {class}`~libvcs.sync.base.WorkingCopyPosition` from
local metadata. It does not fetch or contact a server.

```python
>>> position = example_git_repo.get_position()
>>> position.ref_kind
'branch'
>>> position.revision == example_git_repo.get_revision()
True
>>> position.follows
True
```

Git reports an attached branch or a detached commit. Mercurial reports its
active bookmark when present, otherwise its named branch. Subversion reports
the checkout URL and root base revision; `mixed` and `switched` identify
working copies whose children cannot be described by the root alone.

(sync-policies)=

## Choose an update policy

The default `SyncPolicy(drift="follow", dirty="abort")` follows the selected
target and aborts on detected local changes. Pass `target=SyncTarget(...)`
and `policy=SyncPolicy(...)` to `update_repo()` to choose another behavior.
A method target replaces the constructor's `rev` default.

| Policy | Behavior |
| --- | --- |
| `drift="follow"` | Update to the selected target using native VCS rules. |
| `drift="keep"` | Leave an existing checkout at its current position. |
| `drift="warn"` | Keep its position and report a resolved target mismatch. |
| `dirty="abort"` | Refuse updates while ordinary local changes are present. |
| `dirty="preserve"` | Retain recoverable changes, update, then restore them; conflicts remain visible. |
| `dirty="discard"` | Explicitly discard supported ordinary local changes. |

The library does not prompt for discard. Preservation never falls back to
discard. Existing Git and Hg keep/warn operations inspect local targets
without fetching or changing attachment; different names at the same revision
do not count as drift. New checkouts establish the configured target first.
SVN keep/warn needs a numeric revision for local comparison: remote `HEAD`
cannot be resolved without contacting the server.

(sync-recovery)=

## Preserve and recover local changes

Preservation returns a token when it captures changes. Keep that token even
when `result.ok` is false: `update_state`, `preservation_state`, `conflicts`,
and `errors` describe separate update and restoration outcomes.

This example selects an earlier Git commit while retaining an untracked note,
then recovers the original checkout into a separate directory:

```python
>>> from libvcs import SyncPolicy, SyncTarget
>>> repo = example_git_repo
>>> target = SyncTarget(commit=repo.get_revision())
>>> _ = repo.run(["commit", "--allow-empty", "-m", "local work"])
>>> original_revision = repo.get_revision()
>>> _ = (repo.path / "notes.txt").write_text("keep this note\n")
>>> result = repo.update_repo(target=target, policy=SyncPolicy(dirty="preserve"))
>>> result.ok, result.update_state, result.preservation_state
(True, 'completed', 'restored')
>>> result.conflicts, result.errors
((), [])
>>> token = result.recovery
>>> assert token is not None
>>> repo.get_revision() == target.commit
True
>>> (repo.path / "notes.txt").read_text()
'keep this note\n'
>>> token in [record.recovery for record in repo.list_recoveries()]
True
>>> destination = tmp_path / "recovered"
>>> recovered = repo.recover_changes(token, destination=destination)
>>> recovered.ok, recovered.preservation_state
(True, 'restored')
>>> from libvcs import GitSync
>>> copy = GitSync(url=repo.url, path=destination)
>>> copy.get_revision() == original_revision
True
>>> (destination / "notes.txt").read_text()
'keep this note\n'
>>> repo.release_changes(token)
>>> repo.list_recoveries()
()
```

Release only after verifying the retained changes. Tokens remain after a
successful restoration, conflict, failed update, or separate recovery;
recovery is repeatable until explicit release. `recovery` is `None` when no
capture was needed. Discovery can return damaged or incomplete records with
errors, so a token alone does not certify usable recovery material.

`recover_changes()` writes a new checkout; it does not overwrite the source
or resume an interrupted update. Its destination must not exist, must have
an existing parent, and must not overlap the source or recovery storage.
Interrupted records block automatic updates; listing them does not resume
work. Prevent external editors and VCS writers during these operations: the
POSIX ownership lock coordinates libvcs operations only.

Recovery uses local material. Its dependencies and admitted repository layouts
differ for {doc}`Git <git>`, {doc}`Mercurial <hg>`, and {doc}`Subversion <svn>`.
Process-death tests cover persisted operation boundaries and an active Git
checkout; they do not establish power-loss durability or arbitrary native
command interruption guarantees.

## Modules

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Git Sync
:link: git
:link-type: doc
Clone, fetch, and update Git repositories.
:::

:::{grid-item-card} Hg Sync
:link: hg
:link-type: doc
Clone and update Mercurial repositories.
:::

:::{grid-item-card} SVN Sync
:link: svn
:link-type: doc
Checkout and update Subversion working copies.
:::

:::{grid-item-card} Base
:link: base
:link-type: doc
Abstract base class for all sync backends.
:::

::::

## Constants

```{eval-rst}
.. automodule:: libvcs.sync.constants
   :members:
```

```{toctree}
:hidden:

git
hg
svn
base
```
