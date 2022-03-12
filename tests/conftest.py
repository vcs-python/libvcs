import getpass
import pathlib
import shutil
from typing import Dict

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run


@pytest.fixture(autouse=True, scope="session")
def home_path(tmp_path_factory: pytest.TempPathFactory):
    return tmp_path_factory.mktemp("home")


@pytest.fixture(autouse=True, scope="session")
def user_path(home_path: pathlib.Path):
    p = home_path / getpass.getuser()
    p.mkdir()
    return p


@pytest.fixture(scope="function")
def repos_path(user_path: pathlib.Path, request: pytest.FixtureRequest):
    """Return temporary directory for repository checkout guaranteed unique."""
    dir = user_path / "repos"
    dir.mkdir(exist_ok=True)

    def clean():
        shutil.rmtree(dir)

    request.addfinalizer(clean)
    return dir


@pytest.fixture
def pip_url_kwargs(repos_path: pathlib.Path, git_remote: pathlib.Path):
    """Return kwargs for :func:`create_repo_from_pip_url`."""
    repo_name = "repo_clone"
    return {
        "pip_url": f"git+file://{git_remote}",
        "repo_dir": repos_path / repo_name,
    }


@pytest.fixture
def git_repo(pip_url_kwargs: Dict):
    """Create an git repository for tests. Return repo."""
    git_repo = create_repo_from_pip_url(**pip_url_kwargs)
    git_repo.obtain()
    return git_repo


@pytest.fixture
def git_remote(repos_path: pathlib.Path):
    """Create a git repo with 1 commit, used as a remote."""
    name = "dummyrepo"
    repo_dir = repos_path / name

    run(["git", "init", name], cwd=repos_path)

    testfile_filename = "testfile.test"

    run(["touch", testfile_filename], cwd=repo_dir)
    run(["git", "add", testfile_filename], cwd=repo_dir)
    run(["git", "commit", "-m", "test file for %s" % name], cwd=repo_dir)

    return repo_dir
