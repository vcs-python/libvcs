"""pytest plugin for VCS Repository testing and management."""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import getpass
import hashlib
import os
import pathlib
import random
import shutil
import subprocess
import textwrap
import time
import typing as t
from importlib.metadata import version as get_package_version

import pytest

from libvcs import exc
from libvcs._internal.run import _ENV, run
from libvcs.sync.git import GitRemote, GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync

# Async support - conditional import
try:
    import pytest_asyncio

    from libvcs.sync._async.git import AsyncGitSync
    from libvcs.sync._async.hg import AsyncHgSync
    from libvcs.sync._async.svn import AsyncSvnSync

    HAS_PYTEST_ASYNCIO = True
except ImportError:
    HAS_PYTEST_ASYNCIO = False


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


# =============================================================================
# Repo Fixture Result Dataclass
# =============================================================================

RepoT = t.TypeVar("RepoT")


@dataclasses.dataclass
class RepoFixtureResult(t.Generic[RepoT]):
    """Result from repo fixture with metadata.

    This dataclass wraps the repository instance with additional metadata
    about the fixture setup, including timing and cache information.

    Attributes
    ----------
    repo : RepoT
        The actual repository instance (GitSync, HgSync, SvnSync, or async variants)
    path : pathlib.Path
        Path to the repository working directory
    remote_url : str
        URL of the remote repository (file:// based)
    master_copy_path : pathlib.Path
        Path to the cached master copy
    created_at : float
        Time when the fixture was created (perf_counter)
    from_cache : bool
        True if the repo was copied from an existing master cache

    Examples
    --------
    >>> def test_git_operations(git_repo):
    ...     # Direct access to repo methods via __getattr__
    ...     revision = git_repo.get_revision()
    ...
    ...     # Access metadata
    ...     assert git_repo.from_cache  # True if using cached copy
    ...     print(f"Setup took: {time.perf_counter() - git_repo.created_at:.3f}s")
    ...
    ...     # Access the underlying repo directly
    ...     assert isinstance(git_repo.repo, GitSync)
    """

    repo: RepoT
    path: pathlib.Path
    remote_url: str
    master_copy_path: pathlib.Path
    created_at: float
    from_cache: bool

    def __getattr__(self, name: str) -> t.Any:
        """Delegate attribute access to the underlying repo for backwards compat."""
        return getattr(self.repo, name)


# =============================================================================
# XDG Persistent Cache Infrastructure
# =============================================================================


def get_xdg_cache_dir() -> pathlib.Path:
    """Get XDG cache directory for libvcs tests.

    Uses XDG_CACHE_HOME if set, otherwise defaults to ~/.cache.
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return pathlib.Path(xdg_cache) / "libvcs-test"
    return pathlib.Path.home() / ".cache" / "libvcs-test"


def get_vcs_version(cmd: list[str]) -> str:
    """Get version string from a VCS command, or 'not-installed' if unavailable."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "not-installed"


