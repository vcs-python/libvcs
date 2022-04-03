"""Tests for libvcs git repos."""
import datetime
import getpass
import os
import pathlib
import textwrap
from typing import Callable

import pytest

from pytest_mock import MockerFixture

from libvcs import exc
from libvcs.git import (
    FullRemoteDict,
    GitRemote,
    GitRepo,
    convert_pip_url as git_convert_pip_url,
    extract_status,
)
from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run, which

if not which("git"):
    pytestmark = pytest.mark.skip(reason="git is not available")


RepoTestFactory = Callable[..., GitRepo]
RepoTestFactoryLazyKwargs = Callable[..., dict]
RepoTestFactoryRemotesLazyExpected = Callable[..., FullRemoteDict]


@pytest.fixture(autouse=True, scope="module")
def gitconfig(user_path: pathlib.Path):
    gitconfig = user_path / ".gitconfig"
    gitconfig.write_text(
        textwrap.dedent(
            f"""
  [user]
    email = libvcs@git-pull.com
    name = {getpass.getuser()}
    """
        ),
        encoding="utf-8",
    )
    return gitconfig


@pytest.fixture(autouse=True)
def gitconfig_default(monkeypatch: pytest.MonkeyPatch, user_path: pathlib.Path):
    monkeypatch.setenv("HOME", str(user_path))


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda bare_repo_dir, tmp_path, **kwargs: {
                "url": f"file://{bare_repo_dir}",
                "repo_dir": tmp_path / "obtaining a bare repo",
            },
        ],
        [
            create_repo_from_pip_url,
            lambda bare_repo_dir, tmp_path, **kwargs: {
                "pip_url": f"git+file://{bare_repo_dir}",
                "repo_dir": tmp_path / "obtaining a bare repo",
            },
        ],
    ],
)
def test_repo_git_obtain_initial_commit_repo(
    tmp_path: pathlib.Path,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    """initial commit repos return 'initial'.

    note: this behaviors differently from git(1)'s use of the word "bare".
    running `git rev-parse --is-bare-repository` would return false.
    """
    repo_name = "my_git_project"

    run(["git", "init", repo_name], cwd=tmp_path)

    bare_repo_dir = tmp_path / repo_name
    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    assert git_repo.get_revision() == "initial"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda git_remote, tmp_path, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
            },
        ],
        [
            create_repo_from_pip_url,
            lambda git_remote, tmp_path, **kwargs: {
                "pip_url": f"git+file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
            },
        ],
    ],
)
def test_repo_git_obtain_full(
    tmp_path: pathlib.Path,
    git_remote,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    test_repo_revision = run(["git", "rev-parse", "HEAD"], cwd=git_remote)

    assert git_repo.get_revision() == test_repo_revision
    assert os.path.exists(tmp_path / "myrepo")


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda git_remote, tmp_path, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
            },
        ],
        [
            create_repo_from_pip_url,
            lambda git_remote, tmp_path, **kwargs: {
                "pip_url": f"git+file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
            },
        ],
    ],
)
def test_repo_update_handle_cases(
    tmp_path: pathlib.Path,
    git_remote: pathlib.Path,
    mocker: MockerFixture,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()  # clone initial repo
    mocka = mocker.spy(git_repo, "run")
    git_repo.update_repo()

    mocka.assert_any_call(["symbolic-ref", "--short", "HEAD"])

    mocka.reset_mock()

    # will only look up symbolic-ref if no rev specified for object
    git_repo.rev = "HEAD"
    git_repo.update_repo()
    assert mocker.call(["symbolic-ref", "--short", "HEAD"]) not in mocka.mock_calls


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda git_remote, tmp_path, progress_callback, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
                "progress_callback": progress_callback,
            },
        ],
        [
            create_repo_from_pip_url,
            lambda git_remote, tmp_path, progress_callback, **kwargs: {
                "pip_url": f"git+file://{git_remote}",
                "repo_dir": tmp_path / "myrepo",
                "progress_callback": progress_callback,
            },
        ],
    ],
)
def test_progress_callback(
    tmp_path: pathlib.Path,
    git_remote: pathlib.Path,
    mocker: MockerFixture,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    def progress_callback_spy(output, timestamp):
        assert isinstance(output, str)
        assert isinstance(timestamp, datetime.datetime)

    progress_callback = mocker.Mock(
        name="progress_callback_stub", side_effect=progress_callback_spy
    )

    run(["git", "rev-parse", "HEAD"], cwd=git_remote)

    # create a new repo with the repo as a remote
    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    assert progress_callback.called


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options,lazy_remote_expected",
    [
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
            },
            lambda git_remote, **kwargs: {"origin": f"file://{git_remote}"},
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {"origin": f"file://{git_remote}"},
            },
            lambda git_remote, **kwargs: {"origin": f"file://{git_remote}"},
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote}",
                    "second_remote": f"file://{git_remote}",
                },
            },
            lambda git_remote, **kwargs: {
                "origin": f"file://{git_remote}",
                "second_remote": f"file://{git_remote}",
            },
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "second_remote": f"file://{git_remote}",
                },
            },
            lambda git_remote, **kwargs: {
                "origin": f"file://{git_remote}",
                "second_remote": f"file://{git_remote}",
            },
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "origin": GitRemote(
                        name="origin",
                        fetch_url=f"file://{git_remote}",
                        push_url=f"file://{git_remote}",
                    ),
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=f"file://{git_remote}",
                        push_url=f"file://{git_remote}",
                    ),
                },
            },
            lambda git_remote, **kwargs: {
                "origin": f"file://{git_remote}",
                "second_remote": f"file://{git_remote}",
            },
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=f"file://{git_remote}",
                        push_url=f"file://{git_remote}",
                    ),
                },
            },
            lambda git_remote, **kwargs: {
                "second_remote": f"file://{git_remote}",
            },
        ],
        [
            create_repo_from_pip_url,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "pip_url": f"git+file://{git_remote}",
                "repo_dir": repos_path / repo_name,
            },
            lambda git_remote, **kwargs: {"origin": f"file://{git_remote}"},
        ],
    ],
)
def test_remotes(
    repos_path: pathlib.Path,
    git_remote: pathlib.Path,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
    lazy_remote_expected: RepoTestFactoryRemotesLazyExpected,
):
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    expected = lazy_remote_expected(**locals())
    assert len(expected.keys()) > 0
    for expected_remote_name, expected_remote_url in expected.items():
        assert (
            expected_remote_name,
            expected_remote_url,
            expected_remote_url,
        ) == git_repo.remote(expected_remote_name)


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options,lazy_remote_dict,lazy_remote_expected",
    [
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote}",
                },
            },
            lambda git_remote, **kwargs: {
                "second_remote": GitRemote(
                    **{
                        "name": "second_remote",
                        "fetch_url": f"file://{git_remote}",
                        "push_url": f"file://{git_remote}",
                    }
                )
            },
            lambda git_remote, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=f"file://{git_remote}",
                    fetch_url=f"file://{git_remote}",
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=f"file://{git_remote}",
                    fetch_url=f"file://{git_remote}",
                ),
            },
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote}",
                    # accepts short-hand form since it's inputted in the constructor
                    "second_remote": f"file://{git_remote}",
                },
            },
            lambda git_remote, **kwargs: {},
            lambda git_remote, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=f"file://{git_remote}",
                    fetch_url=f"file://{git_remote}",
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=f"file://{git_remote}",
                    fetch_url=f"file://{git_remote}",
                ),
            },
        ],
        [
            GitRepo,
            lambda git_remote, repos_path, repo_name, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": repos_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote}",
                },
            },
            lambda git_remote, **kwargs: {
                "origin": GitRemote(
                    **{
                        "name": "second_remote",
                        "fetch_url": "https://github.com/vcs-python/libvcs",
                        "push_url": "https://github.com/vcs-python/libvcs",
                    }
                )
            },
            lambda git_remote, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url="https://github.com/vcs-python/libvcs",
                    fetch_url="https://github.com/vcs-python/libvcs",
                ),
            },
        ],
    ],
)
def test_remotes_update_repo(
    repos_path: pathlib.Path,
    git_remote: pathlib.Path,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
    lazy_remote_dict: RepoTestFactoryRemotesLazyExpected,
    lazy_remote_expected: RepoTestFactoryRemotesLazyExpected,
):
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    git_repo._remotes |= lazy_remote_dict(**locals())
    git_repo.update_repo(set_remotes=True)

    expected = lazy_remote_expected(**locals())
    assert len(expected.keys()) > 0
    for expected_remote_name, expected_remote_url in expected.items():
        assert expected_remote_url == git_repo.remote(expected_remote_name)


