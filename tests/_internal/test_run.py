"""Tests for libvcs._internal.run."""

from __future__ import annotations

import pathlib

from libvcs._internal.run import _normalize_command_args


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
