"""pytest fixtures. Live inside libvcs for doctest."""
import functools
import getpass
import pathlib
import random
import shutil
import textwrap
from typing import TYPE_CHECKING, Any, Optional, Protocol

import pytest

from libvcs._internal.run import run
from libvcs.sync.git import GitRemote, GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

skip_if_git_missing = pytest.mark.skipif(
    not shutil.which("git"), reason="git is not available"
)
skip_if_svn_missing = pytest.mark.skipif(
    not shutil.which("svn"), reason="svn is not available"
)
skip_if_hg_missing = pytest.mark.skipif(
    not shutil.which("hg"), reason="hg is not available"
)


class RandomStrSequence:
    def __init__(
        self, characters: str = "abcdefghijklmnopqrstuvwxyz0123456789_"
    ) -> None:
        self.characters: str = characters

    def __iter__(self) -> "RandomStrSequence":
        return self

    def __next__(self) -> str:
        return "".join(random.sample(self.characters, k=8))


namer = RandomStrSequence()


def pytest_ignore_collect(collection_path: pathlib.Path, config: pytest.Config) -> bool:
    if not shutil.which("svn") and any(
        needle in str(collection_path) for needle in ["svn", "subversion"]
    ):
        return True
    if not shutil.which("git") and "git" in str(collection_path):
        return True
    if not shutil.which("hg") and any(
        needle in str(collection_path) for needle in ["hg", "mercurial"]
    ):
        return True

    return False


@pytest.fixture(scope="session")
def home_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    return tmp_path_factory.mktemp("home")


@pytest.fixture(scope="session")
def home_user_name() -> str:
    """Default username to set for :func:`user_path` fixture."""
    return getpass.getuser()


@pytest.fixture(scope="session")
def user_path(home_path: pathlib.Path, home_user_name: str) -> pathlib.Path:
    p = home_path / home_user_name
    p.mkdir()
    return p


@pytest.fixture(scope="function")
def set_home(
    monkeypatch: pytest.MonkeyPatch,
    user_path: pathlib.Path,
) -> None:
    monkeypatch.setenv("HOME", str(user_path))


@pytest.fixture
@skip_if_git_missing
def gitconfig(user_path: pathlib.Path, set_home: pathlib.Path) -> pathlib.Path:
    gitconfig = user_path / ".gitconfig"
    user_email = "libvcs@git-pull.com"
    gitconfig.write_text(
        textwrap.dedent(
            f"""
  [user]
    email = {user_email}
    name = {getpass.getuser()}
  [color]
    diff = auto
    """
        ),
        encoding="utf-8",
    )

    output = run(["git", "config", "--get", "user.email"])
    used_config_file_output = run(
        [
            "git",
            "config",
            "--show-origin",
            "--get",
            "user.email",
        ]
    )
    assert str(gitconfig) in used_config_file_output
    assert user_email in output, "Should use our fixture config and home directory"

    return gitconfig


@pytest.fixture
@skip_if_hg_missing
def hgconfig(user_path: pathlib.Path, set_home: pathlib.Path) -> pathlib.Path:
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
def projects_path(
    user_path: pathlib.Path, request: pytest.FixtureRequest
) -> pathlib.Path:
    """User's local checkouts and clones. Emphemeral directory."""
    dir = user_path / "projects"
    dir.mkdir(exist_ok=True)

    def clean() -> None:
        shutil.rmtree(dir)

    request.addfinalizer(clean)
    return dir


@pytest.fixture(scope="function")
def remote_repos_path(
    user_path: pathlib.Path, request: pytest.FixtureRequest
) -> pathlib.Path:
    """System's remote (file-based) repos to clone andpush to. Emphemeral directory."""
    dir = user_path / "remote_repos"
    dir.mkdir(exist_ok=True)

    def clean() -> None:
        shutil.rmtree(dir)

    request.addfinalizer(clean)
    return dir


def unique_repo_name(remote_repos_path: pathlib.Path, max_retries: int = 15) -> str:
    attempts = 1
    while True:
        if attempts > max_retries:
            raise Exception(
                f"Could not find unused repo destination (attempts: {attempts})"
            )
        remote_repo_name: str = next(namer)
        suggestion = remote_repos_path / remote_repo_name
        if suggestion.exists():
            attempts += 1
            continue
        return remote_repo_name


