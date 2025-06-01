"""Tests for libvcs pytest plugin."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
import typing as t

import pytest

from libvcs._internal.run import run
from libvcs.cmd.git import Git
from libvcs.exc import CommandError
from libvcs.pytest_plugin import (
    _create_git_remote_repo,
)

if t.TYPE_CHECKING:
    import pathlib

    from libvcs.pytest_plugin import CreateRepoFn, GitCommitEnvVars
    from libvcs.sync.git import GitSync


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_create_git_remote_repo(
    create_git_remote_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for create_git_remote_repo pytest fixture."""
    git_remote_1 = create_git_remote_repo()
    git_remote_2 = create_git_remote_repo()

    assert git_remote_1 != git_remote_2


@pytest.mark.skipif(not shutil.which("svn"), reason="svn is not available")
def test_create_svn_remote_repo(
    create_svn_remote_repo: CreateRepoFn,
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
    CreateRepoFn,
    git_remote_repo_single_commit_post_init
)


def test_repo_git_remote_repo_and_sync(
    create_git_remote_repo: CreateRepoFn,
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
    create_git_remote_bare_repo: CreateRepoFn,
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


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_gitconfig_submodule_file_protocol(
    gitconfig: pathlib.Path,
    user_path: pathlib.Path,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that gitconfig fixture allows file:// protocol for git submodule operations.

    Git submodule operations spawn child processes that don't inherit local repo config.
    The child `git clone` process needs protocol.file.allow=always in global config.

    Without this setting, submodule operations fail with:
        fatal: transport 'file' not allowed

    This reproduces GitHub issue #509 where tests fail in strict build environments
    (like Arch Linux packaging) that don't have protocol.file.allow set globally.

    See: https://github.com/vcs-python/libvcs/issues/509
    """
    # Isolate git config: use fixture's gitconfig via HOME, block only system config
    # Note: We don't block GIT_CONFIG_GLOBAL because git falls back to $HOME/.gitconfig
    # when GIT_CONFIG_GLOBAL is unset, which is where our fixture puts the config
    monkeypatch.setenv("HOME", str(user_path))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)

    # Create a source repository to use as submodule
    submodule_source = tmp_path / "submodule_source"
    submodule_source.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=submodule_source,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=submodule_source,
        check=True,
        capture_output=True,
    )

    # Create a main repository
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=main_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=main_repo,
        check=True,
        capture_output=True,
    )

    # Try to add submodule using file:// protocol
    # This spawns a child git clone that needs protocol.file.allow=always
    result = subprocess.run(
        ["git", "submodule", "add", str(submodule_source), "vendor/lib"],
        cwd=main_repo,
        capture_output=True,
        text=True,
    )

    # Assert: submodule add should succeed (no "fatal" errors)
    assert "fatal" not in result.stderr.lower(), (
        f"git submodule add failed with: {result.stderr}\n"
        'This indicates gitconfig fixture is missing [protocol "file"] allow = always'
    )
    assert result.returncode == 0, f"git submodule add failed: {result.stderr}"

    # Verify submodule was actually added
    gitmodules = main_repo / ".gitmodules"
    assert gitmodules.exists(), "Submodule should create .gitmodules file"


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_git_repo_fixture_submodule_file_protocol(
    git_repo: GitSync,
    create_git_remote_repo: CreateRepoFn,
    git_commit_envvars: GitCommitEnvVars,
    user_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that git_repo fixture allows file:// protocol for submodule operations.

    This validates that the git_repo fixture has proper HOME setup so child
    processes (spawned by git submodule add) can find $HOME/.gitconfig with
    protocol.file.allow=always.

    The git_repo fixture depends on set_home to ensure child processes
    (like git clone spawned by git submodule add) can find the test gitconfig.

    See: https://github.com/vcs-python/libvcs/issues/509
    """
    from libvcs.pytest_plugin import git_remote_repo_single_commit_post_init

    # Verify that HOME is set to user_path where test gitconfig resides
    assert os.environ.get("HOME") == str(user_path), (
        f"git_repo fixture should set HOME to user_path.\n"
        f"Expected: {user_path}\n"
        f"Actual: {os.environ.get('HOME')}\n"
        "git_repo fixture is missing set_home dependency"
    )

    # Block system config to prevent interference
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)

    # Create a repo to use as submodule source (with a commit so it can be cloned)
    submodule_source = create_git_remote_repo()
    git_remote_repo_single_commit_post_init(
        remote_repo_path=submodule_source,
        env=git_commit_envvars,
    )

    # Add submodule - this spawns child git clone that needs HOME set correctly
    # NOTE: We do NOT use the local config workaround here
    result = git_repo.cmd.submodules.add(
        repository=f"file://{submodule_source}",
        path="vendor/lib",
    )

    assert "fatal" not in result.lower(), (
        f"git submodule add failed: {result}\n"
        "git_repo fixture needs set_home dependency for child processes"
    )


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
    ("module_default", "param", "expected_branch"),
    [
        ("custom-env", None, "custom-env"),  # Module default propagates when no param
        ("custom-env", "param-override", "param-override"),  # Param overrides default
        ("master", "explicit-param", "explicit-param"),  # Param wins
        ("master", None, "master"),  # Module default
    ],
)
def test_create_git_remote_repo_branch_configuration(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    module_default: str,
    param: str | None,
    expected_branch: str,
) -> None:
    """Test initial branch configuration hierarchy."""
    from libvcs import pytest_plugin

    monkeypatch.setattr(pytest_plugin, "DEFAULT_GIT_INITIAL_BRANCH", module_default)

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

    pytest_plugin._create_git_remote_repo(repo_path, initial_branch=param)

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
