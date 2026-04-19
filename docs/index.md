(index)=

# libvcs

Typed Python utilities for Git, SVN, and Mercurial. Parse URLs,
execute commands, and synchronize repositories -- all with a
consistent, type-friendly API.

::::{grid} 1 2 3 3
:gutter: 2 2 3 3

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc
Install and parse your first VCS URL in 5 minutes.
:::

:::{grid-item-card} URL Parsing
:link: url/index
:link-type: doc
Parse, validate, and normalize git/hg/svn URLs.
:::

:::{grid-item-card} Commands
:link: cmd/index
:link-type: doc
Typed wrappers for git, hg, and svn CLI operations.
:::

:::{grid-item-card} Sync
:link: sync/index
:link-type: doc
Clone and update local repositories.
:::

:::{grid-item-card} pytest Plugin
:link: /api/pytest-plugin
:link-type: doc
Fixtures for isolated VCS test repos.
:::

:::{grid-item-card} Project
:link: project/index
:link-type: doc
Contributing, code style, release process.
:::

::::

## Install

```console
$ pip install libvcs
```

```console
$ uv add libvcs
```

```{tip}
libvcs is pre-1.0. Pin to a range: `libvcs>=0.39,<0.40`
```

See [Quickstart](quickstart.md) for all methods and first steps.

## At a glance

```python
from libvcs.url.git import GitURL

url = GitURL(url="git@github.com:vcs-python/libvcs.git")
url.hostname  # 'github.com'
url.path      # 'vcs-python/libvcs'

GitURL.is_valid(url="https://github.com/vcs-python/libvcs.git")
# True
```

libvcs gives you typed dataclasses for every parsed URL, thin CLI
wrappers for `git` / `hg` / `svn`, and high-level sync that clones or
updates a local checkout in one call.

| Layer | Module | Purpose |
|-------|--------|---------|
| URL parsing | {mod}`libvcs.url` | Detect, validate, normalize VCS URLs |
| Commands | {mod}`libvcs.cmd` | Execute individual VCS CLI operations |
| Sync | {mod}`libvcs.sync` | Clone and update local repositories |

## Testing

libvcs ships a [pytest plugin](/api/pytest-plugin/) with
session-scoped fixtures for Git, SVN, and Mercurial repositories:

```python
def test_my_tool(create_git_remote_repo):
    repo_path = create_git_remote_repo()
    assert repo_path.exists()
```

```{toctree}
:hidden:

quickstart
topics/index
api/index
internals/index
project/index
history
migration
GitHub <https://github.com/vcs-python/libvcs>
```