InitCmdArgs: "TypeAlias" = Optional[list[str]]


class CreateProjectCallbackProtocol(Protocol):
    def __call__(self, remote_repo_path: pathlib.Path) -> None:
        ...


class CreateProjectCallbackFixtureProtocol(Protocol):
    def __call__(
        self,
        remote_repos_path: pathlib.Path = ...,
        remote_repo_name: Optional[str] = ...,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = ...,
        init_cmd_args: InitCmdArgs = ...,
    ) -> pathlib.Path:
        ...


def _create_git_remote_repo(
    remote_repos_path: pathlib.Path,
    remote_repo_name: str,
    remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    init_cmd_args: InitCmdArgs = ["--bare"],
) -> pathlib.Path:
    if init_cmd_args is None:
        init_cmd_args = []
    remote_repo_path = remote_repos_path / remote_repo_name
    run(["git", "init", remote_repo_name, *init_cmd_args], cwd=remote_repos_path)

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


@pytest.fixture
@skip_if_git_missing
def create_git_remote_repo(
    remote_repos_path: pathlib.Path,
) -> CreateProjectCallbackFixtureProtocol:
    """Factory. Create git remote repo to for clone / push purposes"""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
        init_cmd_args: InitCmdArgs = ["--bare"],
    ) -> pathlib.Path:
        return _create_git_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else unique_repo_name(remote_repos_path=remote_repos_path),
            remote_repo_post_init=remote_repo_post_init,
            init_cmd_args=init_cmd_args,
        )

    return fn


def git_remote_repo_single_commit_post_init(remote_repo_path: pathlib.Path) -> None:
    testfile_filename = "testfile.test"
    run(["touch", testfile_filename], cwd=remote_repo_path)
    run(["git", "add", testfile_filename], cwd=remote_repo_path)
    run(["git", "commit", "-m", "test file for dummyrepo"], cwd=remote_repo_path)


@pytest.fixture
@pytest.mark.usefixtures("gitconfig", "set_home")
@skip_if_git_missing
def git_remote_repo(remote_repos_path: pathlib.Path) -> pathlib.Path:
    """Pre-made git repo w/ 1 commit, used as a file:// remote to clone and push to."""
    return _create_git_remote_repo(
        remote_repos_path=remote_repos_path,
        remote_repo_name="dummyrepo",
        remote_repo_post_init=git_remote_repo_single_commit_post_init,
        init_cmd_args=None,  # Don't do --bare
    )


def _create_svn_remote_repo(
    remote_repos_path: pathlib.Path,
    remote_repo_name: str,
    remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
    init_cmd_args: InitCmdArgs = None,
) -> pathlib.Path:
    """Create a test SVN repo to for checkout / commit purposes"""
    if init_cmd_args is None:
        init_cmd_args = []

    remote_repo_path = remote_repos_path / remote_repo_name
    run(["svnadmin", "create", remote_repo_path, *init_cmd_args])

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


@pytest.fixture
@skip_if_svn_missing
def create_svn_remote_repo(
    remote_repos_path: pathlib.Path,
) -> CreateProjectCallbackFixtureProtocol:
    """Pre-made svn repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
        init_cmd_args: InitCmdArgs = None,
    ) -> pathlib.Path:
        return _create_svn_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else unique_repo_name(remote_repos_path=remote_repos_path),
            remote_repo_post_init=remote_repo_post_init,
            init_cmd_args=init_cmd_args,
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
    init_cmd_args: InitCmdArgs = None,
) -> pathlib.Path:
    """Create a test hg repo to for checkout / commit purposes"""
    if init_cmd_args is None:
        init_cmd_args = []

    remote_repo_path = remote_repos_path / remote_repo_name
    run(["hg", "init", remote_repo_name, *init_cmd_args], cwd=remote_repos_path)

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


def hg_remote_repo_single_commit_post_init(remote_repo_path: pathlib.Path) -> None:
    testfile_filename = "testfile.test"
    run(["touch", testfile_filename], cwd=remote_repo_path)
    run(["hg", "add", testfile_filename], cwd=remote_repo_path)
    run(["hg", "commit", "-m", "test file for hg repo"], cwd=remote_repo_path)


@pytest.fixture
@skip_if_hg_missing
def create_hg_remote_repo(
    remote_repos_path: pathlib.Path,
    hgconfig: pathlib.Path,
    set_home: pathlib.Path,
) -> CreateProjectCallbackFixtureProtocol:
    """Pre-made hg repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: Optional[str] = None,
        remote_repo_post_init: Optional[CreateProjectCallbackProtocol] = None,
        init_cmd_args: InitCmdArgs = None,
    ) -> pathlib.Path:
        return _create_hg_remote_repo(
            remote_repos_path=remote_repos_path,
            remote_repo_name=remote_repo_name
            if remote_repo_name is not None
            else unique_repo_name(remote_repos_path=remote_repos_path),
            remote_repo_post_init=remote_repo_post_init,
            init_cmd_args=init_cmd_args,
        )

    return fn


