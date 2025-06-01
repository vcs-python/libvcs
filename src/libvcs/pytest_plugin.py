"""pytest plugin for VCS Repository testing and management."""

from __future__ import annotations

import functools
import getpass
import pathlib
import random
import shutil
import textwrap
import typing as t

import pytest

from libvcs import exc
from libvcs._internal.run import run
from libvcs.sync.git import GitRemote, GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync

if t.TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from libvcs._internal.run import _ENV


class MaxUniqueRepoAttemptsExceeded(exc.LibVCSException):
    """Raised when exceeded threshold of attempts to find a unique repo destination."""

    def __init__(self, attempts: int, *args: object) -> None:
        """Raise LibVCSException exception with message including attempts tried."""
        return super().__init__(
            f"Could not find unused repo destination (attempts: {attempts})",
        )


skip_if_git_missing = pytest.mark.skipif(
    not shutil.which("git"),
    reason="git is not available",
)
skip_if_svn_missing = pytest.mark.skipif(
    not shutil.which("svn"),
    reason="svn is not available",
)
skip_if_hg_missing = pytest.mark.skipif(
    not shutil.which("hg"),
    reason="hg is not available",
)


DEFAULT_VCS_NAME = "Test user"
DEFAULT_VCS_EMAIL = "test@example.com"


@pytest.fixture(scope="session")
def vcs_name() -> str:
    """Return default VCS name."""
    return DEFAULT_VCS_NAME


@pytest.fixture(scope="session")
def vcs_email() -> str:
    """Return default VCS email."""
    return DEFAULT_VCS_EMAIL


@pytest.fixture(scope="session")
def vcs_user(vcs_name: str, vcs_email: str) -> str:
    """Return default VCS user."""
    return f"{vcs_name} <{vcs_email}>"


@pytest.fixture(scope="session")
def git_commit_envvars(vcs_name: str, vcs_email: str) -> _ENV:
    """Return environment variables for `git commit`.

    For some reason, `GIT_CONFIG` via {func}`set_gitconfig` doesn't work for `git
    commit`.
    """
    return {
        "GIT_AUTHOR_NAME": vcs_name,
        "GIT_AUTHOR_EMAIL": vcs_email,
        "GIT_COMMITTER_NAME": vcs_name,
        "GIT_COMMITTER_EMAIL": vcs_email,
    }


class RandomStrSequence:
    """Create a random string sequence."""

    def __init__(
        self,
        characters: str = "abcdefghijklmnopqrstuvwxyz0123456789_",
    ) -> None:
        self.characters: str = characters

    def __iter__(self) -> RandomStrSequence:
        """Iterate across generated strings."""
        return self

    def __next__(self) -> str:
        """Iterate to next string possibility."""
        return "".join(random.sample(self.characters, k=8))


namer = RandomStrSequence()


def pytest_ignore_collect(collection_path: pathlib.Path, config: pytest.Config) -> bool:
    """Skip tests if VCS binaries are missing."""
    if not shutil.which("svn") and any(
        needle in str(collection_path) for needle in ["svn", "subversion"]
    ):
        return True
    if not shutil.which("git") and "git" in str(collection_path):
        return True
    return bool(
        not shutil.which("hg")
        and any(needle in str(collection_path) for needle in ["hg", "mercurial"]),
    )


@pytest.fixture(scope="session")
def home_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Return temporary directory to use as user's home path, pytest fixture."""
    return tmp_path_factory.mktemp("home")


@pytest.fixture(scope="session")
def home_user_name() -> str:
    """Return default username to set for :func:`user_path` fixture."""
    return getpass.getuser()


@pytest.fixture(scope="session")
def user_path(home_path: pathlib.Path, home_user_name: str) -> pathlib.Path:
    """Return user's home directory, pytest fixture."""
    p = home_path / home_user_name
    p.mkdir()
    return p


@pytest.fixture
def set_home(
    monkeypatch: pytest.MonkeyPatch,
    user_path: pathlib.Path,
) -> None:
    """Set home directory, pytest fixture."""
    monkeypatch.setenv("HOME", str(user_path))