def get_cache_key() -> str:
    """Generate cache key from VCS versions and libvcs version.

    The cache is invalidated when any VCS tool or libvcs version changes.
    Results are cached to disk with a 24-hour TTL to avoid slow `hg --version`
    calls (which take ~100ms due to Python startup overhead).
    """
    base_dir = get_xdg_cache_dir()
    key_file = base_dir / ".cache_key"

    # Return cached key if exists and is recent (within 24 hours)
    if key_file.exists():
        try:
            stat = key_file.stat()
            if time.time() - stat.st_mtime < 86400:  # 24 hours
                return key_file.read_text().strip()
        except OSError:
            pass  # File was deleted or inaccessible, regenerate

    # Compute fresh key from VCS versions
    versions = [
        get_vcs_version(["git", "--version"]),
        get_vcs_version(["hg", "--version"]),  # ~100ms due to Python startup
        get_vcs_version(["svn", "--version"]),
        get_package_version("libvcs"),
    ]
    version_str = "|".join(versions)
    cache_key = hashlib.sha256(version_str.encode()).hexdigest()[:12]

    # Cache to disk for future runs
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        key_file.write_text(cache_key)
    except OSError:
        pass  # Cache write failed, continue without caching

    return cache_key


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add libvcs pytest options."""
    group = parser.getgroup("libvcs", "libvcs fixture options")
    group.addoption(
        "--libvcs-cache-dir",
        action="store",
        metavar="PATH",
        help="Override XDG cache directory for libvcs test fixtures",
    )
    group.addoption(
        "--libvcs-clear-cache",
        action="store_true",
        default=False,
        help="Clear libvcs persistent cache before running tests",
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


@pytest.fixture(scope="session")
def libvcs_persistent_cache(request: pytest.FixtureRequest) -> pathlib.Path:
    """Return persistent cache directory for libvcs test fixtures.

    This cache persists across test sessions and is keyed by VCS + libvcs versions.
    When any version changes, the cache is automatically invalidated.

    The cache location follows XDG Base Directory spec:
    - Default: ~/.cache/libvcs-test/<cache-key>/
    - Override: --libvcs-cache-dir=PATH

    Use --libvcs-clear-cache to force cache rebuild.
    """
    # Get cache directory (from option or XDG default)
    custom_cache = request.config.getoption("--libvcs-cache-dir")
    base_dir = pathlib.Path(custom_cache) if custom_cache else get_xdg_cache_dir()

    # Get version-based cache key
    cache_key = get_cache_key()
    cache_dir = base_dir / cache_key

    # Handle --libvcs-clear-cache
    if request.config.getoption("--libvcs-clear-cache") and base_dir.exists():
        shutil.rmtree(base_dir)

    # Clean old cache versions (different keys)
    if base_dir.exists():
        for old_cache in base_dir.iterdir():
            if old_cache.is_dir() and old_cache.name != cache_key:
                shutil.rmtree(old_cache)

    # Create cache directory
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir


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
    libvcs_persistent_cache: pathlib.Path,
) -> pathlib.Path:
    """Directory for remote repos and master copies, using persistent XDG cache.

    This ensures stable file:// URLs across test sessions, enabling proper
    caching of cloned repositories.
    """
    path = libvcs_persistent_cache / "remote_repos"
    path.mkdir(exist_ok=True)
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


InitCmdArgs: t.TypeAlias = list[str] | None


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
def libvcs_test_cache_path(
    libvcs_persistent_cache: pathlib.Path,
) -> pathlib.Path:
    """Return persistent cache directory for libvcs test fixtures.

    This now uses XDG persistent cache, which survives across test sessions
    and is automatically invalidated when VCS or libvcs versions change.
    """
    return libvcs_persistent_cache


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
    remote_repos_path: pathlib.Path,
    empty_git_repo: pathlib.Path,
    gitconfig: pathlib.Path,
    git_commit_envvars: _ENV,
) -> pathlib.Path:
    """Return cached Git remote repo with an initial commit.

    Uses persistent XDG cache - repo persists across test sessions.
    Uses a marker file to ensure the commit was successfully created.
    """
    repo_path = remote_repos_path / "git_remote_repo"
    marker = repo_path / ".libvcs_initialized"

    # Return cached repo if fully initialized (has marker file)
    if repo_path.exists() and marker.exists():
        return repo_path

    # Create from empty template
    if repo_path.exists():
        shutil.rmtree(repo_path)
    shutil.copytree(empty_git_repo, repo_path)

    # Add initial commit
    git_remote_repo_single_commit_post_init(
        remote_repo_path=repo_path,
        env=git_commit_envvars,
    )

    # Mark as fully initialized
    marker.touch()
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
    remote_repos_path: pathlib.Path,
    empty_svn_repo: pathlib.Path,
) -> pathlib.Path:
    """Return cached SVN remote repo.

    Uses persistent XDG cache - repo persists across test sessions.
    Uses a marker file to ensure initialization was successful.
    """
    repo_path = remote_repos_path / "svn_remote_repo"
    marker = repo_path / ".libvcs_initialized"

    # Return cached repo if fully initialized (has marker file)
    if repo_path.exists() and marker.exists():
        return repo_path

    # Create from empty template
    if repo_path.exists():
        shutil.rmtree(repo_path)
    shutil.copytree(empty_svn_repo, repo_path)

    # Mark as fully initialized
    marker.touch()
    return repo_path


@pytest.fixture(scope="session")
@skip_if_svn_missing
def svn_remote_repo_with_files(
    remote_repos_path: pathlib.Path,
    svn_remote_repo: pathlib.Path,
) -> pathlib.Path:
    """Return cached SVN remote repo with files committed.

    Uses persistent XDG cache - repo persists across test sessions.
    Uses a marker file to ensure the commit was successfully created.
    """
    repo_path = remote_repos_path / "svn_remote_repo_with_files"
    marker = repo_path / ".libvcs_initialized"

    # Return cached repo if fully initialized (has marker file)
    if repo_path.exists() and marker.exists():
        return repo_path

    # Create from base svn_remote_repo
    if repo_path.exists():
        shutil.rmtree(repo_path)
    shutil.copytree(svn_remote_repo, repo_path)

    svn_remote_repo_single_commit_post_init(remote_repo_path=repo_path)

    # Mark as fully initialized
    marker.touch()
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
    empty_hg_repo: pathlib.Path,
    hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Return cached Mercurial remote repo with an initial commit.

    Uses persistent XDG cache - repo persists across test sessions.
    Uses a marker file to ensure the commit was successfully created.
    """
    repo_path = remote_repos_path / "hg_remote_repo"
    marker = repo_path / ".libvcs_initialized"

    # Return cached repo if fully initialized (has marker file)
    if repo_path.exists() and marker.exists():
        return repo_path

    # Create from empty template
    if repo_path.exists():
        shutil.rmtree(repo_path)
    shutil.copytree(empty_hg_repo, repo_path)

    # Add initial commit (slow: ~288ms due to hg add + commit)
    hg_remote_repo_single_commit_post_init(
        remote_repo_path=repo_path,
        env={"HGRCPATH": str(hgconfig)},
    )

    # Mark as fully initialized
    marker.touch()
    return repo_path


