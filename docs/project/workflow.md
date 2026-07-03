(workflow)=

# Workflow

## Development environment

Development requires [uv].

```console
$ git clone https://github.com/vcs-python/libvcs.git
```

```console
$ cd libvcs
```

Install the project and its development dependency groups:

```console
$ uv sync
```

Justfile commands prefixed with `watch-` will watch files and rerun.

## Tests

```console
$ uv run py.test
```

Helper: `just test`. Rerun tests on file change: `just watch-test` (requires [entr(1)]).

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

From the project root: `just start-docs`. From inside `docs/`: `just start`.

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
$ uv run ruff check .
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

See {ref}`releasing` for the version policy and release checklist.

[uv]: https://github.com/astral-sh/uv
[pytest-xdist]: https://pytest-xdist.readthedocs.io/
[entr(1)]: http://eradman.com/entrproject/
[`entr(1)`]: http://eradman.com/entrproject/
[ruff format]: https://docs.astral.sh/ruff/formatter/
[ruff]: https://ruff.rs
[mypy]: http://mypy-lang.org/
