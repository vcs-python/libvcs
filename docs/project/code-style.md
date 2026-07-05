(code-style)=

# Code Style

Use this page when you are changing Python code or docstrings and need the
project's formatting, typing, and import conventions. The command examples are
the common local checks; the root contributor guide still owns the full
pre-commit gate.

## Formatting and linting

libvcs uses [ruff](https://ruff.rs) for formatting **and** linting in a
single tool. The full rule set is declared in `pyproject.toml` under
`[tool.ruff]`.

```console
$ uv run ruff format .
```

```console
$ uv run ruff check . --fix --show-fixes
```

## Type checking

[mypy](http://mypy-lang.org/) runs in strict mode:

```console
$ uv run mypy .
```

## Docstrings

All public APIs use **NumPy-style** docstrings:

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

## Imports

- `from __future__ import annotations` at the top of every file.
- Standard-library modules use **namespace imports**: `import pathlib`,
  not `from pathlib import Path`.
- Typing: `import typing as t`, then `t.Optional`, `t.Any`, etc.
