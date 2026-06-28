(workflow)=

# Workflow

## Development environment

[uv] is a required package to develop.

```console
$ git clone https://github.com/vcs-python/libvcs.git
```

```console
$ cd libvcs
```

```console
$ uv install -E "docs test coverage lint"
```

Justfile commands prefixed with `watch-` will watch files and rerun.

## Tests

```console
$ uv run py.test
```

Helpers: `just test` Rerun tests on file change: `just watch-test` (requires [entr(1)])

### Running tests in parallel

The suite spawns real `git`, `hg`, and `svn` processes, so on a multi-core
machine it runs faster across workers with [pytest-xdist] (a dev dependency):

```console
$ just test-parallel
```

This runs `uv run py.test -n auto`, where `auto` sizes the worker pool to the
machine's cores. Parallelism is opt-in — `just test` and `uv run py.test` stay
serial by default.

### Order independence

Tests must pass regardless of the order they run in. Parallel and shuffled runs
spread tests across workers, so any hidden coupling — shared global state, or a
fixture that leaks into a later test — surfaces as a failure. Keep fixtures
self-contained and reset any global state in teardown. Check locally with a
shuffled run:

```console
$ uv run --with pytest-randomly py.test -p randomly
```

## Documentation

Default preview server: http://localhost:8068

[sphinx-autobuild] will automatically build the docs, watch for file changes and launch a server.

From home directory: `just start-docs` From inside `docs/`: `just start`

[sphinx-autobuild]: https://github.com/executablebooks/sphinx-autobuild

### Manual documentation (the hard way)

`cd docs/` and `just html` to build. `just serve` to start http server.

Helpers: `just build-docs`, `just serve-docs`

Rebuild docs on file change: `just watch-docs` (requires [entr(1)])

Rebuild docs and run server via one terminal: `just dev-docs`

## Formatting / linting

### ruff

The project uses [ruff] to handle formatting, sorting imports and linting.

````{tab} Command

uv:

```console
$ uv run ruff
```

If you setup manually:

```console
$ ruff check .
```

````

````{tab} just

```console
$ just ruff
```

````

````{tab} Watch

```console
$ just watch-ruff
```

requires [`entr(1)`].

````

````{tab} Fix files

uv:

```console
$ uv run ruff check . --fix
```

If you setup manually:

```console
$ ruff check . --fix
```

````

#### ruff format

[ruff format] is used for formatting.

````{tab} Command

uv:

```console
$ uv run ruff format .
```

If you setup manually:

```console
$ ruff format .
```

````

````{tab} just

```console
$ just ruff-format
```

````

### mypy

[mypy] is used for static type checking.

````{tab} Command

uv:

```console
$ uv run mypy .
```

If you setup manually:

```console
$ mypy .
```

````

````{tab} just

```console
$ just mypy
```

````

````{tab} Watch

```console
$ just watch-mypy
```

requires [`entr(1)`].
````

## Releasing

Since this software is used in production projects, we don't want to release breaking changes.

Choose what the next version is. Assuming it's version 0.9.0, it could be:

- 0.9.0post0: postrelease, if there was a packaging issue
- 0.9.1: bugfix / security / tweak
- 0.10.0: breaking changes, new features

Let's assume we pick 0.9.1

`CHANGES`: Assure any PRs merged since last release are mentioned. Give a thank you to the
contributor. Set the header with the new version and the date. Leave the "current" header and
_Insert changes/features/fixes for next release here_ at the top::

    current
    -------
    - *Insert changes/features/fixes for next release here*

    libvcs 0.9.1 (2020-10-12)
    -------------------------
    - :issue:`1`: Fix bug

`libvcs/__init__.py` and `__about__.py` - Set version

```console
$ git commit -m 'Tag v0.9.1'
```

```console
$ git tag v0.9.1
```

After `git push` and `git push --tags`, CI will automatically build and deploy to PyPI.

### Releasing (manual)

As of 0.10, [uv] handles virtualenv creation, package requirements, versioning, building, and
publishing. Therefore there is no setup.py or requirements files.

Update `__version__` in `__about__.py` and `pyproject.toml`::

    git commit -m 'build(libvcs): Tag v0.1.1'
    git tag v0.1.1
    git push
    git push --tags
    uv build
    uv publish

[uv]: https://github.com/astral-sh/uv 
[pytest-xdist]: https://pytest-xdist.readthedocs.io/
[entr(1)]: http://eradman.com/entrproject/
[`entr(1)`]: http://eradman.com/entrproject/
[ruff format]: https://docs.astral.sh/ruff/formatter/
[ruff]: https://ruff.rs
[mypy]: http://mypy-lang.org/
