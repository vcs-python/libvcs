"""Tests for libvcs.cmd.hg."""

from __future__ import annotations

import pathlib
import shutil
import typing as t

import pytest

from libvcs.cmd.hg import Hg

if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture

if not shutil.which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


def test_hg_run_accepts_scalar_string(tmp_path: pathlib.Path) -> None:
    """Mercurial run() should not split scalar command strings."""
    repo = Hg(path=tmp_path)

    result = repo.run("help")

    assert "Mercurial Distributed SCM" in result


def test_hg_run_timeout_propagates_to_runner(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """``Hg.run(timeout=X)`` forwards X to the underlying ``run()``."""
    repo = Hg(path=tmp_path)
    mock_run = mocker.patch("libvcs.cmd.hg.run", return_value="")

    repo.run(["help"], timeout=2.5)

    _args, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 2.5
