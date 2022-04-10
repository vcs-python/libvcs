"""pytest fixtures. Live inside libvcs for doctest."""
import getpass
import pathlib
import shutil
import textwrap
from typing import Any

import pytest

from libvcs.states.git import GitRepo, RemoteDict
from libvcs.util import run


@pytest.fixture(autouse=True)
def home_default(monkeypatch: pytest.MonkeyPatch, user_path: pathlib.Path):
    monkeypatch.setenv("HOME", str(user_path))


@pytest.fixture(autouse=True, scope="session")
def home_path(tmp_path_factory: pytest.TempPathFactory):
    return tmp_path_factory.mktemp("home")


@pytest.fixture(autouse=True, scope="session")
def user_path(home_path: pathlib.Path):
    p = home_path / getpass.getuser()
    p.mkdir()
    return p


@pytest.fixture(autouse=True)
def gitconfig(user_path: pathlib.Path, home_default: pathlib.Path):
    gitconfig = user_path / ".gitconfig"
    user_email = "libvcs@git-pull.com"
    gitconfig.write_text(
        textwrap.dedent(
            f"""
  [user]
    email = {user_email}
    name = {getpass.getuser()}
    """
        ),
        encoding="utf-8",
    )

    output = run(["git", "config", "--get", "user.email"])
    assert user_email in output, "Should use our fixture config and home directory"

    return gitconfig


@pytest.fixture(autouse=True)
def add_doctest_fixtures(
    doctest_namespace: dict[str, Any],
    tmp_path: pathlib.Path,
    home_default: pathlib.Path,
    gitconfig: pathlib.Path,
    git_remote_repo: pathlib.Path,
    svn_remote_repo: pathlib.Path,
):
    doctest_namespace["tmp_path"] = tmp_path
    doctest_namespace["gitconfig"] = gitconfig
    doctest_namespace["git_remote_repo"] = git_remote_repo
    doctest_namespace["svn_remote_repo"] = svn_remote_repo


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
def git_remote_repo(
    repos_path: pathlib.Path, gitconfig: pathlib.Path, home_default: pathlib.Path
):
    """Create a git repo with 1 commit, used as a remote."""
    name = "dummyrepo"
    repo_dir = repos_path / name

    run(["git", "init", name], cwd=repos_path)

    testfile_filename = "testfile.test"

    run(["touch", testfile_filename], cwd=repo_dir)
    run(["git", "add", testfile_filename], cwd=repo_dir)
    run(["git", "commit", "-m", "test file for %s" % name], cwd=repo_dir)

    return repo_dir


@pytest.fixture
def svn_remote_repo(repos_path, scope="session"):
    """Create a git repo with 1 commit, used as a remote."""
    server_dirname = "server_dir"
    server_dir = repos_path / server_dirname

    run(["svnadmin", "create", server_dir])

    return server_dir


@pytest.fixture
def git_repo(repos_path: pathlib.Path, git_remote_repo: pathlib.Path):
    """Create an git repository for tests. Return repo."""
    git_repo = GitRepo(
        url=f"file://{git_remote_repo}",
        repo_dir=str(repos_path / "git_repo"),
        remotes={
            "origin": RemoteDict(
                **{
                    "push_url": f"file://{git_remote_repo}",
                    "fetch_url": f"file://{git_remote_repo}",
                }
            )
        },
    )
    git_repo.obtain()
    return git_repo
