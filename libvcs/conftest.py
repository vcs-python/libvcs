"""pytest fixtures. Live inside libvcs for doctest."""
import functools
import getpass
import pathlib
import shutil
import textwrap
from typing import Any, Optional, Protocol

import pytest

from faker import Faker

from libvcs.cmd.core import run, which
from libvcs.projects.git import GitProject, GitRemoteDict

skip_if_git_missing = pytest.mark.skipif(
    not which("git"), reason="git is not available"
)
skip_if_svn_missing = pytest.mark.skipif(
    not which("svn"), reason="svn is not available"
)
skip_if_hg_missing = pytest.mark.skipif(not which("hg"), reason="hg is not available")


def pytest_ignore_collect(path, config: pytest.Config):
    if not which("svn") and any(needle in path for needle in ["svn", "subversion"]):
        return True
    if not which("git") and "git" in path:
        return True
    if not which("hg") and any(needle in path for needle in ["hg", "mercurial"]):
        return True

    return False


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
@pytest.mark.usefixtures("home_default")
@skip_if_git_missing
def gitconfig(user_path: pathlib.Path):
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


@pytest.fixture(autouse=True, scope="session")
@pytest.mark.usefixtures("home_default")
@skip_if_hg_missing
def hgconfig(user_path: pathlib.Path):
    hgrc = user_path / ".hgrc"
    hgrc.write_text(
        textwrap.dedent(
            f"""
        [ui]
        username = libvcs tests <libvcs@git-pull.com>
        merge = internal:merge

        [trusted]
        users = {getpass.getuser()}
    """
        ),
        encoding="utf-8",
    )
    return hgrc


@pytest.fixture(scope="function")
def projects_path(user_path: pathlib.Path, request: pytest.FixtureRequest):
    """User's local checkouts and clones. Emphemeral directory."""
    dir = user_path / "projects"
    dir.mkdir(exist_ok=True)

    def clean():
        shutil.rmtree(dir)

    request.addfinalizer(clean)
    return dir


@pytest.fixture(scope="function")
def remote_repos_path(user_path: pathlib.Path, request: pytest.FixtureRequest):
    """System's remote (file-based) repos to clone andpush to. Emphemeral directory."""
    dir = user_path / "remote_repos"
    dir.mkdir(exist_ok=True)

    def clean():
        shutil.rmtree(dir)

    request.addfinalizer(clean)
    return dir


class CreateProjectCallbackProtocol(Protocol):
    def __call__(self, remote_repo_path: pathlib.Path):
        ...


class CreateProjectCallbackFixtureProtocol(Protocol):
    def __call__(
        self,
        remote_repos_path: Optional[pathlib.Path] = None,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    ):
        ...


def _create_git_remote_repo(
    remote_repos_path: pathlib.Path,
    remote_repo_name: str,
    remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
) -> pathlib.Path:
    remote_repo_path = remote_repos_path / remote_repo_name
    run(["git", "init", remote_repo_name], cwd=remote_repos_path)

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


@pytest.fixture
@skip_if_git_missing
def create_git_remote_repo(remote_repos_path: pathlib.Path, faker: Faker):
    """Factory. Create git remote repo to for clone / push purposes"""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    ):
        return _create_git_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else faker.slug(),
            remote_repo_post_init=remote_repo_post_init,
        )

    return fn


def git_remote_repo_single_commit_post_init(remote_repo_path: pathlib.Path):
    testfile_filename = "testfile.test"
    run(["touch", testfile_filename], cwd=remote_repo_path)
    run(["git", "add", testfile_filename], cwd=remote_repo_path)
    run(["git", "commit", "-m", "test file for dummyrepo"], cwd=remote_repo_path)


@pytest.fixture
@pytest.mark.usefixtures("gitconfig", "home_default")
@skip_if_git_missing
def git_remote_repo(remote_repos_path: pathlib.Path):
    """Pre-made git repo w/ 1 commit, used as a file:// remote to clone and push to."""
    return _create_git_remote_repo(
        remote_repos_path=remote_repos_path,
        remote_repo_name="dummyrepo",
        remote_repo_post_init=git_remote_repo_single_commit_post_init,
    )