@pytest.fixture
def git_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    set_gitconfig: pathlib.Path,
) -> RepoFixtureResult[GitSync]:
    """Pre-made git clone of remote repo checked out to user's projects dir.

    Returns a RepoFixtureResult containing the GitSync instance and metadata.
    The underlying GitSync methods are accessible directly via __getattr__.
    """
    created_at = time.perf_counter()
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    remote_url = f"file://{git_remote_repo}"
    # Unified master copy shared with async_git_repo
    master_copy = remote_repos_path / "git_repo_master"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        repo = GitSync(url=remote_url, path=str(new_checkout_path))
        return RepoFixtureResult(
            repo=repo,
            path=new_checkout_path,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=True,
        )

    repo = GitSync(
        url=remote_url,
        path=master_copy,
        remotes={
            "origin": GitRemote(
                name="origin",
                push_url=remote_url,
                fetch_url=remote_url,
            ),
        },
    )
    repo.obtain()
    return RepoFixtureResult(
        repo=repo,
        path=master_copy,
        remote_url=remote_url,
        master_copy_path=master_copy,
        created_at=created_at,
        from_cache=False,
    )


@pytest.fixture
def hg_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
    set_hgconfig: pathlib.Path,
) -> RepoFixtureResult[HgSync]:
    """Pre-made hg clone of remote repo checked out to user's projects dir.

    Returns a RepoFixtureResult containing the HgSync instance and metadata.
    """
    created_at = time.perf_counter()
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    remote_url = f"file://{hg_remote_repo}"
    # Unified master copy shared with async_hg_repo
    master_copy = remote_repos_path / "hg_repo_master"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        repo = HgSync(url=remote_url, path=str(new_checkout_path))
        return RepoFixtureResult(
            repo=repo,
            path=new_checkout_path,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=True,
        )

    repo = HgSync(url=remote_url, path=master_copy)
    repo.obtain()
    return RepoFixtureResult(
        repo=repo,
        path=master_copy,
        remote_url=remote_url,
        master_copy_path=master_copy,
        created_at=created_at,
        from_cache=False,
    )


@pytest.fixture
def svn_repo(
    remote_repos_path: pathlib.Path,
    projects_path: pathlib.Path,
    svn_remote_repo: pathlib.Path,
) -> RepoFixtureResult[SvnSync]:
    """Pre-made svn checkout of remote repo checked out to user's projects dir.

    Returns a RepoFixtureResult containing the SvnSync instance and metadata.
    """
    created_at = time.perf_counter()
    remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
    new_checkout_path = projects_path / remote_repo_name
    remote_url = f"file://{svn_remote_repo}"
    # Unified master copy shared with async_svn_repo
    master_copy = remote_repos_path / "svn_repo_master"

    if master_copy.exists():
        shutil.copytree(master_copy, new_checkout_path)
        repo = SvnSync(url=remote_url, path=str(new_checkout_path))
        return RepoFixtureResult(
            repo=repo,
            path=new_checkout_path,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=True,
        )

    repo = SvnSync(url=remote_url, path=str(master_copy))
    repo.obtain()
    return RepoFixtureResult(
        repo=repo,
        path=master_copy,
        remote_url=remote_url,
        master_copy_path=master_copy,
        created_at=created_at,
        from_cache=False,
    )


# =============================================================================
# Async Fixtures
# =============================================================================

