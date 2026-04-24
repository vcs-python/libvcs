"""Tests for libvcs._internal.run."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import time
import typing as t

import pytest

from libvcs import exc
from libvcs._internal.run import _normalize_command_args, run


def test_normalize_command_args_keeps_scalar_string() -> None:
    """Scalar strings should remain a single subprocess argument."""
    assert _normalize_command_args("status") == ["status"]


def test_normalize_command_args_keeps_scalar_bytes() -> None:
    """Scalar bytes should remain a single subprocess argument."""
    assert _normalize_command_args(b"status") == [b"status"]


def test_normalize_command_args_expands_sequence() -> None:
    """Sequences should be expanded element by element."""
    assert _normalize_command_args(["status", "--short"]) == ["status", "--short"]


def test_normalize_command_args_coerces_pathlike() -> None:
    """Path-like values should be converted with os.fspath semantics."""
    path = pathlib.Path("example")

    assert _normalize_command_args(path) == ["example"]
    assert _normalize_command_args([path, "status"]) == ["example", "status"]


def test_run_without_timeout_matches_legacy_behavior() -> None:
    """Leaving ``timeout=None`` preserves the pre-timeout call semantics."""
    output = run([sys.executable, "-c", "print('hello'); print('world')"])

    assert "hello" in output
    assert "world" in output


def test_run_raises_command_timeout_when_deadline_exceeded() -> None:
    """A command sleeping past ``timeout`` raises ``CommandTimeoutError`` fast."""
    started = time.monotonic()

    with pytest.raises(exc.CommandTimeoutError) as excinfo:
        run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.3,
        )

    elapsed = time.monotonic() - started

    # Upper bound keeps the test honest: the deadline must actually fire, not
    # fall through to the legacy unbounded wait.
    assert elapsed < 2.5, f"timeout took too long: {elapsed:.2f}s"
    assert isinstance(excinfo.value, exc.CommandError)


def test_run_timeout_captures_partial_stderr_output() -> None:
    """Output produced before the timeout is preserved on ``CommandTimeoutError``."""
    script = (
        "import sys, time;"
        "sys.stderr.write('first\\n');"
        "sys.stderr.flush();"
        "time.sleep(10)"
    )

    with pytest.raises(exc.CommandTimeoutError) as excinfo:
        run(
            [sys.executable, "-c", script],
            timeout=0.5,
            log_in_real_time=True,
        )

    # The pre-timeout stderr chunk is forwarded to the callback and stashed in
    # the exception's ``output`` so callers can diagnose what the process was
    # doing before it was killed.
    assert "first" in excinfo.value.output


def test_run_timeout_reaps_child_process() -> None:
    """Timed-out processes are terminated; no zombies remain in the group."""
    script = "import time; time.sleep(10)"

    captured: dict[str, t.Any] = {}
    original_popen = subprocess.Popen

    def _capturing_popen(*args: t.Any, **kwargs: t.Any) -> t.Any:
        proc = original_popen(*args, **kwargs)
        captured["proc"] = proc
        return proc

    # Attribute replacement keeps the test narrow -- we just need a handle on
    # the Popen that ``run`` created so we can assert the child was actually
    # reaped rather than abandoned (no zombie left behind).
    subprocess.Popen = _capturing_popen  # type: ignore[misc,assignment]
    try:
        with pytest.raises(exc.CommandTimeoutError):
            run([sys.executable, "-c", script], timeout=0.3)
    finally:
        subprocess.Popen = original_popen  # type: ignore[misc]

    proc = captured["proc"]
    # ``returncode`` is only populated once ``wait`` succeeds, so a populated
    # value proves the timeout branch both killed and reaped the child.
    assert proc.returncode is not None


def test_run_without_timeout_completes_successfully() -> None:
    """Regression guard: quick commands return output, no TimeoutError, no hang."""
    output = run([sys.executable, "-c", "print('ok')"])
    assert "ok" in output


def test_run_timeout_none_is_the_default() -> None:
    """Omitting ``timeout`` is equivalent to ``timeout=None``."""
    output = run([sys.executable, "-c", "print('default')"], timeout=None)
    assert "default" in output
