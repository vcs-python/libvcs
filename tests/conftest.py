import pathlib
from typing import Dict

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run


@pytest.fixture(scope="function")
def parentdir(tmp_path: pathlib.Path):
    """Return temporary directory for repository checkout guaranteed unique."""
    dir = tmp_path / "repo"
    dir.mkdir()
    return dir


@pytest.fixture
def pip_url_kwargs(parentdir: pathlib.Path, git_remote: pathlib.Path):
    """Return kwargs for :func:`create_repo_from_pip_url`."""
    repo_name = "repo_clone"
    return {
        "pip_url": f"git+file://{git_remote}",
        "repo_dir": parentdir / repo_name,
    }


@pytest.fixture
def git_repo(pip_url_kwargs: Dict):
    """Create an git repository for tests. Return repo."""
    git_repo = create_repo_from_pip_url(**pip_url_kwargs)
    git_repo.obtain()
    return git_repo


@pytest.fixture
def git_remote(parentdir: pathlib.Path):
    """Create a git repo with 1 commit, used as a remote."""
    name = "dummyrepo"
    repo_dir = parentdir / name

    run(["git", "init", name], cwd=parentdir)

    testfile_filename = "testfile.test"

    run(["touch", testfile_filename], cwd=repo_dir)
    run(["git", "add", testfile_filename], cwd=repo_dir)
    run(["git", "commit", "-m", "test file for %s" % name], cwd=repo_dir)

    return repo_dir
