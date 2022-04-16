"""Tests for libvcs git repos."""
import datetime
import os
import pathlib
import textwrap
from typing import Callable

import pytest

from pytest_mock import MockerFixture

from libvcs import exc
from libvcs.cmd.core import run, which
from libvcs.conftest import CreateProjectCallbackFixtureProtocol
from libvcs.projects.git import (
    GitFullRemoteDict,
    GitProject,
    GitRemote,
    GitStatus,
    convert_pip_url as git_convert_pip_url,
)
from libvcs.shortcuts import create_project_from_pip_url

if not which("git"):
    pytestmark = pytest.mark.skip(reason="git is not available")


ProjectTestFactory = Callable[..., GitProject]
ProjectTestFactoryLazyKwargs = Callable[..., dict]
ProjectTestFactoryRemotesLazyExpected = Callable[..., GitFullRemoteDict]


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitProject,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": f"file://{bare_dir}",
                "dir": tmp_path / "obtaining a bare repo",
            },
        ],
        [
            create_project_from_pip_url,
            lambda bare_dir, tmp_path, **kwargs: {
                "pip_url": f"git+file://{bare_dir}",
                "dir": tmp_path / "obtaining a bare repo",
            },
        ],
    ],
)
def test_repo_git_obtain_initial_commit_repo(
    tmp_path: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    """initial commit repos return 'initial'.

    note: this behaviors differently from git(1)'s use of the word "bare".
    running `git rev-parse --is-bare-repository` would return false.
    """
    repo_name = "my_git_project"

    run(["git", "init", repo_name], cwd=tmp_path)

    bare_dir = tmp_path / repo_name
    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    assert git_repo.get_revision() == "initial"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitProject,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
            },
        ],
        [
            create_project_from_pip_url,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "pip_url": f"git+file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
            },
        ],
    ],
)
def test_repo_git_obtain_full(
    tmp_path: pathlib.Path,
    git_remote_repo,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    test_repo_revision = run(["git", "rev-parse", "HEAD"], cwd=git_remote_repo)

    assert git_repo.get_revision() == test_repo_revision
    assert os.path.exists(tmp_path / "myrepo")


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitProject,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
            },
        ],
        [
            create_project_from_pip_url,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "pip_url": f"git+file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
            },
        ],
    ],
)
def test_repo_update_handle_cases(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    mocker: MockerFixture,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))
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
            GitProject,
            lambda git_remote_repo, tmp_path, progress_callback, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
                "progress_callback": progress_callback,
            },
        ],
        [
            create_project_from_pip_url,
            lambda git_remote_repo, tmp_path, progress_callback, **kwargs: {
                "pip_url": f"git+file://{git_remote_repo}",
                "dir": tmp_path / "myrepo",
                "progress_callback": progress_callback,
            },
        ],
    ],
)
def test_progress_callback(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    mocker: MockerFixture,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    def progress_callback_spy(output, timestamp):
        assert isinstance(output, str)
        assert isinstance(timestamp, datetime.datetime)

    progress_callback = mocker.Mock(
        name="progress_callback_stub", side_effect=progress_callback_spy
    )

    run(["git", "rev-parse", "HEAD"], cwd=git_remote_repo)

    # create a new repo with the repo as a remote
    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    assert progress_callback.called


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options,lazy_remote_expected",
    [
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
            },
            lambda git_remote_repo, **kwargs: {"origin": f"file://{git_remote_repo}"},
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {"origin": f"file://{git_remote_repo}"},
            },
            lambda git_remote_repo, **kwargs: {"origin": f"file://{git_remote_repo}"},
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote_repo}",
                    "second_remote": f"file://{git_remote_repo}",
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": f"file://{git_remote_repo}",
                "second_remote": f"file://{git_remote_repo}",
            },
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "second_remote": f"file://{git_remote_repo}",
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": f"file://{git_remote_repo}",
                "second_remote": f"file://{git_remote_repo}",
            },
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "origin": GitRemote(
                        name="origin",
                        fetch_url=f"file://{git_remote_repo}",
                        push_url=f"file://{git_remote_repo}",
                    ),
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=f"file://{git_remote_repo}",
                        push_url=f"file://{git_remote_repo}",
                    ),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "origin": f"file://{git_remote_repo}",
                "second_remote": f"file://{git_remote_repo}",
            },
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "second_remote": GitRemote(
                        name="second_remote",
                        fetch_url=f"file://{git_remote_repo}",
                        push_url=f"file://{git_remote_repo}",
                    ),
                },
            },
            lambda git_remote_repo, **kwargs: {
                "second_remote": f"file://{git_remote_repo}",
            },
        ],
        [
            create_project_from_pip_url,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "pip_url": f"git+file://{git_remote_repo}",
                "dir": projects_path / repo_name,
            },
            lambda git_remote_repo, **kwargs: {"origin": f"file://{git_remote_repo}"},
        ],
    ],
)
def test_remotes(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
    lazy_remote_expected: ProjectTestFactoryRemotesLazyExpected,
):
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))
    git_repo.obtain()

    expected = lazy_remote_expected(**locals())
    assert len(expected.keys()) > 0
    for expected_remote_name, expected_remote_url in expected.items():
        assert (
            expected_remote_name,
            expected_remote_url,
            expected_remote_url,
        ) == git_repo.remote(expected_remote_name).to_tuple()


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options,lazy_remote_dict,lazy_remote_expected",
    [
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote_repo}",
                },
            },
            lambda git_remote_repo, **kwargs: {
                "second_remote": GitRemote(
                    **{
                        "name": "second_remote",
                        "fetch_url": f"file://{git_remote_repo}",
                        "push_url": f"file://{git_remote_repo}",
                    }
                )
            },
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=f"file://{git_remote_repo}",
                    fetch_url=f"file://{git_remote_repo}",
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=f"file://{git_remote_repo}",
                    fetch_url=f"file://{git_remote_repo}",
                ),
            },
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote_repo}",
                    # accepts short-hand form since it's inputted in the constructor
                    "second_remote": f"file://{git_remote_repo}",
                },
            },
            lambda git_remote_repo, **kwargs: {},
            lambda git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    push_url=f"file://{git_remote_repo}",
                    fetch_url=f"file://{git_remote_repo}",
                ),
                "second_remote": GitRemote(
                    name="second_remote",
                    push_url=f"file://{git_remote_repo}",
                    fetch_url=f"file://{git_remote_repo}",
                ),
            },
        ],
        [
            GitProject,
            lambda git_remote_repo, projects_path, repo_name, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": projects_path / repo_name,
                "remotes": {
                    "origin": f"file://{git_remote_repo}",
                },
            },
            lambda git_remote_repo, second_git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    **{
                        "name": "second_remote",
                        "fetch_url": f"{second_git_remote_repo!s}",
                        "push_url": f"{second_git_remote_repo!s}",
                    }
                )
            },
            lambda git_remote_repo, second_git_remote_repo, **kwargs: {
                "origin": GitRemote(
                    name="origin",
                    fetch_url=f"{second_git_remote_repo!s}",
                    push_url=f"{second_git_remote_repo!s}",
                ),
            },
        ],
    ],
)
def test_remotes_update_repo(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
    lazy_remote_dict: ProjectTestFactoryRemotesLazyExpected,
    lazy_remote_expected: ProjectTestFactoryRemotesLazyExpected,
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
):
    repo_name = "myrepo"
    remote_name = "myremote"
    remote_url = "https://localhost/my/git/repo.git"

    second_git_remote_repo = create_git_remote_repo()

    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))
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
            GitProject,
            lambda git_remote_repo, dir, **kwargs: {
                "url": f"file://{git_remote_repo}",
                "dir": str(dir),
            },
        ],
        [
            create_project_from_pip_url,
            lambda git_remote_repo, dir, **kwargs: {
                "pip_url": f"git+file://{git_remote_repo}",
                "dir": dir,
            },
        ],
    ],
)
def test_remotes_preserves_git_ssh(
    projects_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    # Regression test for #14
    repo_name = "myexamplegit"
    dir = projects_path / repo_name
    remote_name = "myremote"
    remote_url = "git+ssh://git@github.com/tony/AlgoXY.git"
    git_repo: GitProject = constructor(**lazy_constructor_options(**locals()))

    git_repo.obtain()
    git_repo.set_remote(name=remote_name, url=remote_url)

    assert (
        GitRemote(remote_name, remote_url, remote_url).to_dict()
        in git_repo.remotes().values()
    )


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    "constructor,lazy_constructor_options",
    [
        [
            GitProject,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": f"file://{bare_dir}",
                "dir": tmp_path / "obtaining a bare repo",
            },
        ],
        [
            create_project_from_pip_url,
            lambda bare_dir, tmp_path, **kwargs: {
                "pip_url": f"git+file://{bare_dir}",
                "dir": tmp_path / "obtaining a bare repo",
            },
        ],
    ],
)
def test_private_ssh_format(
    tmpdir: pathlib.Path,
    constructor: ProjectTestFactory,
    lazy_constructor_options: ProjectTestFactoryLazyKwargs,
):
    pip_url_kwargs = {
        "pip_url": "git+ssh://github.com:/tmp/omg/private_ssh_repo",
        "dir": tmpdir,
    }

    with pytest.raises(exc.LibVCSException) as excinfo:
        create_project_from_pip_url(**pip_url_kwargs)
    excinfo.match(r"is malformatted")