@pytest.fixture
@skip_if_hg_missing
def hg_remote_repo(
    remote_repos_path: pathlib.Path, hgconfig: pathlib.Path
) -> pathlib.Path:
    """Pre-made, file-based repo for push and pull."""
    return _create_hg_remote_repo(
        remote_repos_path=remote_repos_path,
        remote_repo_name="dummyrepo",
        remote_repo_post_init=hg_remote_repo_single_commit_post_init,
    )


@pytest.fixture
def git_repo(projects_path: pathlib.Path, git_remote_repo: pathlib.Path) -> GitSync:
    """Pre-made git clone of remote repo checked out to user's projects dir."""
    git_repo = GitSync(
        url=f"file://{git_remote_repo}",
        dir=str(projects_path / "git_repo"),
        remotes={
            "origin": GitRemote(
                name="origin",
                push_url=f"file://{git_remote_repo}",
                fetch_url=f"file://{git_remote_repo}",
            )
        },
    )
    git_repo.obtain()
    return git_repo


@pytest.fixture
def hg_repo(projects_path: pathlib.Path, hg_remote_repo: pathlib.Path) -> HgSync:
    """Pre-made hg clone of remote repo checked out to user's projects dir."""
    hg_repo = HgSync(
        url=f"file://{hg_remote_repo}",
        dir=str(projects_path / "hg_repo"),
    )
    hg_repo.obtain()
    return hg_repo


@pytest.fixture
def svn_repo(projects_path: pathlib.Path, svn_remote_repo: pathlib.Path) -> SvnSync:
    """Pre-made svn clone of remote repo checked out to user's projects dir."""
    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo}",
        dir=str(projects_path / "svn_repo"),
    )
    svn_repo.obtain()
    return svn_repo


@pytest.fixture
def add_doctest_fixtures(
    request: pytest.FixtureRequest,
    doctest_namespace: dict[str, Any],
    tmp_path: pathlib.Path,
    set_home: pathlib.Path,
    gitconfig: pathlib.Path,
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    create_svn_remote_repo: CreateProjectCallbackFixtureProtocol,
    create_hg_remote_repo: CreateProjectCallbackFixtureProtocol,
    git_repo: pathlib.Path,
) -> None:
    from _pytest.doctest import DoctestItem

    if not isinstance(request._pyfuncitem, DoctestItem):  # Only run on doctest items
        return
    doctest_namespace["tmp_path"] = tmp_path
    if shutil.which("git"):
        doctest_namespace["gitconfig"] = gitconfig
        doctest_namespace["create_git_remote_repo"] = functools.partial(
            create_git_remote_repo,
            remote_repo_post_init=git_remote_repo_single_commit_post_init,
            init_cmd_args=None,
        )
        doctest_namespace["create_git_remote_repo_bare"] = create_git_remote_repo
        doctest_namespace["git_local_clone"] = git_repo
    if shutil.which("svn"):
        doctest_namespace["create_svn_remote_repo"] = create_svn_remote_repo
    if shutil.which("hg"):
        doctest_namespace["create_hg_remote_repo_bare"] = create_hg_remote_repo
        doctest_namespace["create_hg_remote_repo"] = functools.partial(
            create_hg_remote_repo,
            remote_repo_post_init=hg_remote_repo_single_commit_post_init,
        )
