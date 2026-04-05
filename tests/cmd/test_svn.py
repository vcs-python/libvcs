"""Tests for libvcs.cmd.svn."""

from __future__ import annotations

import pathlib
import shutil

import pytest

from libvcs.cmd.svn import Svn

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_svn_run_accepts_scalar_string(tmp_path: pathlib.Path) -> None:
    """Subversion run() should not split scalar command strings."""
    repo = Svn(path=tmp_path)

    result = repo.run("help")

    assert "usage: svn <subcommand> [options] [args]" in result
