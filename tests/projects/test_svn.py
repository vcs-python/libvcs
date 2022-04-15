"""tests for libvcs svn repos."""
import os
import pathlib

import pytest

from libvcs.cmd.core import which
from libvcs.conftest import CreateProjectCallbackFixtureProtocol
from libvcs.projects.svn import SubversionProject
from libvcs.shortcuts import create_project_from_pip_url

if not which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_repo_svn(tmp_path: pathlib.Path, svn_remote_repo):
    repo_name = "my_svn_project"

    svn_repo = create_project_from_pip_url(
        **{
            "pip_url": f"svn+file://{svn_remote_repo}",
            "dir": tmp_path / repo_name,
        }
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
):
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SubversionProject(
        dir=svn_repo_checkout_dir, url=f"file://{svn_server!s}"
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert svn_repo_checkout_dir.exists()
