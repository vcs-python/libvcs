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


def test_run_timeout_reaps_child_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timed-out processes are terminated; no zombies remain in the group."""
    script = "import time; time.sleep(10)"

    captured: dict[str, t.Any] = {}
    original_popen = subprocess.Popen

    def _capturing_popen(*args: t.Any, **kwargs: t.Any) -> t.Any:
        proc = original_popen(*args, **kwargs)
        captured["proc"] = proc
        return proc

    # ``monkeypatch.setattr`` auto-restores even if the test body raises and
    # is safe under ``pytest-xdist`` parallel runs, unlike a hand-rolled
    # try/finally around a global assignment.
    monkeypatch.setattr(subprocess, "Popen", _capturing_popen)

    with pytest.raises(exc.CommandTimeoutError):
        run([sys.executable, "-c", script], timeout=0.3)

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


def test_command_timeout_error_renders_duration() -> None:
    """Direct ``CommandTimeoutError`` construction surfaces the duration."""
    err = exc.CommandTimeoutError(
        output="",
        returncode=None,
        cmd="git fetch origin",
        timeout=2.5,
    )

    rendered = str(err)
    assert "timed out after 2.5s" in rendered
    assert "git fetch origin" in rendered
    # Regression guard: the bare ``CommandError`` template would have produced
    # ``"Command failed with code None: ..."`` when ``returncode`` is ``None``.
    assert "code None" not in rendered


def test_command_timeout_error_without_timeout_falls_back() -> None:
    """Omitting ``timeout=`` still produces a readable timeout message."""
    err = exc.CommandTimeoutError(output="partial", cmd="git fetch")

    rendered = str(err)
    assert "timed out" in rendered
    assert "git fetch" in rendered
    assert "partial" in rendered


def test_run_timeout_message_includes_duration() -> None:
    """``run(..., timeout=X)`` raises an exception whose ``str()`` shows X."""
    with pytest.raises(exc.CommandTimeoutError) as excinfo:
        run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.3)

    assert excinfo.value.timeout == 0.3
    rendered = str(excinfo.value)
    assert "timed out after" in rendered
    assert "0.3" in rendered


def test_run_timeout_does_not_deadlock_on_chatty_stdout() -> None:
    """A child filling its stdout pipe must not deadlock the deadline loop.

    The OS pipe buffer is typically 64 KiB on Linux. The child below writes
    well past that before exiting; if the parent only drained ``stderr``, the
    child would block on ``write()`` and only ``terminate()`` would unwedge
    it, losing all the legitimate output.
    """
    script = "import sys; sys.stdout.write('x' * 200000); sys.stdout.flush()"

    output = run([sys.executable, "-c", script], timeout=15.0)

    assert len(output) >= 200000


def test_run_timeout_preserves_stdout_after_exit() -> None:
    """Captured stdout from the deadline loop survives back to the caller."""
    script = "print('preserved'); print('lines')"
    output = run([sys.executable, "-c", script], timeout=10.0)

    assert "preserved" in output
    assert "lines" in output


def test_run_timeout_captures_partial_stdout_on_timeout() -> None:
    """Stdout flushed before the deadline appears in ``CommandTimeoutError.output``."""
    script = (
        "import sys, time; "
        "sys.stdout.write('partial-stdout\\n'); "
        "sys.stdout.flush(); "
        "time.sleep(10)"
    )

    with pytest.raises(exc.CommandTimeoutError) as excinfo:
        run([sys.executable, "-c", script], timeout=0.5)

    assert "partial-stdout" in excinfo.value.output


def test_run_timeout_handles_early_stderr_close_without_hanging() -> None:
    """A child that closes stderr long before exiting must not stall the loop.

    Before the EOF-unregister fix, ``selectors.select`` kept waking on the
    closed-but-readable stderr fd, the read returned ``b""``, and the loop
    spun until the deadline. With the unregister, the stream is removed
    after the first empty read and the loop returns to waiting on the
    remaining fd or the poll interval.
    """
    script = (
        "import os, sys, time; "
        "os.close(sys.stderr.fileno()); "
        "time.sleep(0.2); "
        "print('done')"
    )
    started = time.monotonic()

    output = run([sys.executable, "-c", script], timeout=10.0)

    elapsed = time.monotonic() - started
    assert "done" in output
    # An upper bound that's loose enough not to flake but tight enough to
    # catch a regression where the EOF unregister is undone.
    assert elapsed < 5.0, f"early-stderr-close path took too long: {elapsed:.2f}s"