@pytest.fixture(scope="session")
@skip_if_git_missing
def gitconfig(
    user_path: pathlib.Path,
    vcs_email: str,
    vcs_name: str,
) -> pathlib.Path:
    """Return git configuration, pytest fixture."""
    gitconfig = user_path / ".gitconfig"

    if gitconfig.exists():
        return gitconfig

    gitconfig.write_text(
        textwrap.dedent(
            f"""
  [user]
    email = {vcs_email}
    name = {vcs_name}
  [color]
    diff = auto
    """,
        ),
        encoding="utf-8",
    )

    return gitconfig


@pytest.fixture
@skip_if_git_missing
def set_gitconfig(
    monkeypatch: pytest.MonkeyPatch,
    gitconfig: pathlib.Path,
) -> pathlib.Path:
    """Set git configuration."""
    monkeypatch.setenv("GIT_CONFIG", str(gitconfig))
    return gitconfig


@pytest.fixture(scope="session")
@skip_if_hg_missing
def hgconfig(
    user_path: pathlib.Path,
    vcs_user: str,
) -> pathlib.Path:
    """Return Mercurial configuration."""
    hgrc = user_path / ".hgrc"
    hgrc.write_text(
        textwrap.dedent(
            f"""
        [ui]
        username = {vcs_user}
        merge = internal:merge

        [trusted]
        users = {getpass.getuser()}
    """,
        ),
        encoding="utf-8",
    )
    return hgrc


@pytest.fixture
@skip_if_hg_missing
def set_hgconfig(
    monkeypatch: pytest.MonkeyPatch,
    hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Set Mercurial configuration."""
    monkeypatch.setenv("HGRCPATH", str(hgconfig))
    return hgconfig


@pytest.fixture
def projects_path(
    user_path: pathlib.Path,
    request: pytest.FixtureRequest,
) -> pathlib.Path:
    """User's local checkouts and clones. Emphemeral directory."""
    path = user_path / "projects"
    path.mkdir(exist_ok=True)

    def clean() -> None:
        shutil.rmtree(path)

    request.addfinalizer(clean)
    return path


@pytest.fixture(scope="session")
def remote_repos_path(
    user_path: pathlib.Path,
    request: pytest.FixtureRequest,
) -> pathlib.Path:
    """System's remote (file-based) repos to clone and push to. Emphemeral directory."""
    path = user_path / "remote_repos"
    path.mkdir(exist_ok=True)

    def clean() -> None:
        shutil.rmtree(path)

    request.addfinalizer(clean)
    return path


def unique_repo_name(remote_repos_path: pathlib.Path, max_retries: int = 15) -> str:
    """Attempt to find and return a unique repo named based on path."""
    attempts = 1
    while True:
        if attempts > max_retries:
            raise MaxUniqueRepoAttemptsExceeded(attempts=attempts)
        remote_repo_name: str = next(namer)
        suggestion = remote_repos_path / remote_repo_name
        if suggestion.exists():
            attempts += 1
            continue
        return remote_repo_name


InitCmdArgs: TypeAlias = t.Optional[list[str]]


class CreateRepoPostInitFn(t.Protocol):
    """Typing for VCS repo creation callback."""

    def __call__(
        self,
        remote_repo_path: pathlib.Path,
        env: _ENV | None = None,
    ) -> None:
        """Ran after creating a repo from pytest fixture."""
        ...


class CreateRepoPytestFixtureFn(t.Protocol):
    """Typing for VCS pytest fixture callback."""

    def __call__(
        self,
        remote_repos_path: pathlib.Path = ...,
        remote_repo_name: str | None = ...,
        remote_repo_post_init: CreateRepoPostInitFn | None = ...,
        init_cmd_args: InitCmdArgs = ...,
    ) -> pathlib.Path:
        """py.test fixture function to create a project in a remote repo."""
        ...


DEFAULT_GIT_REMOTE_REPO_CMD_ARGS = ["--bare"]


def _create_git_remote_repo(
    remote_repo_path: pathlib.Path,
    remote_repo_post_init: CreateRepoPostInitFn | None = None,
    init_cmd_args: InitCmdArgs = DEFAULT_GIT_REMOTE_REPO_CMD_ARGS,
    env: _ENV | None = None,
) -> pathlib.Path:
    if init_cmd_args is None:
        init_cmd_args = []
    run(
        ["git", "init", remote_repo_path.stem, *init_cmd_args],
        cwd=remote_repo_path.parent,
    )

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path, env=env)

    return remote_repo_path


