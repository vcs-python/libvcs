(internals)=

# Internals

:::{warning}
Be careful with these! Internal APIs are **not** covered by version policies. They can break or be removed between minor versions!

If you need an internal API stabilized please [file an issue](https://github.com/vcs-python/libvcs/issues).
:::

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Exceptions
:link: exc
:link-type: doc
Error hierarchy for VCS operations.
:::

:::{grid-item-card} Types
:link: types
:link-type: doc
Shared type aliases and protocols.
:::

:::{grid-item-card} Dataclasses
:link: dataclasses
:link-type: doc
Internal dataclass utilities.
:::

:::{grid-item-card} QueryList
:link: query_list
:link-type: doc
Filterable list for object collections.
:::

:::{grid-item-card} Run
:link: run
:link-type: doc
Runtime helpers and environment utilities.
:::

:::{grid-item-card} Subprocess
:link: subprocess
:link-type: doc
Subprocess wrappers for VCS binaries.
:::

:::{grid-item-card} Shortcuts
:link: shortcuts
:link-type: doc
Convenience functions for common operations.
:::

::::

```{toctree}
:hidden:

exc
types
dataclasses
query_list
run
async_run
subprocess
async_subprocess
shortcuts
```