def test_ls_remotes(git_repo: GitProject):
    remotes = git_repo.remotes()

    assert "origin" in remotes
    assert "origin" in git_repo.remotes(flat=True)


def test_get_remotes(git_repo: GitProject):
    assert "origin" in git_repo.remotes()


@pytest.mark.parametrize(
    "repo_name,new_repo_url",
    [
        ["myrepo", "file:///apples"],
    ],
)
def test_set_remote(git_repo: GitProject, repo_name: str, new_repo_url: str):
    mynewremote = git_repo.set_remote(name=repo_name, url="file:///")

    assert "file:///" in mynewremote.fetch_url, "set_remote returns remote"

    assert isinstance(
        git_repo.remote(name=repo_name), GitRemote
    ), "remote() returns GitRemote"
    assert "file:///" in git_repo.remote(name=repo_name).fetch_url, "new value set"

    assert "myrepo" in git_repo.remotes(), ".remotes() returns new remote"

    with pytest.raises(
        exc.CommandError,
        match=f".*remote {repo_name} already exists.*",
    ):
        mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url)

    mynewremote = git_repo.set_remote(name="myrepo", url=new_repo_url, overwrite=True)

    assert (
        new_repo_url in git_repo.remote(name="myrepo").fetch_url
    ), "Running remove_set should overwrite previous remote"


