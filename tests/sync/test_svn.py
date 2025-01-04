"""Tests for libvcs svn repos."""

from __future__ import annotations

import shutil
import typing as t

import pytest

from libvcs.sync.svn import SvnSync

if t.TYPE_CHECKING:
    import pathlib

    from libvcs.pytest_plugin import CreateRepoPytestFixtureFn

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_svn_sync(tmp_path: pathlib.Path, svn_remote_repo: pathlib.Path) -> None:
    """Tests for SvnSync."""
    repo_name = "my_svn_project"

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo}",
        path=str(tmp_path / repo_name),
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert (tmp_path / repo_name).exists()


def test_svn_sync_with_files(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """Tests for SvnSync."""
    repo_name = "my_svn_project"

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo_with_files}",
        path=str(tmp_path / repo_name),
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 3

    assert (tmp_path / repo_name).exists()


def test_repo_svn_remote_checkout(
    create_svn_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for SvnSync with remote checkout."""
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SvnSync(path=svn_repo_checkout_dir, url=f"file://{svn_server!s}")

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert svn_repo_checkout_dir.exists()