def test_git_get_url_and_rev_from_pip_url():
    pip_url = "git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git"

    url, rev = git_convert_pip_url(pip_url)
    assert "ssh://git@bitbucket.example.com:7999/PROJ/repo.git" == url
    assert rev is None

    pip_url = "{}@{}".format(
        "git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git",
        "eucalyptus",
    )
    url, rev = git_convert_pip_url(pip_url)
    assert "ssh://git@bitbucket.example.com:7999/PROJ/repo.git" == url
    assert rev == "eucalyptus"

    # the git manual refers to this as "scp-like syntax"
    # https://git-scm.com/docs/git-clone
    pip_url = "{}@{}".format("git+user@hostname:user/repo.git", "eucalyptus")
    url, rev = git_convert_pip_url(pip_url)
    assert "user@hostname:user/repo.git" == url
    assert rev == "eucalyptus"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda git_remote, repo_dir, **kwargs: {
                "url": f"file://{git_remote}",
                "repo_dir": str(repo_dir),
            },
        ],
        [
            create_repo_from_pip_url,
            lambda git_remote, repo_dir, **kwargs: {
                "pip_url": f"git+file://{git_remote}",
                "repo_dir": repo_dir,
            },
        ],
    ],
)
def test_remotes_preserves_git_ssh(
    repos_path: pathlib.Path,
    git_remote: pathlib.Path,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    # Regression test for #14
    repo_name = "myexamplegit"
    repo_dir = repos_path / repo_name
    remote_name = "myremote"
    remote_url = "git+ssh://git@github.com/tony/AlgoXY.git"
    git_repo: GitRepo = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    git_repo.set_remote(name=remote_name, url=remote_url)

    assert (
        GitRemote(remote_name, remote_url, remote_url)._asdict()
        in git_repo.remotes().values()
    )


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitRepo,
            lambda bare_repo_dir, tmp_path, **kwargs: {
                "url": f"file://{bare_repo_dir}",
                "repo_dir": tmp_path / "obtaining a bare repo",
            },
        ],
        [
            create_repo_from_pip_url,
            lambda bare_repo_dir, tmp_path, **kwargs: {
                "pip_url": f"git+file://{bare_repo_dir}",
                "repo_dir": tmp_path / "obtaining a bare repo",
            },
        ],
    ],
)
def test_private_ssh_format(
    pip_url_kwargs: dict,
    constructor: RepoTestFactory,
    lazy_constructor_options: RepoTestFactoryLazyKwargs,
):
    pip_url_kwargs.update(
        **{"pip_url": "git+ssh://github.com:/tmp/omg/private_ssh_repo"}
    )

    with pytest.raises(exc.LibVCSException) as excinfo:
        create_repo_from_pip_url(**pip_url_kwargs)
    excinfo.match(r"is malformatted")


