(adr-order-independent-tests)=

# ADR 0002: Order-independent tests with opt-in parallelism

## Status

Accepted. 2026-06-28.

## Context

The test suite is subprocess-bound: it spawns real `git`, `hg`, and `svn`
processes and writes working copies to disk. Wall-time lives in process
spawning and filesystem I/O, not Python, so the single largest lever for a
faster suite is running independent tests across CPU cores.

Parallel execution (and, equivalently, shuffled execution) is only safe when
the suite is **order-independent**: every test must pass regardless of what ran
before it. The suite was not. Two pieces of shared mutable state passed in the
fixed collection order but failed once tests were reordered:

- `libvcs.url.registry.VCSRegistry` stored its `parser_map` in a class
  variable, so constructing any second registry mutated the module-level
  `registry` singleton — whichever test built a custom registry first changed
  URL detection for every later test.
- The `git_repo` / `hg_repo` pytest fixtures handed the first consumer a live
  handle to a session-cached master checkout. The first test to use the fixture
  could mutate that cache (add a remote, switch a branch), leaking state into
  every later test that copied it.

These were invisible under the default order and surfaced only when a
shuffled run (`pytest-randomly`) or a parallel run (`pytest-xdist`) changed
which tests ran together and in what sequence. They are also genuine bugs for
downstream consumers (e.g. vcspull) that build on `VCSRegistry` and the
fixtures, independent of how the tests run.

## Decision

Two coupled commitments — the invariant is the prerequisite for the mechanism.

### Tests are order-independent

No shared mutable state may leak across tests. Coupling is fixed at the source,
never hidden behind a fixed order or a co-locating scheduler:

- `VCSRegistry.parser_map` is a per-instance attribute; each registry is
  independent and the global `registry` is never mutated by constructing
  another.
- The `git_repo` / `hg_repo` / `svn_repo` fixtures treat the master checkout as
  a pristine, read-only cache and hand every consumer — including the first —
  its own copy. A test may mutate its checkout freely without affecting any
  other.

The expectation is documented in {ref}`workflow` so contributors keep new tests
order-independent, with a shuffled-run check (`uv run --with pytest-randomly
py.test -p randomly`).

### Parallelism is opt-in, not the default

`pytest-xdist` is a development dependency exposed via `just test-parallel`
(`uv run py.test -n auto`). The default `uv run py.test` stays serial.

- The worker count is **not** hardcoded. `-n auto` adapts to the machine; the
  operator caps it when needed. A subprocess-bound suite oversubscribes on
  high-core machines, so a fixed count committed to `addopts` would be wrong
  somewhere.
- The default scheduler (`load`) is used. A co-locating scheduler (`loadfile`)
  was trialled as a workaround for the order-coupling, but once the coupling is
  fixed it is unnecessary, so it is not committed.

## Alternatives considered

| Approach | order-safe | default unchanged | portable | chosen |
|----------|:----------:|:-----------------:|:--------:|:------:|
| Fix coupling at source + opt-in `-n auto` (`load`) | yes | yes | yes | **yes** |
| Keep `--dist=loadfile` workaround, leave coupling | masks it | yes | yes | no |
| `-n auto` in `addopts` (always parallel) | needs fix | no | no | no |
| Hardcode a worker count (e.g. `-n 12`) | needs fix | no | no | no |
| `pytest-randomly` as a committed CI gate | detects only | yes | yes | deferred |

The decisive point: a co-locating scheduler only *hides* order-coupling, and it
was measured to be no faster than the default scheduler once the coupling was
fixed — so the coupling is fixed and the workaround dropped. `pytest-randomly`
detects order-coupling but does not parallelize; it is used transiently for
checks (`uv run --with pytest-randomly`) rather than committed.

## Consequences

### Positive

- The suite passes under serial, shuffled, and parallel (`-n auto`) execution.
- Two real isolation bugs in shipped code (`VCSRegistry`, the repo fixtures)
  are fixed, benefiting downstream consumers regardless of parallelism.
- A faster opt-in run is available without changing the stable default.

### Tradeoffs

- Parallel wall-time varies with machine load, and `-n auto` can oversubscribe
  a subprocess-bound suite on high-core machines — the operator picks the
  worker count.
- Contributors must keep new tests order-independent (reset global state in
  teardown; isolate per-test resources).

### Risks

- A future order-coupling could reintroduce flakiness that appears only under
  parallel or shuffled runs. Mitigation: the order-independence expectation is
  documented with a shuffled-run check, so the regression is reproducible.

## Prior art

- `pytest-xdist` provides the `load`, `loadscope`, and `loadfile` schedulers;
  its guidance is that tests must be independent for `load` to be safe.
- `pytest-randomly` randomizes order specifically to surface inter-test
  coupling.
- The broader convention across test suites: parallel execution requires
  order-independent tests, and shared mutable state (global registries, cached
  fixtures handed out by reference) is the usual cause of order-dependent
  failures.
