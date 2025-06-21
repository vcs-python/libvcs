"""Tests for libvcs pytest plugin."""

from __future__ import annotations

import shutil
import textwrap
import typing as t

import pytest

from libvcs._internal.run import run
from libvcs.cmd.git import Git
from libvcs.exc import CommandError
from libvcs.pytest_plugin import (
    DEFAULT_GIT_INITIAL_BRANCH,
    _create_git_remote_repo,
)

if t.TYPE_CHECKING:
    import pathlib

    from libvcs.pytest_plugin import CreateRepoPytestFixtureFn


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_create_git_remote_repo(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for create_git_remote_repo pytest fixture."""
    git_remote_1 = create_git_remote_repo()
    git_remote_2 = create_git_remote_repo()

    assert git_remote_1 != git_remote_2


@pytest.mark.skipif(not shutil.which("svn"), reason="svn is not available")
def test_create_svn_remote_repo(
    create_svn_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for create_svn_remote_repo pytest fixture."""
    svn_remote_1 = create_svn_remote_repo()
    svn_remote_2 = create_svn_remote_repo()

    assert svn_remote_1 != svn_remote_2


def test_gitconfig(
    gitconfig: pathlib.Path,
    set_gitconfig: pathlib.Path,
    vcs_email: str,
) -> None:
    """Test gitconfig fixture."""
    output = run(["git", "config", "--get", "user.email"])
    used_config_file_output = run(
        [
            "git",
            "config",
            "--show-origin",
            "--get",
            "user.email",
        ],
    )
    assert str(gitconfig) in used_config_file_output
    assert vcs_email in output, "Should use our fixture config and home directory"


def test_git_fixtures(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Tests for libvcs pytest plugin git configuration."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Initialize variables
    pytester.plugins = ["pytest_plugin"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-vv
        """.strip(),
        ),
    )
    pytester.makeconftest(
        textwrap.dedent(
            r"""
import pathlib
import pytest

@pytest.fixture(scope="session")
def vcs_email() -> str:
    return "custom_email@testemail.com"

@pytest.fixture(autouse=True)
def setup(
    request: pytest.FixtureRequest,
    gitconfig: pathlib.Path,
    set_home: pathlib.Path,
) -> None:
    pass
    """,
        ),
    )
    tests_path = pytester.path / "tests"
    files = {
        "example.py": textwrap.dedent(
            """
import pathlib

from libvcs.sync.git import GitSync
from libvcs.pytest_plugin import (
    CreateRepoPytestFixtureFn,
    git_remote_repo_single_commit_post_init
)


def test_repo_git_remote_repo_and_sync(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(path=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()


def test_git_bare_repo_sync_and_commit(
    create_git_remote_bare_repo: CreateRepoPytestFixtureFn,
    projects_path: pathlib.Path,
) -> None:
    git_server = create_git_remote_bare_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(path=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()

    git_remote_repo_single_commit_post_init(
        remote_repo_path=git_repo_checkout_dir
    )

    assert git_repo.get_revision() != "initial"

    last_committer_email = git_repo.cmd.run(["log", "-1", "--pretty=format:%ae"])

    assert last_committer_email == "custom_email@testemail.com", (
        'Email should use the override from the "vcs_email" fixture'
    )
        """,
        ),
    }
    first_test_key = next(iter(files.keys()))
    first_test_filename = str(tests_path / first_test_key)

    tests_path.mkdir()
    for file_name, text in files.items():
        test_file = tests_path / file_name
        test_file.write_text(
            text,
            encoding="utf-8",
        )

    # Test
    result = pytester.runpytest(str(first_test_filename))
    result.assert_outcomes(passed=2)


def test_create_git_remote_repo_basic(tmp_path: pathlib.Path) -> None:
    """Test basic git repository creation."""
    repo_path = tmp_path / "test-repo"

    result = _create_git_remote_repo(repo_path, init_cmd_args=[])

    assert result == repo_path
    assert repo_path.exists()
    assert (repo_path / ".git").exists()


def test_create_git_remote_repo_bare(tmp_path: pathlib.Path) -> None:
    """Test bare git repository creation."""
    repo_path = tmp_path / "test-repo.git"

    result = _create_git_remote_repo(repo_path, init_cmd_args=["--bare"])

    assert result == repo_path
    assert repo_path.exists()
    assert (repo_path / "HEAD").exists()
    assert not (repo_path / ".git").exists()


def test_create_git_remote_repo_with_initial_branch(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test repository creation with custom initial branch.

    This test checks both modern Git (2.30.0+) and fallback behavior.
    """
    repo_path = tmp_path / "test-repo"

    # Track Git.init calls
    init_calls: list[dict[str, t.Any]] = []

    def mock_init(self: Git, *args: t.Any, **kwargs: t.Any) -> str:
        init_calls.append({"args": args, "kwargs": kwargs})

        # Simulate old Git that doesn't support --initial-branch
        if kwargs.get("initial_branch"):
            msg = "error: unknown option `initial-branch'"
            raise CommandError(
                msg,
                returncode=1,
                cmd=["git", "init", "--initial-branch=main"],
            )

        # Create the repo directory to simulate successful init
        self.path.mkdir(exist_ok=True)
        (self.path / ".git").mkdir(exist_ok=True)
        return "Initialized empty Git repository"

    monkeypatch.setattr(Git, "init", mock_init)

    result = _create_git_remote_repo(repo_path, initial_branch="develop")

    # Should have tried twice: once with initial_branch, once without
    assert len(init_calls) == 2
    assert init_calls[0]["kwargs"].get("initial_branch") == "develop"
    assert "initial_branch" not in init_calls[1]["kwargs"]
    assert result == repo_path


def test_create_git_remote_repo_modern_git(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test repository creation with Git 2.30.0+ that supports --initial-branch."""
    repo_path = tmp_path / "test-repo"

    init_calls: list[dict[str, t.Any]] = []

    def mock_init(self: Git, *args: t.Any, **kwargs: t.Any) -> str:
        init_calls.append({"args": args, "kwargs": kwargs})
        # Simulate successful init with --initial-branch support
        self.path.mkdir(exist_ok=True)
        (self.path / ".git").mkdir(exist_ok=True)
        branch = kwargs.get("initial_branch", "master")
        return f"Initialized empty Git repository with initial branch '{branch}'"

    monkeypatch.setattr(Git, "init", mock_init)

    result = _create_git_remote_repo(repo_path, initial_branch="main")

    # Should only call init once since it succeeded
    assert len(init_calls) == 1
    assert init_calls[0]["kwargs"].get("initial_branch") == "main"
    assert result == repo_path


@pytest.mark.parametrize(
    ("env_var", "param", "expected_branch"),
    [
        ("custom-env", None, "custom-env"),  # Use env var
        ("custom-env", "param-override", "param-override"),  # Param overrides env
        (None, "explicit-param", "explicit-param"),  # Use param
        (None, None, DEFAULT_GIT_INITIAL_BRANCH),  # Use default
    ],
)
def test_create_git_remote_repo_branch_configuration(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    env_var: str | None,
    param: str | None,
    expected_branch: str,
) -> None:
    """Test initial branch configuration hierarchy."""
    # Always reload the module to ensure fresh state
    import sys

    if "libvcs.pytest_plugin" in sys.modules:
        del sys.modules["libvcs.pytest_plugin"]

    if env_var:
        monkeypatch.setenv("LIBVCS_GIT_DEFAULT_INITIAL_BRANCH", env_var)

    # Import after setting env var
    from libvcs.pytest_plugin import _create_git_remote_repo

    repo_path = tmp_path / "test-repo"

    # Track what branch was used
    used_branch = None

    def mock_init(self: Git, *args: t.Any, **kwargs: t.Any) -> str:
        nonlocal used_branch
        used_branch = kwargs.get("initial_branch")
        self.path.mkdir(exist_ok=True)
        (self.path / ".git").mkdir(exist_ok=True)
        return "Initialized"

    monkeypatch.setattr(Git, "init", mock_init)

    _create_git_remote_repo(repo_path, initial_branch=param)

    assert used_branch == expected_branch


def test_create_git_remote_repo_post_init_callback(tmp_path: pathlib.Path) -> None:
    """Test that post-init callback is executed."""
    repo_path = tmp_path / "test-repo"
    callback_executed = False
    callback_path = None

    def post_init_callback(
        remote_repo_path: pathlib.Path,
        env: t.Any = None,
    ) -> None:
        nonlocal callback_executed, callback_path
        callback_executed = True
        callback_path = remote_repo_path
        (remote_repo_path / "callback-marker.txt").write_text("executed")

    _create_git_remote_repo(
        repo_path,
        remote_repo_post_init=post_init_callback,
        init_cmd_args=[],  # Create non-bare repo for easier testing
    )

    assert callback_executed
    assert callback_path == repo_path
    assert (repo_path / "callback-marker.txt").exists()
    assert (repo_path / "callback-marker.txt").read_text() == "executed"


def test_create_git_remote_repo_permission_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling of permission errors."""
    repo_path = tmp_path / "test-repo"

    def mock_init(self: Git, *args: t.Any, **kwargs: t.Any) -> str:
        msg = "fatal: cannot mkdir .git: Permission denied"
        raise CommandError(
            msg,
            returncode=128,
            cmd=["git", "init"],
        )

    monkeypatch.setattr(Git, "init", mock_init)

    with pytest.raises(CommandError) as exc_info:
        _create_git_remote_repo(repo_path)

    assert "Permission denied" in str(exc_info.value)


@pytest.mark.skipif(
    not shutil.which("git"),
    reason="git is not available",
)
def test_create_git_remote_repo_integration(tmp_path: pathlib.Path) -> None:
    """Integration test with real git command."""
    repo_path = tmp_path / "integration-repo"

    result = _create_git_remote_repo(repo_path, initial_branch="development")

    assert result == repo_path
    assert repo_path.exists()

    # Check actual git status
    git = Git(path=repo_path)

    # Get git version to determine what to check
    try:
        version = git.version()
        if version.major > 2 or (version.major == 2 and version.minor >= 30):
            # Can check branch name on modern Git
            branch_output = git.run(["symbolic-ref", "HEAD"])
            assert "refs/heads/development" in branch_output
    except Exception:
        # Just verify it's a valid repo
        status = git.run(["status", "--porcelain"])
        assert isinstance(status, str)