def test_get_git_version(git_repo: GitProject):
    expected_version = git_repo.run(["--version"]).replace("git version ", "")
    assert git_repo.get_git_version()
    assert expected_version == git_repo.get_git_version()


def test_get_current_remote_name(git_repo: GitProject):
    assert git_repo.get_current_remote_name() == "origin"

    new_branch = "another-branch-with-no-upstream"
    git_repo.run(["checkout", "-B", new_branch])
    assert (
        git_repo.get_current_remote_name() == new_branch
    ), "branch w/o upstream should return branch only"

    new_remote_name = "new_remote_name"
    git_repo.set_remote(
        name=new_remote_name, url=f"file://{git_repo.dir}", overwrite=True
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


def test_GitRemote_from_stdout():
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
    }.items() <= GitStatus.from_stdout(FIXTURE_A).to_dict().items()


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
def test_GitRemote__from_stdout_b(fixture: str, expected_result: dict):
    assert (
        GitStatus.from_stdout(textwrap.dedent(fixture)).to_dict().items()
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
def test_GitRemote__from_stdout_c(fixture: str, expected_result: dict):
    assert (
        expected_result.items()
        <= GitStatus.from_stdout(textwrap.dedent(fixture)).to_dict().items()
    )


def test_repo_git_remote_checkout(
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
):
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitProject(dir=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()
