(code-style)=

# Code Style

Formatting, typing, and import conventions moved to
[`.github/CONTRIBUTING.md`][contributing-file]; the NumPy docstring
convention moved to [`.github/WRITING.md`][writing-file]. This page keeps
the one runnable example that used to live here, because it is collected as
a test under `docs/` — moving it into `.github/` would stop it running.

```python
>>> def fetch(url: str, *, branch: str | None = None) -> str:
...     """Fetch a remote branch.
...
...     Parameters
...     ----------
...     url : str
...         Repository URL.
...     branch : str or None
...         Branch name. ``None`` means the default branch.
...
...     Returns
...     -------
...     str
...         The fetched commit hash.
...     """
...     return "abc123"
```

[contributing-file]: https://github.com/vcs-python/libvcs/blob/master/.github/CONTRIBUTING.md
[writing-file]: https://github.com/vcs-python/libvcs/blob/master/.github/WRITING.md
