"""tests for libvcs svn repos."""
import os
import pathlib
import shutil

import pytest

from libvcs.pytest_plugin import CreateProjectCallbackFixtureProtocol
from libvcs.sync.svn import SvnSync

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_repo_svn(tmp_path: pathlib.Path, svn_remote_repo: pathlib.Path) -> None:
    repo_name = "my_svn_project"

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo}",
        dir=str(tmp_path / repo_name),
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert os.path.exists(tmp_path / repo_name)


def test_repo_svn_remote_checkout(
    create_svn_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SvnSync(dir=svn_repo_checkout_dir, url=f"file://{svn_server!s}")

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert svn_repo_checkout_dir.exists()