def test_ls_remotes(git_repo: GitRepo):
    remotes = git_repo.remotes()

    assert "origin" in remotes
    assert "origin" in git_repo.remotes(flat=True)


def test_get_remotes(git_repo: GitRepo):
    assert "origin" in git_repo.remotes()


@pytest.mark.parametrize(
    "repo_name,new_repo_url",
    [
        ["myrepo", "file:///apples"],
    ],
)
def test_set_remote(git_repo: GitRepo, repo_name: str, new_repo_url: str):
    mynewremote = git_repo.set_remote(name=repo_name, url="file:///")

    assert "file:///" in mynewremote, "set_remote returns remote"

    assert "file:///" in git_repo.remote(name=repo_name), "remote returns remote"

    assert "myrepo" in git_repo.remotes(), ".remotes() returns new remote"

    with pytest.raises(
        exc.CommandError,
        match=f".*remote {repo_name} already exists.*",
    ):
        mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url)

    mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url, overwrite=True)

    assert new_repo_url in git_repo.remote(
        name="myrepo"
    ), "Running remove_set should overwrite previous remote"


def test_get_git_version(git_repo: GitRepo):
    expected_version = git_repo.run(["--version"]).replace("git version ", "")
    assert git_repo.get_git_version()
    assert expected_version == git_repo.get_git_version()


