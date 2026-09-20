"""Tests for libvcs svn repos."""

from __future__ import annotations

import shutil
import typing as t

import pytest

from libvcs import exc
from libvcs.sync.base import SyncResult
from libvcs.sync.svn import SvnOptions, SvnSync

if t.TYPE_CHECKING:
    import pathlib

    from libvcs.pytest_plugin import CreateRepoFn

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_svn_position_reports_local_url_and_revision(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """Position reads the working copy after its remote becomes unavailable."""
    remote = tmp_path / "remote"
    shutil.copytree(svn_remote_repo_with_files, remote)
    repo = SvnSync(url=remote.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    shutil.rmtree(remote)

    position = repo.get_position()

    assert (position.ref_kind, position.ref_name) == ("url", repo.url)
    assert position.revision == "3"
    assert position.follows
    assert not position.mixed
    assert not position.switched


def test_svn_position_reports_mixed_and_switched_subtrees(
    tmp_path: pathlib.Path,
    create_svn_remote_repo: CreateRepoFn,
) -> None:
    """A root revision cannot stand in for mixed or switched child entries."""
    remote = create_svn_remote_repo()
    repo = SvnSync(url=remote.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    (repo.path / "trunk").mkdir()
    (repo.path / "trunk" / "file.txt").write_text("first\n")
    repo.cmd.run(["add", "trunk"])
    assert not repo.get_position().mixed
    repo.cmd.run(["commit", "-m", "add trunk"])

    position = repo.get_position()
    assert position.mixed
    assert position.revision == "0"

    repo.cmd.run(["update"])
    repo.cmd.run(["copy", "trunk", "branch"])
    repo.cmd.run(["commit", "-m", "copy branch"])
    repo.cmd.run(["update"])
    repo.cmd.run(["copy", "-r", "1", f"{repo.url}/trunk", "old-copy"])
    assert not repo.get_position().mixed
    repo.cmd.run(["propset", "svn:externals", "--", "-r1 ^/trunk external-copy", "."])
    repo.cmd.run(["update"])
    assert not repo.get_position().mixed
    repo.cmd.run(["switch", f"{repo.url}/branch", "trunk"])

    position = repo.get_position()
    assert not position.mixed
    assert position.switched
    assert position.ref_name == repo.url


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


def test_svn_options_establish_ambient_checkout_depth(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """An empty-depth checkout creates only the working-copy root."""
    checkout = tmp_path / "empty-checkout"
    repo = SvnSync(
        url=svn_remote_repo_with_files.as_uri(),
        path=checkout,
        options=SvnOptions(depth="empty"),
    )

    repo.obtain()

    assert {entry.name for entry in checkout.iterdir()} == {".svn"}


def test_repo_svn_remote_checkout(
    create_svn_remote_repo: CreateRepoFn,
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


def test_update_repo_checkout_failure_returns_sync_result(
    create_svn_remote_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Test that a deleted remote in update_repo() returns SyncResult with error."""
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SvnSync(path=svn_repo_checkout_dir, url=f"file://{svn_server!s}")

    svn_repo.obtain()

    # Delete the remote to cause an update failure
    shutil.rmtree(svn_server)

    result = svn_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "checkout"
    assert isinstance(result.errors[0].exception, exc.CommandError)
