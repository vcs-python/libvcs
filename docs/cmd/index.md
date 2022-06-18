(cmd)=

# `libvcs.cmd`

Compare to: [`fabtools.git`](https://fabtools.readthedocs.io/en/0.19.0/api/git.html#git-module),
[`salt.modules.git`](https://docs.saltproject.io/en/latest/ref/modules/all/salt.modules.git.html),
[`ansible.builtin.git`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/git_module.html)

:::{warning}

All APIs are considered experimental and subject to break pre-1.0. They can and will break between
versions.

:::

```{toctree}
:caption: API

git
hg
svn
```

## Controlling commands

### Override `run()`

You want to control `stdout`, `stderr`, terminal output, tee'ing or logging, introspect and modify
the commands themselves. libvcs is designed to make this trivial to control.

- Git -> `Git.<command>` -> `Git.run` -> `run`

You override `Git.run` method, and all `Git` commands can be intercepted.

```python

class MyGit(Git):
    def run(self, *args, **kwargs):
        return ...
```

You can also pass-through using `super()`

```python

class MyGit(Git):
    def run(self, *args, **kwargs):
        return super().run(*args, **kwargs)
```

Two possibilities:

1. Modify args / kwargs before running them
2. Replace `run()` with a different subprocess runner

### `LazySubprocessMixin`

```python

class MyGit(Git, LazySubprocessMixin):
    def run(self, *args, **kwargs):
        return ...
```

You can introspect it here.

Instead of `git.run(...)` you'd do `git.run(...).run()`.

Also, you can introspect and modify the output before execution

```python
>>> mycmd = git.run(...)
>>> mycmd.flags
...
>>> mycmd.flags = '--help'
>>> mycmd.run()
```
