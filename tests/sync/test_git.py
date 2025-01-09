"""Tests for libvcs GitSync."""

from __future__ import annotations

import datetime
import pathlib
import random
import shutil
import textwrap
import typing as t
from collections.abc import Callable

import pytest

from libvcs import exc
from libvcs._internal.run import run
from libvcs._internal.shortcuts import create_project
from libvcs.sync.git import (
    GitRemote,
    GitStatus,
    GitSync,
    convert_pip_url as git_convert_pip_url,
)

if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from libvcs.pytest_plugin import CreateRepoPytestFixtureFn

if not shutil.which("git"):
    pytestmark = pytest.mark.skip(reason="git is not available")


ProjectTestFactory = Callable[..., GitSync]
ProjectTestFactoryLazyKwargs = Callable[..., dict[str, str]]
ProjectTestFactoryRemoteLazyExpected = Callable[..., dict[str, GitRemote]]


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": bare_dir.as_uri(),
                "path": tmp_path / "obtaining a bare repo",
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": f"git+{bare_dir.as_uri()}",
                "path": tmp_path / "obtaining a bare repo",
                "vcs": "git",
            },
        ),
    ],
)
def test_repo_git_obtain_initial_commit_repo(
    tmp_path: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Initial commit repos return 'initial'.

    note: this behaviors differently from git(1)'s use of the word "bare".
    running `git rev-parse --is-bare-repository` would return false.
    """
    repo_name = "my_git_project"

    run(["git", "init", repo_name], cwd=tmp_path)

    bare_dir = tmp_path / repo_name
    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    assert git_repo.get_revision() == "initial"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": tmp_path / "myrepo",
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": f"git+{git_remote_repo.as_uri()}",
                "path": tmp_path / "myrepo",
                "vcs": "git",
            },
        ),
    ],
)
def test_repo_git_obtain_full(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Test GitSync.obtain()."""
    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    test_repo_revision = run(["git", "rev-parse", "HEAD"], cwd=git_remote_repo)

    assert git_repo.get_revision() == test_repo_revision
    assert (tmp_path / "myrepo").exists()


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": tmp_path / "myrepo",
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": f"git+{git_remote_repo.as_uri()}",
                "path": tmp_path / "myrepo",
                "vcs": "git",
            },
        ),
    ],
)
def test_repo_update_handle_cases(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    mocker: MockerFixture,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Test GitSync.update_repo() edgecases."""
    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()  # clone initial repo

    cmd_mock = mocker.spy(git_repo.cmd, "symbolic_ref")
    git_repo.update_repo()

    cmd_mock.assert_any_call(name="HEAD", short=True)

    cmd_mock.reset_mock()

    # will only look up symbolic-ref if no rev specified for object
    git_repo.rev = "HEAD"
    git_repo.update_repo()
    assert mocker.call(name="HEAD", short=True) not in cmd_mock.mock_calls


@pytest.mark.parametrize(
    ("has_untracked_files", "needs_stash", "has_remote_changes"),
    [
        (True, True, True),
        (True, True, False),
        (True, False, True),
        (True, False, False),
        (False, True, True),
        (False, True, False),
        (False, False, True),
        (False, False, False),
    ],
)
def test_repo_update_stash_cases(
    tmp_path: pathlib.Path,
    create_git_remote_bare_repo: CreateRepoPytestFixtureFn,
    mocker: MockerFixture,
    has_untracked_files: bool,
    needs_stash: bool,
    has_remote_changes: bool,
) -> None:
    """Test GitSync.update_repo() stash cases."""
    git_bare_repo = create_git_remote_bare_repo()

    git_repo: GitSync = GitSync(
        url=git_bare_repo.as_uri(),
        path=tmp_path / "myrepo",
        vcs="git",
    )
    git_repo.obtain()  # clone initial repo

    # Make an initial commit so we can reset
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text(f"some content: {random.random()}", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "a commit"])
    git_repo.run(["push"])

    if has_remote_changes:
        some_file = git_repo.path / "some_file"
        some_file.write_text(f"some content: {random.random()}", encoding="utf-8")
        git_repo.run(["add", some_file])
        git_repo.run(["commit", "-m", "a commit"])
        git_repo.run(["push"])
        git_repo.run(["reset", "--hard", "HEAD^"])

    if has_untracked_files:
        some_file = git_repo.path / "some_file"
        some_file.write_text(f"some content: {random.random()}", encoding="utf-8")

    if needs_stash:
        some_stashed_file = git_repo.path / "some_stashed_file"
        some_stashed_file.write_text(
            f"some content: {random.random()}",
            encoding="utf-8",
        )
        git_repo.run(["add", some_stashed_file])

    cmd_mock = mocker.spy(git_repo.cmd, "symbolic_ref")
    git_repo.update_repo()

    cmd_mock.assert_any_call(name="HEAD", short=True)


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda git_remote_repo, tmp_path, progress_callback, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": tmp_path / "myrepo",
                "progress_callback": progress_callback,
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda git_remote_repo, tmp_path, progress_callback, **kwargs: {
                "url": f"git+{git_remote_repo.as_uri()}",
                "path": tmp_path / "myrepo",
                "progress_callback": progress_callback,
                "vcs": "git",
            },
        ),
    ],
)
def test_progress_callback(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    mocker: MockerFixture,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Test GitSync with progress callback."""

    def progress_callback_spy(output: str, timestamp: datetime.datetime) -> None:
        assert isinstance(output, str)
        assert isinstance(timestamp, datetime.datetime)

    progress_callback = mocker.Mock(
        name="progress_callback_stub",
        side_effect=progress_callback_spy,
    )

    # create a new repo with the repo as a remote
    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    assert progress_callback.called


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options", "lazy_remote_expected"),
    [
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {"origin": git_remote_repo.as_uri()},
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "origin": git_remote_repo.as_uri(),
                    "second_remote": git_remote_repo.as_uri(),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "second_remote": git_remote_repo.as_uri(),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "origin": GitRemote(
                        name="origin",
                        fetch_url=git_remote_repo.as_uri(),
                        push_url=git_remote_repo.as_uri(),
                    ),
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=git_remote_repo.as_uri(),
                        push_url=git_remote_repo.as_uri(),
                    ),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "vcs": "git",
                "remotes": {
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=git_remote_repo.as_uri(),
                        push_url=git_remote_repo.as_uri(),
                    ),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "second_remote": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            create_project,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"git+{git_remote_repo.as_uri()}",
                "path": projects_path / repo_name,
                "vcs": "git",
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
        ),
    ],
)
def test_remotes(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
    lazy_remote_expected: ProjectTestFactoryRemoteLazyExpected,
) -> None:
    """Tests GitSync Remotes."""
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    expected = lazy_remote_expected(**locals())
    assert len(expected.keys()) > 0
    for expected_remote_name, expected_remote_dict in expected.items():
        remote = git_repo.remote(expected_remote_name)
        assert remote is not None

        if remote is not None:
            assert expected_remote_name == remote.name
            assert expected_remote_dict.fetch_url == remote.fetch_url
            assert expected_remote_dict.push_url == remote.push_url


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    (
        "constructor",
        "lazy_constructor_options",
        "lazy_remote_dict",
        "lazy_remote_expected",
    ),
    [
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "origin": git_remote_repo.as_uri(),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "second_remote": GitRemote(
                    name="second_remote",
                    fetch_url=git_remote_repo.as_uri(),
                    push_url=git_remote_repo.as_uri(),
                ),
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=git_remote_repo.as_uri(),
                    fetch_url=git_remote_repo.as_uri(),
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=git_remote_repo.as_uri(),
                    fetch_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "origin": git_remote_repo.as_uri(),
                    # accepts short-hand form since it's inputted in the constructor
                    "second_remote": git_remote_repo.as_uri(),
                },
            },
            lambda git_remote_repo, **kwargs: {},
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=git_remote_repo.as_uri(),
                    fetch_url=git_remote_repo.as_uri(),
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=git_remote_repo.as_uri(),
                    fetch_url=git_remote_repo.as_uri(),
                ),
            },
        ),
        (
            GitSync,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": projects_path / repo_name,
                "remotes": {
                    "origin": git_remote_repo.as_uri(),
                },
            },
            lambda git_remote_repo, second_git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="second_remote",
                    fetch_url=f"{second_git_remote_repo!s}",
                    push_url=f"{second_git_remote_repo!s}",
                ),
            },
            lambda git_remote_repo, second_git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=f"{second_git_remote_repo!s}",
                    push_url=f"{second_git_remote_repo!s}",
                ),
            },
        ),
    ],
)
def test_remotes_update_repo(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
    lazy_remote_dict: ProjectTestFactoryRemoteLazyExpected,
    lazy_remote_expected: ProjectTestFactoryRemoteLazyExpected,
    create_git_remote_repo: CreateRepoPytestFixtureFn,
) -> None:
    """Tests GitSync with updated remotes."""
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    second_git_remote_repo = create_git_remote_repo()

    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    git_repo._remotes |= {
        k: GitRemote(*v) if isinstance(v, dict) else v
        for k, v in lazy_remote_dict(**locals()).items()
    }
    git_repo.update_repo(set_remotes=True)

    expected = lazy_remote_expected(**locals())
    assert len(expected.keys()) > 0
    for expected_remote_name, expected_remote in expected.items():
        assert expected_remote == git_repo.remote(expected_remote_name)