@pytest.fixture(scope="session")
def libvcs_test_cache_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Return temporary directory to use as cache path for libvcs tests."""
    return tmp_path_factory.mktemp("libvcs-test-cache")


@pytest.fixture(scope="session")
def empty_git_repo_path(libvcs_test_cache_path: pathlib.Path) -> pathlib.Path:
    """Return temporary directory to use for master-copy of a git repo."""
    return libvcs_test_cache_path / "empty_git_repo"


@pytest.fixture(scope="session")
def empty_git_bare_repo_path(libvcs_test_cache_path: pathlib.Path) -> pathlib.Path:
    """Return temporary directory to use for master-copy of a bare git repo."""
    return libvcs_test_cache_path / "empty_git_bare_repo"


@pytest.fixture(scope="session")
@skip_if_git_missing
def empty_git_bare_repo(
    empty_git_bare_repo_path: pathlib.Path,
) -> pathlib.Path:
    """Return factory to create git remote repo to for clone / push purposes."""
    if (
        empty_git_bare_repo_path.exists()
        and (empty_git_bare_repo_path / ".git").exists()
    ):
        return empty_git_bare_repo_path

    return _create_git_remote_repo(
        remote_repo_path=empty_git_bare_repo_path,
        remote_repo_post_init=None,
        init_cmd_args=DEFAULT_GIT_REMOTE_REPO_CMD_ARGS,  # --bare
    )


@pytest.fixture(scope="session")
@skip_if_git_missing
def empty_git_repo(
    empty_git_repo_path: pathlib.Path,
) -> pathlib.Path:
    """Return factory to create git remote repo to for clone / push purposes."""
    if empty_git_repo_path.exists() and (empty_git_repo_path / ".git").exists():
        return empty_git_repo_path

    return _create_git_remote_repo(
        remote_repo_path=empty_git_repo_path,
        remote_repo_post_init=None,
        init_cmd_args=None,
    )


@pytest.fixture(scope="session")
@skip_if_git_missing
def create_git_remote_bare_repo(
    remote_repos_path: pathlib.Path,
    empty_git_bare_repo: pathlib.Path,
) -> CreateRepoPytestFixtureFn:
    """Return factory to create git remote repo to for clone / push purposes."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: str | None = None,
        remote_repo_post_init: CreateRepoPostInitFn | None = None,
        init_cmd_args: InitCmdArgs = DEFAULT_GIT_REMOTE_REPO_CMD_ARGS,
    ) -> pathlib.Path:
        if remote_repo_name is None:
            remote_repo_name = unique_repo_name(remote_repos_path=remote_repos_path)
        remote_repo_path = remote_repos_path / remote_repo_name

        shutil.copytree(empty_git_bare_repo, remote_repo_path)

        assert empty_git_bare_repo.exists()

        assert remote_repo_path.exists()

        return remote_repo_path

    return fn