def test_get_current_remote_name(git_repo: GitRepo):
    assert git_repo.get_current_remote_name() == "origin"

    new_branch = "another-branch-with-no-upstream"
    git_repo.run(["checkout", "-B", new_branch])
    assert (
        git_repo.get_current_remote_name() == new_branch
    ), "branch w/o upstream should return branch only"

    new_remote_name = "new_remote_name"
    git_repo.set_remote(
        name=new_remote_name, url=f"file://{git_repo.path}", overwrite=True
    )
    git_repo.run(["fetch", new_remote_name])
    git_repo.run(["branch", "--set-upstream-to", f"{new_remote_name}/{new_branch}"])
    assert (
        git_repo.get_current_remote_name() == new_remote_name
    ), "Should reflect new upstream branch (different remote)"

    upstream = "{}/{}".format(new_remote_name, "master")

    git_repo.run(["branch", "--set-upstream-to", upstream])
    assert (
        git_repo.get_current_remote_name() == upstream
    ), "Should reflect upstream branch (differente remote+branch)"

    git_repo.run(["checkout", "master"])

    # Different remote, different branch
    remote = f"{new_remote_name}/{new_branch}"
    git_repo.run(["branch", "--set-upstream-to", remote])
    assert (
        git_repo.get_current_remote_name() == remote
    ), "Should reflect new upstream branch (different branch)"


def test_extract_status():
    FIXTURE_A = textwrap.dedent(
        """
        # branch.oid d4ccd4d6af04b53949f89fbf0cdae13719dc5a08
        # branch.head fix-current-remote-name
        1 .M N... 100644 100644 100644 91082f119279b6f105ee9a5ce7795b3bdbe2b0de 91082f119279b6f105ee9a5ce7795b3bdbe2b0de CHANGES
    """  # NOQA: E501
    )
    assert {
        "branch_oid": "d4ccd4d6af04b53949f89fbf0cdae13719dc5a08",
        "branch_head": "fix-current-remote-name",
    }.items() <= extract_status(FIXTURE_A)._asdict().items()


@pytest.mark.parametrize(
    "fixture,expected_result",
    [
        [
            """
        # branch.oid de6185fde0806e5c7754ca05676325a1ea4d6348
        # branch.head fix-current-remote-name
        # branch.upstream origin/fix-current-remote-name
        # branch.ab +0 -0
        1 .M N... 100644 100644 100644 91082f119279b6f105ee9a5ce7795b3bdbe2b0de 91082f119279b6f105ee9a5ce7795b3bdbe2b0de CHANGES
        1 .M N... 100644 100644 100644 302ca2c18d4c295ce217bff5f93e1ba342dc6665 302ca2c18d4c295ce217bff5f93e1ba342dc6665 tests/test_git.py
    """,  # NOQA: E501
            {
                "branch_oid": "de6185fde0806e5c7754ca05676325a1ea4d6348",
                "branch_head": "fix-current-remote-name",
                "branch_upstream": "origin/fix-current-remote-name",
                "branch_ab": "+0 -0",
                "branch_ahead": "0",
                "branch_behind": "0",
            },
        ],
        [
            "# branch.upstream moo/origin/myslash/remote",
            {"branch_upstream": "moo/origin/myslash/remote"},
        ],
        [
            """
            # branch.oid c3c5323abc5dca78d9bdeba6c163c2a37b452e69
            # branch.head libvcs-0.4.0
            # branch.upstream origin/libvcs-0.4.0
            # branch.ab +0 -0
            """,
            {
                "branch_oid": "c3c5323abc5dca78d9bdeba6c163c2a37b452e69",
                "branch_head": "libvcs-0.4.0",
                "branch_upstream": "origin/libvcs-0.4.0",
                "branch_ab": "+0 -0",
                "branch_ahead": "0",
                "branch_behind": "0",
            },
        ],
    ],
)
def test_extract_status_b(fixture: str, expected_result: dict):
    assert (
        extract_status(textwrap.dedent(fixture))._asdict().items()
        >= expected_result.items()
    )


@pytest.mark.parametrize(
    "fixture,expected_result",
    [
        [
            "# branch.ab +1 -83",
            {
                "branch_ab": "+1 -83",
                "branch_ahead": "1",
                "branch_behind": "83",
            },
        ],
        [
            """
            # branch.ab +0 -0
            """,
            {
                "branch_ab": "+0 -0",
                "branch_ahead": "0",
                "branch_behind": "0",
            },
        ],
        [
            """
            # branch.ab +1 -83
            """,
            {
                "branch_ab": "+1 -83",
                "branch_ahead": "1",
                "branch_behind": "83",
            },
        ],
        [
            """
            # branch.ab +9999999 -9999999
            """,
            {
                "branch_ab": "+9999999 -9999999",
                "branch_ahead": "9999999",
                "branch_behind": "9999999",
            },
        ],
    ],
)
def test_extract_status_c(fixture: str, expected_result: dict):
    assert (
        expected_result.items()
        <= extract_status(textwrap.dedent(fixture))._asdict().items()
    )