def test_git_get_url_and_rev_from_pip_url() -> None:
    """Test GitSync via pip URL."""
    pip_url = "git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git"

    url, rev = git_convert_pip_url(pip_url)
    assert url == "ssh://git@bitbucket.example.com:7999/PROJ/repo.git"
    assert rev is None

    pip_url = "{}@{}".format(
        "git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git",
        "eucalyptus",
    )
    url, rev = git_convert_pip_url(pip_url)
    assert url == "ssh://git@bitbucket.example.com:7999/PROJ/repo.git"
    assert rev == "eucalyptus"

    # the git manual refers to this as "scp-like syntax"
    # https://git-scm.com/docs/git-clone
    pip_url = "{}@{}".format("git+user@hostname:user/repo.git", "eucalyptus")
    url, rev = git_convert_pip_url(pip_url)
    assert url == "user@hostname:user/repo.git"
    assert rev == "eucalyptus"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda git_remote_repo, path, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": path,
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda git_remote_repo, path, **kwargs: {
                "url": f"git+{git_remote_repo.as_uri()}",
                "path": path,
                "vcs": "git",
            },
        ),
    ],
)
def test_remotes_preserves_git_ssh(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Test GitSync preserves Git SSH."""
    # Regression test for #14
    repo_name = "myexamplegit"
    path = projects_path / repo_name
    remote_name = "myremote"
    remote_url = "git+ssh://git@github.com/tony/AlgoXY.git"
    git_repo: GitSync = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    git_repo.set_remote(name=remote_name, url=remote_url)

    assert GitRemote(remote_name, remote_url, remote_url) in list(
        git_repo.remotes().values(),
    )


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": bare_dir.as_uri(),
                "path": tmp_path / "obtaining a bare repo",
                "vcs": "git",
            },
        ),
        (
            create_project,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": f"git+{bare_dir.as_uri()}",
                "path": tmp_path / "obtaining a bare repo",
                "vcs": "git",
            },
        ),
    ],
)
def test_private_ssh_format(
    tmp_path: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
) -> None:
    """Test GitSync with private ssh repo format."""
    with pytest.raises(exc.LibVCSException) as excinfo:
        create_project(
            url=git_convert_pip_url(
                "git+ssh://github.com:/tmp/omg/private_ssh_repo",
            ).url,
            path=tmp_path,
            vcs="git",
        )
        excinfo.match(r".*is a malformed.*")


def test_git_sync_remotes(git_repo: GitSync) -> None:
    """Test GitSync.remotes()."""
    remotes = git_repo.remotes()

    assert "origin" in remotes
    assert git_repo.cmd.remote.show() == "origin"
    assert "origin" in git_repo.cmd.remote.show(name="origin")
    assert "origin" in git_repo.cmd.remote.show(name="origin", no_query_remotes=True)
    assert git_repo.remotes()["origin"].name == "origin"


@pytest.mark.parametrize(
    ("repo_name", "new_repo_url"),
    [
        ("myrepo", "file:///apples"),
    ],
)
def test_set_remote(git_repo: GitSync, repo_name: str, new_repo_url: str) -> None:
    """Test GitSync.set_remote()."""
    mynewremote = git_repo.set_remote(name=repo_name, url="file:///")

    assert "file:///" in mynewremote.fetch_url, "set_remote returns remote"

    assert isinstance(
        git_repo.remote(name=repo_name),
        GitRemote,
    ), "remote() returns GitRemote"
    remote = git_repo.remote(name=repo_name)
    assert remote is not None, "Remote should exist"
    if remote is not None:
        assert "file:///" in remote.fetch_url, "new value set"

    assert "myrepo" in git_repo.remotes(), ".remotes() returns new remote"

    with pytest.raises(
        exc.CommandError,
        match=f".*remote {repo_name} already exists.*",
    ):
        mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url)

    mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url, overwrite=True)

    remote = git_repo.remote(name="myrepo")
    assert remote is not None
    if remote is not None:
        assert new_repo_url in remote.fetch_url, (
            "Running remove_set should overwrite previous remote"
        )


def test_get_git_version(git_repo: GitSync) -> None:
    """Test get_git_version()."""
    expected_version = git_repo.run(["--version"]).replace("git version ", "")
    assert git_repo.get_git_version()
    assert expected_version == git_repo.get_git_version()


def test_get_current_remote_name(git_repo: GitSync) -> None:
    """Test retrieval of current remote."""
    assert git_repo.get_current_remote_name() == "origin"

    new_branch = "another-branch-with-no-upstream"
    git_repo.run(["checkout", "-B", new_branch])
    assert git_repo.get_current_remote_name() == new_branch, (
        "branch w/o upstream should return branch only"
    )

    new_remote_name = "new_remote_name"
    git_repo.set_remote(
        name=new_remote_name,
        url=git_repo.path.as_uri(),
        overwrite=True,
    )
    git_repo.run(["fetch", new_remote_name])
    git_repo.run(["branch", "--set-upstream-to", f"{new_remote_name}/{new_branch}"])
    assert git_repo.get_current_remote_name() == new_remote_name, (
        "Should reflect new upstream branch (different remote)"
    )

    upstream = "{}/{}".format(new_remote_name, "master")

    git_repo.run(["branch", "--set-upstream-to", upstream])
    assert git_repo.get_current_remote_name() == upstream, (
        "Should reflect upstream branch (different remote+branch)"
    )

    git_repo.run(["checkout", "master"])

    # Different remote, different branch
    remote = f"{new_remote_name}/{new_branch}"
    git_repo.run(["branch", "--set-upstream-to", remote])
    assert git_repo.get_current_remote_name() == remote, (
        "Should reflect new upstream branch (different branch)"
    )


def test_GitRemote_from_stdout() -> None:
    """Test GitStatus.from_stdout()."""
    FIXTURE_A = textwrap.dedent(
        """
        # branch.oid d4ccd4d6af04b53949f89fbf0cdae13719dc5a08
        # branch.head fix-current-remote-name
        1 .M N... 100644 100644 100644 91082f119279b6f105ee9a5ce7795b3bdbe2b0de 91082f119279b6f105ee9a5ce7795b3bdbe2b0de CHANGES
    """,  # NOQA: E501
    )
    assert GitStatus(
        branch_oid="d4ccd4d6af04b53949f89fbf0cdae13719dc5a08",
        branch_head="fix-current-remote-name",
    ) == GitStatus.from_stdout(FIXTURE_A)


class GitBranchComplexResult(t.TypedDict):
    """Test fixture for GitBranch."""

    branch_oid: str
    branch_head: str
    branch_upstream: str
    branch_ab: str
    branch_ahead: str
    branch_behind: str


@pytest.mark.parametrize(
    ("fixture", "expected_result"),
    [
        (
            """
        # branch.oid de6185fde0806e5c7754ca05676325a1ea4d6348
        # branch.head fix-current-remote-name
        # branch.upstream origin/fix-current-remote-name
        # branch.ab +0 -0
        1 .M N... 100644 100644 100644 91082f119279b6f105ee9a5ce7795b3bdbe2b0de 91082f119279b6f105ee9a5ce7795b3bdbe2b0de CHANGES
        1 .M N... 100644 100644 100644 302ca2c18d4c295ce217bff5f93e1ba342dc6665 302ca2c18d4c295ce217bff5f93e1ba342dc6665 tests/test_git.py
    """,  # NOQA: E501
            GitStatus(
                branch_oid="de6185fde0806e5c7754ca05676325a1ea4d6348",
                branch_head="fix-current-remote-name",
                branch_upstream="origin/fix-current-remote-name",
                branch_ab="+0 -0",
                branch_ahead="0",
                branch_behind="0",
            ),
        ),
        (
            "# branch.upstream moo/origin/myslash/remote",
            GitStatus(branch_upstream="moo/origin/myslash/remote"),
        ),
        (
            """
            # branch.oid c3c5323abc5dca78d9bdeba6c163c2a37b452e69
            # branch.head libvcs-0.4.0
            # branch.upstream origin/libvcs-0.4.0
            # branch.ab +0 -0
            """,
            GitStatus(
                branch_oid="c3c5323abc5dca78d9bdeba6c163c2a37b452e69",
                branch_head="libvcs-0.4.0",
                branch_upstream="origin/libvcs-0.4.0",
                branch_ab="+0 -0",
                branch_ahead="0",
                branch_behind="0",
            ),
        ),
    ],
)
def test_GitRemote__from_stdout_b(fixture: str, expected_result: GitStatus) -> None:
    """Test GitStatus.from_stdout()."""
    assert GitStatus.from_stdout(textwrap.dedent(fixture)) == expected_result


class GitBranchResult(t.TypedDict):
    """Test dictionary for GitStatus branch result."""

    branch_ab: str
    branch_ahead: str
    branch_behind: str


@pytest.mark.parametrize(
    ("fixture", "expected_result"),
    [
        (
            "# branch.ab +1 -83",
            GitStatus(
                branch_ab="+1 -83",
                branch_ahead="1",
                branch_behind="83",
            ),
        ),
        (
            """
            # branch.ab +0 -0
            """,
            GitStatus(
                branch_ab="+0 -0",
                branch_ahead="0",
                branch_behind="0",
            ),
        ),
        (
            """
            # branch.ab +1 -83
            """,
            GitStatus(
                branch_ab="+1 -83",
                branch_ahead="1",
                branch_behind="83",
            ),
        ),
        (
            """
            # branch.ab +9999999 -9999999
            """,
            GitStatus(
                branch_ab="+9999999 -9999999",
                branch_ahead="9999999",
                branch_behind="9999999",
            ),
        ),
    ],
)
def test_GitRemote__from_stdout_c(fixture: str, expected_result: GitStatus) -> None:
    """Test for GitStatus.from_stdout()."""
    assert expected_result == GitStatus.from_stdout(textwrap.dedent(fixture))


def test_repo_git_remote_checkout(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for create_git_remote_repo w/ remote checkout."""
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(path=git_repo_checkout_dir, url=git_server.as_uri())

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()
