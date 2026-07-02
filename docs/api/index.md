(api)=

(reference)=

# API Reference

libvcs exposes three public subsystems -- URL parsing, command execution,
and repository synchronization -- plus a pytest plugin for test fixtures.

All APIs are pre-1.0 and may change between minor versions.
Pin to a range, e.g. `libvcs>=0.45,<0.46`.

## Subsystems

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} URL Parsing
:link: /url/index
:link-type: doc
Detect, validate, and normalize Git / Hg / SVN URLs.
Typed dataclasses with pip- and npm-style support.
:::

:::{grid-item-card} Commands
:link: /cmd/index
:link-type: doc
Thin Python wrappers around `git`, `hg`, and `svn` CLIs.
Fine-grained control over individual VCS operations.
:::

:::{grid-item-card} Sync
:link: /sync/index
:link-type: doc
High-level clone-and-update for local repositories.
One call to fetch or create a working copy.
:::

:::{grid-item-card} pytest Plugin
:link: /api/pytest-plugin
:link-type: doc
Per-test isolated Git, SVN, and Mercurial repository fixtures,
backed by session-cached remotes. Drop-in test isolation.
:::

::::

```{toctree}
:hidden:

/url/index
/cmd/index
/sync/index
pytest-plugin
```