def _create_svn_remote_repo(
    remote_repos_path: pathlib.Path,
    remote_repo_name: str,
    remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
) -> pathlib.Path:
    """Create a test SVN repo to for checkout / commit purposes"""

    remote_repo_path = remote_repos_path / remote_repo_name
    run(["svnadmin", "create", remote_repo_path])

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


@pytest.fixture
@skip_if_svn_missing
def create_svn_remote_repo(remote_repos_path: pathlib.Path, faker: Faker):
    """Pre-made svn repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    ):
        return _create_svn_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else faker.word(),
            remote_repo_post_init=remote_repo_post_init,
        )

    return fn


@pytest.fixture
@skip_if_svn_missing
def svn_remote_repo(remote_repos_path: pathlib.Path) -> pathlib.Path:
    """Pre-made. Local file:// based SVN server."""
    svn_repo_name = "svn_server_dir"
    remote_repo_path = _create_svn_remote_repo(
        remote_repos_path=remote_repos_path,
        remote_repo_name=svn_repo_name,
        remote_repo_post_init=None,
    )

    return remote_repo_path


def _create_hg_remote_repo(
    remote_repos_path: pathlib.Path,
    remote_repo_name: str,
    remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
) -> pathlib.Path:
    """Create a test hg repo to for checkout / commit purposes"""
    remote_repo_path = remote_repos_path / remote_repo_name
    run(["hg", "init", remote_repo_name], cwd=remote_repos_path)

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


def hg_remote_repo_single_commit_post_init(remote_repo_path: pathlib.Path):
    testfile_filename = "testfile.test"
    run(["touch", testfile_filename], cwd=remote_repo_path)
    run(["hg", "add", testfile_filename], cwd=remote_repo_path)
    run(["hg", "commit", "-m", "test file for hg repo"], cwd=remote_repo_path)


@pytest.fixture
@pytest.mark.usefixtures("hgconfig")
@skip_if_hg_missing
def create_hg_remote_repo(remote_repos_path: pathlib.Path, faker: Faker):
    """Pre-made hg repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    ):
        return _create_hg_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else faker.word(),
            remote_repo_post_init=remote_repo_post_init,
        )

    return fn


@pytest.fixture
@pytest.mark.usefixtures("hgconfig")
@skip_if_hg_missing
def hg_remote_repo(remote_repos_path: pathlib.Path):
    """Pre-made, file-based repo for push and pull."""
    return _create_hg_remote_repo(
        remote_repos_path=remote_repos_path,
        remote_repo_name="dummyrepo",
        remote_repo_post_init=hg_remote_repo_single_commit_post_init,
    )


@pytest.fixture
def git_repo(projects_path: pathlib.Path, git_remote_repo: pathlib.Path):
    """Pre-made git clone of remote repo checked out to user's projects dir."""
    git_repo = GitProject(
        url=f"file://{git_remote_repo}",
        dir=str(projects_path / "git_repo"),
        remotes={
            "origin": GitRemoteDict(
                **{
                    "push_url": f"file://{git_remote_repo}",
                    "fetch_url": f"file://{git_remote_repo}",
                }
            )
        },
    )
    git_repo.obtain()
    return git_repo


@pytest.fixture(autouse=True)
def add_doctest_fixtures(
    doctest_namespace: dict[str, Any],
    tmp_path: pathlib.Path,
    home_default: pathlib.Path,
    gitconfig: pathlib.Path,
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    create_svn_remote_repo: CreateProjectCallbackFixtureProtocol,
    create_hg_remote_repo: CreateProjectCallbackFixtureProtocol,
    git_repo: pathlib.Path,
):
    doctest_namespace["tmp_path"] = tmp_path
    if which("git"):
        doctest_namespace["gitconfig"] = gitconfig
        doctest_namespace["create_git_remote_repo"] = functools.partial(
            create_git_remote_repo,
            remote_repo_post_init=git_remote_repo_single_commit_post_init,
        )
        doctest_namespace["create_git_remote_repo_bare"] = create_git_remote_repo
        doctest_namespace["git_local_clone"] = git_repo
    if which("svn"):
        doctest_namespace["create_svn_remote_repo"] = create_svn_remote_repo
    if which("hg"):
        doctest_namespace["create_hg_remote_repo_bare"] = create_hg_remote_repo
        doctest_namespace["create_hg_remote_repo"] = functools.partial(
            create_hg_remote_repo,
            remote_repo_post_init=hg_remote_repo_single_commit_post_init,
        )
