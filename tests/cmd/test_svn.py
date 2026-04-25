"""Tests for libvcs.cmd.svn."""

from __future__ import annotations

import pathlib
import shutil
import typing as t

import pytest

from libvcs.cmd.svn import Svn

if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_svn_run_accepts_scalar_string(tmp_path: pathlib.Path) -> None:
    """Subversion run() should not split scalar command strings."""
    repo = Svn(path=tmp_path)

    result = repo.run("help")

    assert "usage: svn <subcommand> [options] [args]" in result


def test_svn_run_timeout_propagates_to_runner(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """``Svn.run(timeout=X)`` forwards X to the underlying ``run()``."""
    repo = Svn(path=tmp_path)
    mock_run = mocker.patch("libvcs.cmd.svn.run", return_value="")

    repo.run(["help"], timeout=2.5)

    _args, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 2.5
