"""Tests for libvcs pytest plugin."""

from __future__ import annotations

import shutil
import textwrap
import typing as t

import pytest

from libvcs._internal.run import run

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