@pytest.fixture(scope="session")
@skip_if_git_missing
def create_git_remote_repo(
    remote_repos_path: pathlib.Path,
    empty_git_repo: pathlib.Path,
) -> CreateRepoPytestFixtureFn:
    """Return factory to create git remote repo to for clone / push purposes."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: str | None = None,
        remote_repo_post_init: CreateRepoPostInitFn | None = None,
        init_cmd_args: InitCmdArgs = DEFAULT_GIT_REMOTE_REPO_CMD_ARGS,
    ) -> pathlib.Path:
        if remote_repo_name is None:
            remote_repo_name = unique_repo_name(remote_repos_path=remote_repos_path)
        remote_repo_path = remote_repos_path / remote_repo_name

        shutil.copytree(empty_git_repo, remote_repo_path)

        if remote_repo_post_init is not None and callable(remote_repo_post_init):
            remote_repo_post_init(remote_repo_path=remote_repo_path)

        assert empty_git_repo.exists()
        assert (empty_git_repo / ".git").exists()

        assert remote_repo_path.exists()
        assert (remote_repo_path / ".git").exists()

        return remote_repo_path

    return fn


def git_remote_repo_single_commit_post_init(
    remote_repo_path: pathlib.Path,
    env: _ENV | None = None,
) -> None:
    """Post-initialization: Create a test git repo with a single commit."""
    testfile_filename = "testfile.test"
    run(
        ["touch", testfile_filename],
        cwd=remote_repo_path,
        env=env,
    )
    run(["git", "add", testfile_filename], cwd=remote_repo_path, env=env)
    run(
        ["git", "commit", "-m", "test file for dummyrepo"],
        cwd=remote_repo_path,
        env=env,
    )


@pytest.fixture(scope="session")
@skip_if_git_missing
def git_remote_repo(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    gitconfig: pathlib.Path,
    git_commit_envvars: _ENV,
) -> pathlib.Path:
    """Copy the session-scoped Git repository to a temporary directory."""
    # TODO: Cache the effect of of this in a session-based repo
    repo_path = create_git_remote_repo()
    git_remote_repo_single_commit_post_init(
        remote_repo_path=repo_path,
        env=git_commit_envvars,
    )
    return repo_path


def _create_svn_remote_repo(
    remote_repo_path: pathlib.Path,
    remote_repo_post_init: CreateRepoPostInitFn | None = None,
    init_cmd_args: InitCmdArgs = None,
) -> pathlib.Path:
    """Create a test SVN repo to for checkout / commit purposes."""
    if init_cmd_args is None:
        init_cmd_args = []

    run(["svnadmin", "create", str(remote_repo_path), *init_cmd_args])

    assert remote_repo_path.exists()
    assert remote_repo_path.is_dir()

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


def svn_remote_repo_single_commit_post_init(
    remote_repo_path: pathlib.Path,
    env: _ENV | None = None,
) -> None:
    """Post-initialization: Create a test SVN repo with a single commit."""
    assert remote_repo_path.exists()
    repo_dumpfile = pathlib.Path(__file__).parent / "data" / "repotest.dump"
    run(
        " ".join(
            [
                "svnadmin",
                "load",
                str(remote_repo_path),
                "<",
                str(repo_dumpfile),
            ],
        ),
        shell=True,
    )


@pytest.fixture(scope="session")
def empty_svn_repo_path(libvcs_test_cache_path: pathlib.Path) -> pathlib.Path:
    """Return temporary directory to use for master-copy of a svn repo."""
    return libvcs_test_cache_path / "empty_svn_repo"


@pytest.fixture(scope="session")
@skip_if_svn_missing
def empty_svn_repo(
    empty_svn_repo_path: pathlib.Path,
) -> pathlib.Path:
    """Return factory to create svn remote repo to for clone / push purposes."""
    if not shutil.which("svn") or not shutil.which("svnadmin"):
        pytest.skip(
            reason="svn is not available",
        )

    if empty_svn_repo_path.exists() and (empty_svn_repo_path / "conf").exists():
        return empty_svn_repo_path

    return _create_svn_remote_repo(
        remote_repo_path=empty_svn_repo_path,
        remote_repo_post_init=None,
        init_cmd_args=None,
    )


@pytest.fixture(scope="session")
@skip_if_svn_missing
def create_svn_remote_repo(
    remote_repos_path: pathlib.Path,
    empty_svn_repo: pathlib.Path,
) -> CreateRepoPytestFixtureFn:
    """Pre-made svn repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: str | None = None,
        remote_repo_post_init: CreateRepoPostInitFn | None = None,
        init_cmd_args: InitCmdArgs = None,
    ) -> pathlib.Path:
        if remote_repo_name is None:
            remote_repo_name = unique_repo_name(remote_repos_path=remote_repos_path)
        remote_repo_path = remote_repos_path / remote_repo_name

        shutil.copytree(empty_svn_repo, remote_repo_path)

        if remote_repo_post_init is not None and callable(remote_repo_post_init):
            remote_repo_post_init(remote_repo_path=remote_repo_path)

        assert empty_svn_repo.exists()

        assert remote_repo_path.exists()

        return remote_repo_path

    return fn


