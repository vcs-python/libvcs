import pathlib
import shutil

import pytest

from libvcs.pytest_plugin import CreateProjectCallbackFixtureProtocol


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_create_git_remote_repo(
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_remote_1 = create_git_remote_repo()
    git_remote_2 = create_git_remote_repo()

    assert git_remote_1 != git_remote_2


@pytest.mark.skipif(not shutil.which("svn"), reason="svn is not available")
def test_create_svn_remote_repo(
    create_svn_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    svn_remote_1 = create_svn_remote_repo()
    svn_remote_2 = create_svn_remote_repo()

    assert svn_remote_1 != svn_remote_2
