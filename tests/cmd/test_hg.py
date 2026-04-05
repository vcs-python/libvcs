"""Tests for libvcs.cmd.hg."""

from __future__ import annotations

import pathlib
import shutil

import pytest

from libvcs.cmd.hg import Hg

if not shutil.which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


def test_hg_run_accepts_scalar_string(tmp_path: pathlib.Path) -> None:
    """Mercurial run() should not split scalar command strings."""
    repo = Hg(path=tmp_path)

    result = repo.run("help")

    assert "Mercurial Distributed SCM" in result