@pytest.fixture(scope="session")
@skip_if_svn_missing
def svn_remote_repo(
    create_svn_remote_repo: CreateRepoPytestFixtureFn,
) -> pathlib.Path:
    """Pre-made. Local file:// based SVN server."""
    return create_svn_remote_repo()


@pytest.fixture(scope="session")
@skip_if_svn_missing
def svn_remote_repo_with_files(
    create_svn_remote_repo: CreateRepoPytestFixtureFn,
) -> pathlib.Path:
    """Pre-made. Local file:// based SVN server."""
    repo_path = create_svn_remote_repo()
    svn_remote_repo_single_commit_post_init(remote_repo_path=repo_path)
    return repo_path


def _create_hg_remote_repo(
    remote_repo_path: pathlib.Path,
    remote_repo_post_init: CreateRepoPostInitFn | None = None,
    init_cmd_args: InitCmdArgs = None,
) -> pathlib.Path:
    """Create a test hg repo to for checkout / commit purposes."""
    if init_cmd_args is None:
        init_cmd_args = []

    run(
        ["hg", "init", remote_repo_path.stem, *init_cmd_args],
        cwd=remote_repo_path.parent,
    )

    if remote_repo_post_init is not None and callable(remote_repo_post_init):
        remote_repo_post_init(remote_repo_path=remote_repo_path)

    return remote_repo_path


def hg_remote_repo_single_commit_post_init(
    remote_repo_path: pathlib.Path,
    env: _ENV | None = None,
) -> None:
    """Post-initialization: Create a test mercurial repo with a single commit."""
    testfile_filename = "testfile.test"
    run(["touch", testfile_filename], cwd=remote_repo_path, env=env)
    run(["hg", "add", testfile_filename], cwd=remote_repo_path, env=env)
    run(["hg", "commit", "-m", "test file for hg repo"], cwd=remote_repo_path, env=env)


@pytest.fixture(scope="session")
def empty_hg_repo_path(libvcs_test_cache_path: pathlib.Path) -> pathlib.Path:
    """Return temporary directory to use for master-copy of a hg repo."""
    return libvcs_test_cache_path / "empty_hg_repo"


@pytest.fixture(scope="session")
@skip_if_hg_missing
def empty_hg_repo(
    empty_hg_repo_path: pathlib.Path,
) -> pathlib.Path:
    """Return factory to create hg remote repo to for clone / push purposes."""
    if empty_hg_repo_path.exists() and (empty_hg_repo_path / ".hg").exists():
        return empty_hg_repo_path

    return _create_hg_remote_repo(
        remote_repo_path=empty_hg_repo_path,
        remote_repo_post_init=None,
        init_cmd_args=None,
    )


@pytest.fixture(scope="session")
@skip_if_hg_missing
def create_hg_remote_repo(
    remote_repos_path: pathlib.Path,
    empty_hg_repo: pathlib.Path,
    hgconfig: pathlib.Path,
) -> CreateRepoPytestFixtureFn:
    """Pre-made hg repo, bare, used as a file:// remote to checkout and commit to."""

    def fn(
        remote_repos_path: pathlib.Path = remote_repos_path,
        remote_repo_name: str | None = None,
        remote_repo_post_init: CreateRepoPostInitFn | None = None,
        init_cmd_args: InitCmdArgs = None,
    ) -> pathlib.Path:
        if remote_repo_name is None:
            remote_repo_name = unique_repo_name(remote_repos_path=remote_repos_path)
        remote_repo_path = remote_repos_path / remote_repo_name

        shutil.copytree(empty_hg_repo, remote_repo_path)

        if remote_repo_post_init is not None and callable(remote_repo_post_init):
            remote_repo_post_init(
                remote_repo_path=remote_repo_path,
                env={"HGRCPATH": str(hgconfig)},
            )

        assert empty_hg_repo.exists()

        assert remote_repo_path.exists()

        return remote_repo_path

    return fn


