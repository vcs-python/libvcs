"""Conftest.py (root-level).

We keep this in root pytest fixtures in pytest's doctest plugin to be available, as well
as avoiding conftest.py from being included in the wheel, in addition to pytest_plugin
for pytester only being available via the root directory.

See "pytest_plugins in non-top-level conftest files" in
https://docs.pytest.org/en/stable/deprecations.html
"""

from __future__ import annotations

import time
import typing as t
from collections import defaultdict

import pytest

if t.TYPE_CHECKING:
    import pathlib

    from _pytest.fixtures import FixtureDef, SubRequest
    from _pytest.terminal import TerminalReporter

pytest_plugins = ["pytester"]

# Fixture profiling storage
_fixture_timings: dict[str, list[float]] = defaultdict(list)
_fixture_call_counts: dict[str, int] = defaultdict(int)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add fixture profiling options."""
    group = parser.getgroup("libvcs", "libvcs fixture options")
    group.addoption(
        "--fixture-durations",
        action="store",
        type=int,
        default=0,
        metavar="N",
        help="Show N slowest fixture setup times (N=0 for all)",
    )
    group.addoption(
        "--fixture-durations-min",
        action="store",
        type=float,
        default=0.005,
        metavar="SECONDS",
        help="Minimum duration to show in fixture timing report (default: 0.005)",
    )
    group.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests (marked with @pytest.mark.performance)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip performance tests unless --run-performance is given."""
    if config.getoption("--run-performance"):
        # --run-performance given: run all tests
        return

    skip_performance = pytest.mark.skip(reason="need --run-performance option to run")
    for item in items:
        if "performance" in item.keywords:
            item.add_marker(skip_performance)


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(
    fixturedef: FixtureDef[t.Any],
    request: SubRequest,
) -> t.Generator[None, t.Any, t.Any]:
    """Wrap fixture setup to measure timing."""
    start = time.perf_counter()
    try:
        result = yield
        return result
    finally:
        duration = time.perf_counter() - start
        fixture_name = fixturedef.argname
        _fixture_timings[fixture_name].append(duration)
        _fixture_call_counts[fixture_name] += 1


def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    """Display fixture timing summary."""
    durations_count = config.option.fixture_durations
    durations_min = config.option.fixture_durations_min

    # Skip if no timing requested (durations_count defaults to 0 meaning "off")
    if durations_count == 0 and not config.option.verbose:
        return

    # Build summary data
    fixture_stats: list[tuple[str, float, int, float]] = []
    for name, times in _fixture_timings.items():
        total_time = sum(times)
        call_count = len(times)
        avg_time = total_time / call_count if call_count > 0 else 0
        fixture_stats.append((name, total_time, call_count, avg_time))

    # Sort by total time descending
    fixture_stats.sort(key=lambda x: x[1], reverse=True)

    # Filter by minimum duration
    fixture_stats = [s for s in fixture_stats if s[1] >= durations_min]

    if not fixture_stats:
        return

    # Limit count if specified
    if durations_count > 0:
        fixture_stats = fixture_stats[:durations_count]

    terminalreporter.write_sep("=", "fixture setup times")
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"{'Fixture':<40} {'Total':>10} {'Calls':>8} {'Avg':>10}",
    )
    terminalreporter.write_line("-" * 70)

    for name, total, calls, avg in fixture_stats:
        terminalreporter.write_line(
            f"{name:<40} {total:>9.3f}s {calls:>8} {avg:>9.3f}s",
        )


@pytest.fixture(autouse=True)
def add_doctest_fixtures(
    request: pytest.FixtureRequest,
    doctest_namespace: dict[str, t.Any],
) -> None:
    """Configure doctest fixtures for pytest-doctest."""
    from _pytest.doctest import DoctestItem

    if isinstance(request._pyfuncitem, DoctestItem):
        request.getfixturevalue("add_doctest_fixtures")
        request.getfixturevalue("set_home")


@pytest.fixture(autouse=True)
def cwd_default(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Configure current directory for pytest tests."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def setup(
    request: pytest.FixtureRequest,
    gitconfig: pathlib.Path,
    set_home: pathlib.Path,
) -> None:
    """Configure test fixtures for pytest."""
