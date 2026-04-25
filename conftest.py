"""Conftest.py (root-level).

We keep this in root pytest fixtures in pytest's doctest plugin to be available, as well
as avoiding conftest.py from being included in the wheel, in addition to pytest_plugin
for pytester only being available via the root directory.

See "pytest_plugins in non-top-level conftest files" in
https://docs.pytest.org/en/stable/deprecations.html
"""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    import pathlib

pytest_plugins = ["pytester"]


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


@pytest.fixture
def fast_timeout_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tighten the deadline-loop spread so test wall-clock budgets stay reliable.

    The two ``_TIMEOUT_*`` constants in :mod:`libvcs._internal.run` are tuned
    for production use (0.5 s SIGTERM grace, 0.1 s selector poll). For tests
    that intentionally fire the deadline, those defaults add up to ~0.7 s of
    unavoidable wall-clock spread on top of the test's nominal timeout, which
    makes upper-bound assertions fragile on loaded CI runners. This fixture
    monkeypatches both to 0.05 s so the spread stays predictable; production
    behaviour is unchanged.
    """
    from libvcs._internal import run as run_module

    monkeypatch.setattr(run_module, "_TIMEOUT_KILL_GRACE_SECONDS", 0.05)
    monkeypatch.setattr(run_module, "_TIMEOUT_POLL_INTERVAL_SECONDS", 0.05)