@pytest.fixture(scope="session")
@skip_if_hg_missing
def hg_remote_repo(
    remote_repos_path: pathlib.Path,
    create_hg_remote_repo: CreateRepoPytestFixtureFn,
    hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Pre-made, file-based repo for push and pull."""
    repo_path = create_hg_remote_repo()
    hg_remote_repo_single_commit_post_init(
        remote_repo_path=repo_path,
        env={"HGRCPATH": str(hgconfig)},
    )
    return repo_path


@pytest.fixture
def git_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    set_gitconfig: pathlib.Path,
) -> GitSync:
    """Pre-made git clone of remote repo checked out to user's projects dir."""
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    master_copy = remote_repos_path / "git_repo"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        return GitSync(
            url=f"file://{git_remote_repo}",
            path=str(new_checkout_path),
        )

    git_repo = GitSync(
        url=f"file://{git_remote_repo}",
        path=master_copy,
        remotes={
            "origin": GitRemote(
                name="origin",
                push_url=f"file://{git_remote_repo}",
                fetch_url=f"file://{git_remote_repo}",
            ),
        },
    )
    git_repo.obtain()
    return git_repo


@pytest.fixture
def hg_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
    set_hgconfig: pathlib.Path,
) -> HgSync:
    """Pre-made hg clone of remote repo checked out to user's projects dir."""
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    master_copy = remote_repos_path / "hg_repo"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        return HgSync(
            url=f"file://{hg_remote_repo}",
            path=str(new_checkout_path),
        )

    hg_repo = HgSync(
        url=f"file://{hg_remote_repo}",
        path=master_copy,
    )
    hg_repo.obtain()
    return hg_repo


@pytest.fixture
def svn_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    svn_remote_repo: pathlib.Path,
) -> SvnSync:
    """Pre-made svn clone of remote repo checked out to user's projects dir."""
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    master_copy = remote_repos_path / "svn_repo"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        return SvnSync(
            url=f"file://{svn_remote_repo}",
            path=str(new_checkout_path),
        )

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo}",
        path=str(projects_path / "svn_repo"),
    )
    svn_repo.obtain()
    return svn_repo


@pytest.fixture
def add_doctest_fixtures(
    request: pytest.FixtureRequest,
    doctest_namespace: dict[str, t.Any],
    tmp_path: pathlib.Path,
    set_home: pathlib.Path,
    git_commit_envvars: _ENV,
    hgconfig: pathlib.Path,
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    create_svn_remote_repo: CreateRepoPytestFixtureFn,
    create_hg_remote_repo: CreateRepoPytestFixtureFn,
    git_repo: pathlib.Path,
) -> None:
    """Harness pytest fixtures to pytest's doctest namespace."""
    from _pytest.doctest import DoctestItem

    if not isinstance(request._pyfuncitem, DoctestItem):  # Only run on doctest items
        return
    doctest_namespace["tmp_path"] = tmp_path
    if shutil.which("git"):
        doctest_namespace["create_git_remote_repo"] = functools.partial(
            create_git_remote_repo,
            remote_repo_post_init=functools.partial(
                git_remote_repo_single_commit_post_init,
                env=git_commit_envvars,
            ),
            init_cmd_args=None,
        )
        doctest_namespace["create_git_remote_repo_bare"] = create_git_remote_repo
        doctest_namespace["example_git_repo"] = git_repo
    if shutil.which("svn"):
        doctest_namespace["create_svn_remote_repo_bare"] = create_svn_remote_repo
        doctest_namespace["create_svn_remote_repo"] = functools.partial(
            create_svn_remote_repo,
            remote_repo_post_init=svn_remote_repo_single_commit_post_init,
        )
    if shutil.which("hg"):
        doctest_namespace["create_hg_remote_repo_bare"] = create_hg_remote_repo
        doctest_namespace["create_hg_remote_repo"] = functools.partial(
            create_hg_remote_repo,
            remote_repo_post_init=functools.partial(
                hg_remote_repo_single_commit_post_init,
                env={"HGRCPATH": str(hgconfig)},
            ),
        )