if HAS_PYTEST_ASYNCIO:

    @pytest_asyncio.fixture
    @skip_if_git_missing
    async def async_git_repo(
        remote_repos_path: pathlib.Path,
        projects_path: pathlib.Path,
        git_remote_repo: pathlib.Path,
        set_gitconfig: pathlib.Path,
    ) -> t.AsyncGenerator[RepoFixtureResult[AsyncGitSync], None]:
        """Pre-made async git clone of remote repo checked out to user's projects dir.

        Async equivalent of :func:`git_repo` fixture.
        Returns a RepoFixtureResult containing the AsyncGitSync instance and metadata.

        Examples
        --------
        >>> @pytest.mark.asyncio
        ... async def test_git_operations(async_git_repo):
        ...     revision = await async_git_repo.get_revision()
        ...     assert async_git_repo.from_cache  # True if using cached copy
        """
        created_at = time.perf_counter()
        remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
        new_checkout_path = projects_path / remote_repo_name
        remote_url = f"file://{git_remote_repo}"
        # Unified master copy shared with git_repo
        master_copy = remote_repos_path / "git_repo_master"

        if master_copy.exists():
            shutil.copytree(master_copy, new_checkout_path)
            repo = AsyncGitSync(url=remote_url, path=new_checkout_path)
            yield RepoFixtureResult(
                repo=repo,
                path=new_checkout_path,
                remote_url=remote_url,
                master_copy_path=master_copy,
                created_at=created_at,
                from_cache=True,
            )
            return

        repo = AsyncGitSync(
            url=remote_url,
            path=master_copy,
            remotes={
                "origin": GitRemote(
                    name="origin",
                    push_url=remote_url,
                    fetch_url=remote_url,
                ),
            },
        )
        await repo.obtain()
        yield RepoFixtureResult(
            repo=repo,
            path=master_copy,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=False,
        )

    @pytest_asyncio.fixture
    @skip_if_hg_missing
    async def async_hg_repo(
        remote_repos_path: pathlib.Path,
        projects_path: pathlib.Path,
        hg_remote_repo: pathlib.Path,
        set_hgconfig: pathlib.Path,
    ) -> t.AsyncGenerator[RepoFixtureResult[AsyncHgSync], None]:
        """Pre-made async hg clone of remote repo checked out to user's projects dir.

        Async equivalent of :func:`hg_repo` fixture.
        Returns a RepoFixtureResult containing the AsyncHgSync instance and metadata.

        Examples
        --------
        >>> @pytest.mark.asyncio
        ... async def test_hg_operations(async_hg_repo):
        ...     revision = await async_hg_repo.get_revision()
        ...     assert async_hg_repo.from_cache  # True if using cached copy
        """
        created_at = time.perf_counter()
        remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
        new_checkout_path = projects_path / remote_repo_name
        remote_url = f"file://{hg_remote_repo}"
        # Unified master copy shared with hg_repo
        master_copy = remote_repos_path / "hg_repo_master"

        if master_copy.exists():
            shutil.copytree(master_copy, new_checkout_path)
            repo = AsyncHgSync(url=remote_url, path=new_checkout_path)
            yield RepoFixtureResult(
                repo=repo,
                path=new_checkout_path,
                remote_url=remote_url,
                master_copy_path=master_copy,
                created_at=created_at,
                from_cache=True,
            )
            return

        repo = AsyncHgSync(url=remote_url, path=master_copy)
        await repo.obtain()
        yield RepoFixtureResult(
            repo=repo,
            path=master_copy,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=False,
        )

    @pytest_asyncio.fixture
    @skip_if_svn_missing
    async def async_svn_repo(
        remote_repos_path: pathlib.Path,
        projects_path: pathlib.Path,
        svn_remote_repo: pathlib.Path,
    ) -> t.AsyncGenerator[RepoFixtureResult[AsyncSvnSync], None]:
        """Pre-made async svn checkout of remote repo.

        Checked out to user's projects dir.
        Async equivalent of :func:`svn_repo` fixture.
        Returns a RepoFixtureResult containing the AsyncSvnSync instance and metadata.

        Examples
        --------
        >>> @pytest.mark.asyncio
        ... async def test_svn_operations(async_svn_repo):
        ...     revision = await async_svn_repo.get_revision()
        ...     assert async_svn_repo.from_cache  # True if using cached copy
        """
        created_at = time.perf_counter()
        remote_repo_name = unique_repo_name(remote_repos_path=projects_path)
        new_checkout_path = projects_path / remote_repo_name
        remote_url = f"file://{svn_remote_repo}"
        # Unified master copy shared with svn_repo
        master_copy = remote_repos_path / "svn_repo_master"

        if master_copy.exists():
            shutil.copytree(master_copy, new_checkout_path)
            repo = AsyncSvnSync(url=remote_url, path=new_checkout_path)
            yield RepoFixtureResult(
                repo=repo,
                path=new_checkout_path,
                remote_url=remote_url,
                master_copy_path=master_copy,
                created_at=created_at,
                from_cache=True,
            )
            return

        repo = AsyncSvnSync(url=remote_url, path=master_copy)
        await repo.obtain()
        yield RepoFixtureResult(
            repo=repo,
            path=master_copy,
            remote_url=remote_url,
            master_copy_path=master_copy,
            created_at=created_at,
            from_cache=False,
        )


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
    # Add asyncio for async doctests
    doctest_namespace["asyncio"] = asyncio
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
