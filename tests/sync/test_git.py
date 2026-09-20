"""Tests for libvcs GitSync."""

from __future__ import annotations

import datetime
import os
import pathlib
import random
import shutil
import subprocess
import textwrap
import time
import typing as t
from collections.abc import Callable

import pytest

from libvcs import GitOptions, exc
from libvcs._internal.run import run
from libvcs._internal.shortcuts import create_project
from libvcs.cmd.git_filter import Auto, BlobNone
from libvcs.sync.base import SyncPolicy, SyncResult, SyncTarget
from libvcs.sync.git import (
    GitRemote,
    GitStatus,
    GitSync,
    convert_pip_url as git_convert_pip_url,
)

if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from libvcs.pytest_plugin import CreateRepoFn, GitCommitEnvVars

if not shutil.which("git"):
    pytestmark = pytest.mark.skip(reason="git is not available")


ProjectTestFactory = Callable[..., GitSync]
ProjectTestFactoryLazyKwargs = Callable[..., dict[str, str]]
ProjectTestFactoryRemoteLazyExpected = Callable[..., dict[str, GitRemote]]


def test_obtain_reports_clone_failure(tmp_path: pathlib.Path) -> None:
    """A missing remote must fail at clone, before submodule or remote setup."""
    missing_remote = tmp_path / "missing-remote"
    repo = GitSync(url=str(missing_remote), path=tmp_path / "checkout")

    with pytest.raises(exc.CommandError) as error:
        repo.obtain()

    assert "git clone " in error.value.cmd
    assert str(missing_remote) in error.value.output
    assert "does not exist" in error.value.output


def test_git_position_distinguishes_attached_and_detached(git_repo: GitSync) -> None:
    """Position reports a moving branch or an immutable detached commit."""
    branch = git_repo.cmd.run(["symbolic-ref", "--short", "HEAD"]).strip()
    revision = git_repo.get_revision()
    position = git_repo.get_position()

    assert (position.ref_kind, position.ref_name) == ("branch", branch)
    assert position.revision == revision
    assert position.follows

    git_repo.cmd.run(["tag", branch], check_returncode=True)
    assert git_repo.get_position().ref_name == branch

    git_repo.cmd.run(["checkout", "--detach", "HEAD"], check_returncode=True)
    position = git_repo.get_position()

    assert (position.ref_kind, position.ref_name) == ("commit", revision)
    assert position.revision == revision
    assert not position.follows


def test_git_remotes_keep_fetch_and_push_destinations(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting a separate push URL never changes where the repository fetches."""
    monkeypatch.delenv("GIT_CONFIG", raising=False)
    fetch_url = git_remote_repo.as_uri()
    push_url = (tmp_path / "push.git").as_uri()
    repo = GitSync(
        url=fetch_url,
        path=tmp_path / "copy",
        remotes={"origin": GitRemote("origin", fetch_url, push_url)},
    )

    repo.obtain()

    assert repo.remote("origin") == GitRemote("origin", fetch_url, push_url)


def test_git_sync_rejects_invalid_filter_before_destination(
    tmp_path: pathlib.Path,
) -> None:
    """GitSync validates filters without touching the destination."""
    destination = tmp_path / "checkout"

    with pytest.raises(ValueError, match="limit"):
        GitSync(
            url="file:///unused",
            path=destination,
            options=GitOptions(filter={"kind": "blob:limit", "limit": False}),
        )

    assert not destination.exists()


def test_git_sync_accepts_auto_for_existing_repo_without_submodules(
    git_repo: GitSync,
) -> None:
    """Auto is valid when an existing checkout has no submodule workload."""
    repo = GitSync(
        url=git_repo.url,
        path=git_repo.path,
        options=GitOptions(filter=Auto()),
    )

    assert repo.options.filter == Auto()
    assert repo.cmd.submodules.ls() == []


def test_git_sync_auto_clone_skips_filter_when_no_submodules(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Auto reaches clone and is omitted from an empty submodule update."""
    repo = GitSync(
        url="https://example.com/repo.git",
        path=tmp_path / "checkout",
        options=GitOptions(filter=Auto()),
    )
    clone = mocker.patch.object(repo.cmd, "clone", return_value="")
    ls_files = mocker.patch.object(
        repo.cmd,
        "run",
        return_value="100644 deadbeef 0\t.gitmodules\0",
    )
    mocker.patch.object(repo.cmd.submodule, "init", return_value="")
    update = mocker.patch.object(repo.cmd.submodule, "update", return_value="")
    mocker.patch.object(repo, "set_remotes")

    repo.obtain()

    assert clone.call_args.kwargs["_filter"] == Auto()
    ls_files.assert_called_once_with(
        ["ls-files", "--stage", "-z"], check_returncode=True
    )
    assert update.call_args.kwargs["_filter"] is None


def test_git_sync_auto_clone_rejects_present_submodules(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Auto reports the unsupported submodule workload after cloning."""
    repo = GitSync(
        url="https://example.com/repo.git",
        path=tmp_path / "checkout",
        options=GitOptions(filter=Auto()),
    )
    clone = mocker.patch.object(repo.cmd, "clone", return_value="")
    mocker.patch.object(
        repo.cmd,
        "run",
        return_value="160000 deadbeef 0\tdeps/sub\0",
    )
    init = mocker.patch.object(repo.cmd.submodule, "init", return_value="")
    update = mocker.patch.object(repo.cmd.submodule, "update", return_value="")

    with pytest.raises(ValueError, match=r"auto.*submodule"):
        repo.obtain()

    clone.assert_called_once()
    init.assert_not_called()
    update.assert_not_called()


def test_git_sync_obtain_partial_clone(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    git_commit_envvars: GitCommitEnvVars,
) -> None:
    """GitSync obtains history while leaving old blobs promised by the remote."""
    monkeypatch.delenv("GIT_CONFIG", raising=False)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    remote = tmp_path / "remote"
    run(["git", "init", str(remote)], env=git_commit_envvars)
    run(["git", "config", "uploadpack.allowFilter", "true"], cwd=remote)
    run(["git", "config", "uploadpack.allowAnySHA1InWant", "true"], cwd=remote)
    tracked = remote / "tracked.txt"
    for version in range(3):
        tracked.write_text(f"version {version}\n", encoding="utf-8")
        run(["git", "add", "tracked.txt"], cwd=remote, env=git_commit_envvars)
        run(
            ["git", "commit", "-m", f"version {version}"],
            cwd=remote,
            env=git_commit_envvars,
        )

    destination = tmp_path / "checkout"
    repo = GitSync(
        url=remote.as_uri(),
        path=destination,
        options=GitOptions(filter=BlobNone()),
    )
    repo.obtain()

    assert (
        repo.cmd.run(["config", "--get", "remote.origin.partialclonefilter"], trim=True)
        == "blob:none"
    )
    assert repo.cmd.run(["rev-list", "--count", "HEAD"], trim=True) == "3"
    missing = repo.cmd.run(["rev-list", "--objects", "--missing=print", "--all"])
    assert any(line.startswith("?") for line in missing.splitlines())
    assert (destination / "tracked.txt").read_text(encoding="utf-8") == "version 2\n"
    assert repo.cmd.run(["ls-remote", "origin"]).strip()


@pytest.mark.parametrize("depth", [None, 3])
def test_git_sync_obtain_forwards_filter_to_submodule(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    git_commit_envvars: GitCommitEnvVars,
    depth: int | None,
) -> None:
    """GitSync creates submodules as partial clones with the configured filter."""
    monkeypatch.delenv("GIT_CONFIG", raising=False)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")

    submodule_remote = tmp_path / "submodule-remote"
    run(["git", "init", str(submodule_remote)], env=git_commit_envvars)
    run(["git", "config", "uploadpack.allowFilter", "true"], cwd=submodule_remote)
    run(
        ["git", "config", "uploadpack.allowAnySHA1InWant", "true"],
        cwd=submodule_remote,
    )
    submodule_file = submodule_remote / "data.txt"
    for version in range(3):
        submodule_file.write_text(f"submodule data {version}\n", encoding="utf-8")
        run(["git", "add", "data.txt"], cwd=submodule_remote, env=git_commit_envvars)
        run(
            ["git", "commit", "-m", f"submodule data {version}"],
            cwd=submodule_remote,
            env=git_commit_envvars,
        )

    run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            submodule_remote.as_uri(),
            "nested",
        ],
        cwd=submodule_remote,
        env=git_commit_envvars,
    )
    run(
        ["git", "commit", "-m", "add nested submodule"],
        cwd=submodule_remote,
        env=git_commit_envvars,
    )

    parent_remote = tmp_path / "parent-remote"
    run(["git", "init", str(parent_remote)], env=git_commit_envvars)
    run(["git", "config", "uploadpack.allowFilter", "true"], cwd=parent_remote)
    run(
        ["git", "config", "uploadpack.allowAnySHA1InWant", "true"],
        cwd=parent_remote,
    )
    run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            submodule_remote.as_uri(),
            "deps/sub",
        ],
        cwd=parent_remote,
        env=git_commit_envvars,
    )
    run(
        ["git", "commit", "-m", "add submodule"],
        cwd=parent_remote,
        env=git_commit_envvars,
    )

    destination = tmp_path / "checkout"
    repo = GitSync(
        url=parent_remote.as_uri(),
        path=destination,
        options=GitOptions(
            depth=depth,
            filter=[BlobNone(), {"kind": "tree", "depth": 2}],
        ),
    )
    repo.obtain()

    assert (destination / "deps" / "sub" / "data.txt").read_text(
        encoding="utf-8"
    ) == "submodule data 2\n"
    assert (destination / "deps" / "sub" / "nested" / "data.txt").read_text(
        encoding="utf-8"
    ) == "submodule data 2\n"
    assert run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=destination / "deps" / "sub",
    ).strip() == str(depth or 4)
    submodule_git_dir = destination / ".git" / "modules" / "deps" / "sub"
    assert (
        run(
            ["git", "config", "--get", "remote.origin.partialclonefilter"],
            cwd=submodule_git_dir,
        ).strip()
        == "combine:blob:none+tree:2"
    )
    missing = run(
        ["git", "rev-list", "--objects", "--missing=print", "--all"],
        cwd=destination / "deps" / "sub",
    )
    assert any(line.startswith("?") for line in missing.splitlines())

    submodule_file.write_text("submodule data 3\n")
    run(
        ["git", "commit", "-am", "submodule update"],
        cwd=submodule_remote,
        env=git_commit_envvars,
    )
    run(["git", "submodule", "update", "--remote", "deps/sub"], cwd=parent_remote)
    run(
        ["git", "commit", "-am", "advance submodule"],
        cwd=parent_remote,
        env=git_commit_envvars,
    )
    result = repo.update_repo()
    assert result.ok, result.errors
    assert (
        destination / "deps" / "sub" / "data.txt"
    ).read_text() == "submodule data 3\n"


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda bare_dir, tmp_path, **kwargs: {
                "url": bare_dir.as_uri(),
                "path": tmp_path / "obtaining a bare repo",
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

    test_repo_revision = run(["git", "rev-parse", "HEAD"], cwd=git_remote_repo).strip()

    assert git_repo.get_revision() == test_repo_revision
    assert (tmp_path / "myrepo").exists()


def test_git_options_depth_one_creates_shallow_clone(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
) -> None:
    """A depth-one option preserves the former shallow-clone behavior."""
    git_repo = GitSync(
        url=git_remote_repo.as_uri(),
        path=tmp_path / "myrepo",
        options=GitOptions(depth=1),
    )
    assert git_repo.options.depth == 1
    git_repo.obtain()

    is_shallow = run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=tmp_path / "myrepo",
    )
    assert is_shallow.strip() == "true"


class DepthFixture(t.NamedTuple):
    """Parameters for :func:`test_obtain_honors_clone_depth`."""

    test_id: str
    sync_kwargs: dict[str, t.Any]
    expected_count: int
    expected_shallow: bool


DEPTH_FIXTURES: list[DepthFixture] = [
    DepthFixture(
        test_id="full-clone",
        sync_kwargs={},
        expected_count=6,
        expected_shallow=False,
    ),
    DepthFixture(
        test_id="depth-1",
        sync_kwargs={"options": GitOptions(depth=1)},
        expected_count=1,
        expected_shallow=True,
    ),
    DepthFixture(
        test_id="depth-3",
        sync_kwargs={"options": GitOptions(depth=3)},
        expected_count=3,
        expected_shallow=True,
    ),
]


@pytest.mark.parametrize(
    list(DepthFixture._fields),
    DEPTH_FIXTURES,
    ids=[test.test_id for test in DEPTH_FIXTURES],
)
def test_obtain_honors_clone_depth(
    tmp_path: pathlib.Path,
    create_git_remote_repo: CreateRepoFn,
    git_commit_envvars: GitCommitEnvVars,
    test_id: str,
    sync_kwargs: dict[str, t.Any],
    expected_count: int,
    expected_shallow: bool,
) -> None:
    """obtain() clones at the requested depth; an explicit depth wins.

    The ``file://`` URL matters: git ignores ``--depth`` for local-path clones.
    """
    remote_repo = create_git_remote_repo()
    env = os.environ.copy()
    env.update(git_commit_envvars)
    for i in range(1, 7):
        (remote_repo / "f.txt").write_text(str(i))
        run(["git", "add", "f.txt"], cwd=remote_repo, env=env)
        run(["git", "commit", "-m", f"c{i}"], cwd=remote_repo, env=env)

    checkout = tmp_path / "checkout"
    git_repo = GitSync(url=remote_repo.as_uri(), path=checkout, **sync_kwargs)
    git_repo.obtain()

    commit_count = run(["git", "rev-list", "--count", "HEAD"], cwd=checkout)
    is_shallow = run(["git", "rev-parse", "--is-shallow-repository"], cwd=checkout)
    assert int(commit_count) == expected_count
    assert is_shallow.strip() == ("true" if expected_shallow else "false")


@pytest.mark.parametrize(
    # Postpone evaluation of options so fixture variables can interpolate
    ("constructor", "lazy_constructor_options"),
    [
        (
            GitSync,
            lambda git_remote_repo, tmp_path, **kwargs: {
                "url": git_remote_repo.as_uri(),
                "path": tmp_path / "myrepo",
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

    original = git_repo.get_position()
    assert git_repo.update_repo().ok
    assert git_repo.get_position() == original
    git_repo.rev = "HEAD"
    assert git_repo.update_repo().ok
    assert git_repo.get_position().revision == original.revision
    assert git_repo.get_position().ref_kind == "commit"


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
    create_git_remote_bare_repo: CreateRepoFn,
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

    head = git_repo.get_revision()
    before = git_repo.run(["status", "--porcelain=v2", "-z"])
    result = git_repo.update_repo()
    assert result.ok is not (has_untracked_files or needs_stash)
    if has_untracked_files or needs_stash:
        assert git_repo.get_revision() == head
        assert git_repo.run(["status", "--porcelain=v2", "-z"]) == before


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
    create_git_remote_repo: CreateRepoFn,
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
    assert git_repo.cmd.remotes.show().strip() == "origin"
    git_origin = git_repo.cmd.remotes.get(remote_name="origin")
    assert git_origin is not None
    assert "origin" in git_origin.show()
    assert "origin" in git_origin.show(no_query_remotes=True)
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
    expected_version = git_repo.run(["--version"]).replace("git version ", "").strip()
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
    create_git_remote_repo: CreateRepoFn,
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


def test_update_repo_success_returns_sync_result(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
) -> None:
    """Test that a successful update_repo() returns SyncResult with ok=True."""
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )
    git_repo.obtain()

    # Make an initial commit so rev-list HEAD succeeds
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text("content", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "initial commit"])
    git_repo.run(["push"])

    result = git_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is True
    assert result.errors == []
    assert bool(result) is True


def test_update_repo_fetch_failure_returns_sync_result(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
) -> None:
    """Test that a fetch failure in update_repo() returns SyncResult with error."""
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )
    git_repo.obtain()

    # Make a commit and push so the repo has a valid HEAD
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text("content", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "a commit"])
    git_repo.run(["push"])

    # Make another commit, push, then reset to create a "behind" state
    another_file = git_repo.path / "another_file"
    another_file.write_text("more content", encoding="utf-8")
    git_repo.run(["add", str(another_file)])
    git_repo.run(["commit", "-m", "second commit"])
    git_repo.run(["push"])
    git_repo.run(["reset", "--hard", "HEAD^"])

    # Delete the remote directory to cause a fetch failure
    shutil.rmtree(git_server)

    result = git_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert bool(result) is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "fetch"
    assert result.errors[0].exception is not None
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_update_repo_checkout_failure_returns_sync_result(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
) -> None:
    """Test that a checkout failure in update_repo() returns SyncResult with error."""
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )
    git_repo.obtain()

    # Make a commit and push so the repo has a valid HEAD
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text("content", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "initial commit"])
    git_repo.run(["push"])

    # Set rev to a nonexistent branch to trigger a checkout failure
    git_repo.rev = "nonexistent-branch"

    result = git_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert bool(result) is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "target"
    assert result.errors[0].exception is not None
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_update_repo_rev_list_head_failure_returns_sync_result(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
) -> None:
    """update_repo() records rev-list HEAD failure in SyncResult."""
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )
    git_repo.obtain()

    # Make a commit and push so the repo has a valid HEAD
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text("content", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "initial commit"])
    git_repo.run(["push"])

    # Corrupt HEAD so rev-list HEAD fails
    head_file = git_repo.path / ".git" / "HEAD"
    head_file.write_text("ref: refs/heads/nonexistent\n")

    result = git_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert bool(result) is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "precondition"
    assert result.errors[0].exception is not None
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_update_repo_obtain_failure_recorded(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Test that obtain failure when .git is missing is recorded in SyncResult.

    When .git does not exist, update_repo() calls obtain(). If the clone
    fails, the error is recorded as ``obtain``.
    """
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )

    # Mock obtain to raise CommandError (simulates a clone failure)
    mocker.patch.object(
        git_repo,
        "obtain",
        side_effect=exc.CommandError(
            output="fatal: repository not found",
            returncode=128,
            cmd="git clone",
        ),
    )

    result = git_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "obtain"
    assert result.errors[0].exception is not None
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_update_repo_set_remotes_failure_recorded(
    create_git_remote_bare_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Test that set_remotes failure is recorded in SyncResult.

    When ``set_remotes=True`` is passed and ``set_remotes()`` raises
    CommandError, the error is recorded as ``set-remotes``.
    """
    git_server = create_git_remote_bare_repo()
    git_repo = GitSync(
        path=tmp_path / "myrepo",
        url=git_server.as_uri(),
    )
    git_repo.obtain()

    # Make a commit and push so the repo has a valid HEAD
    initial_file = git_repo.path / "initial_file"
    initial_file.write_text("content", encoding="utf-8")
    git_repo.run(["add", str(initial_file)])
    git_repo.run(["commit", "-m", "initial commit"])
    git_repo.run(["push"])

    mocker.patch.object(
        git_repo,
        "set_remotes",
        side_effect=exc.CommandError(
            output="fatal: remote error",
            returncode=1,
            cmd="git remote set-url",
        ),
    )

    result = git_repo.update_repo(set_remotes=True)

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "set-remotes"
    assert result.errors[0].exception is not None
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_sync_result_multiple_errors() -> None:
    """Test that SyncResult can accumulate multiple errors."""
    result = SyncResult()
    assert result.ok is True

    result.add_error(step="fetch", message="network error")
    assert result.ok is False
    assert len(result.errors) == 1

    result.add_error(step="checkout", message="branch not found")
    assert len(result.errors) == 2
    assert result.errors[0].step == "fetch"
    assert result.errors[1].step == "checkout"


def test_remote_is_fast_for_repos_with_many_refs(
    git_repo: GitSync,
    tmp_path: pathlib.Path,
) -> None:
    """``GitSync.remote`` stays O(1) even when the repo has thousands of refs.

    The prior implementation called ``git remote show -n origin`` whose output
    enumerates every remote-tracking ref. For repositories like openai/codex
    (2,400+ branches) that stream of lines piped through the subprocess
    progress callback produced the appearance of a hang during vcspull sync.

    This test seeds synthetic refs/remotes/origin/branch-N entries and asserts
    that ``remote('origin')`` returns promptly. A generous 5-second budget is
    enough to catch the pathological old path (many seconds on WSL2) without
    flaking on slow CI. Refs are batched through ``git update-ref --stdin``
    (one subprocess) instead of one invocation per ref so the test setup
    doesn't dominate suite duration.
    """
    # Point origin at a commit we already have so fake refs don't dangle.
    head_sha = run(["git", "rev-parse", "HEAD"], cwd=git_repo.path).strip()

    # Seed 500 fake remote-tracking refs in a single ``git update-ref`` call;
    # the cumulative count is what would blow up ``git remote show -n``.
    stdin_input = "".join(
        f"update refs/remotes/origin/fake-branch-{i:04d} {head_sha}\n"
        for i in range(500)
    )
    subprocess.run(
        ["git", "-C", str(git_repo.path), "update-ref", "--stdin"],
        input=stdin_input,
        text=True,
        check=True,
    )

    started = time.monotonic()
    remote = git_repo.remote("origin")
    elapsed = time.monotonic() - started

    assert remote is not None
    assert remote.fetch_url, "fetch URL must be populated"
    assert elapsed < 5.0, f"remote() too slow: {elapsed:.2f}s with 500 fake refs"


def test_remote_swallows_libvcs_exception(
    git_repo: GitSync,
    mocker: MockerFixture,
) -> None:
    """``GitSync.remote`` returns ``None`` when ``git remote -v`` fails.

    The pre-rewrite implementation wrapped the underlying subprocess call
    in ``try / except LibVCSException`` so a corrupt config or a locked
    ``.git/config`` did not crash a ``vcspull sync``. The new path must
    preserve that resilience -- callers should still see ``None`` rather
    than a raised exception.
    """
    mocker.patch.object(
        git_repo.cmd.remotes,
        "get",
        side_effect=exc.CommandError(
            output="fatal: bad config",
            returncode=128,
            cmd="git remote --verbose",
        ),
    )

    assert git_repo.remote("origin") is None


def test_update_repo_rejects_option_like_rev(
    git_repo: GitSync,
    tmp_path: pathlib.Path,
) -> None:
    """Reject a revision that git would parse as an option.

    A `rev` reaches `git rev-list <commit>`, which has no end-of-options `--`
    before the operand. A value such as `--output=<file>` is parsed there as
    the diff `--output` option, whose callback truncates the file during
    option parsing -- arbitrary file destruction from a config-supplied rev.
    """
    victim = tmp_path / "victim.txt"
    victim.write_text("important\n")
    git_repo.rev = f"--output={victim}"

    result = git_repo.update_repo()

    assert not result.ok, "update_repo() should fail for an option-like rev"
    assert victim.read_text() == "important\n", "Prevent rev argument injection"


def _preservation_update(repo: GitSync) -> str:
    """Create a fetched successor while leaving the checkout at its base."""
    base = repo.get_revision()
    (repo.path / "upstream.txt").write_text("upstream\n")
    repo.run(["add", "upstream.txt"])
    repo.run(["commit", "-m", "upstream"])
    repo.run(
        ["push", "--set-upstream", "origin", f"HEAD:preservation-{repo.path.name}"]
    )
    repo.run(["reset", "--hard", base])
    return base


def test_preservation_abort_before_capture(git_repo: GitSync) -> None:
    """Default abort leaves dirty contents and HEAD untouched."""
    base = _preservation_update(git_repo)
    (git_repo.path / "local.txt").write_text("local\n")
    result = git_repo.update_repo()
    assert not result.ok
    assert result.update_state == "not-started"
    assert git_repo.get_revision() == base
    assert (git_repo.path / "local.txt").read_text() == "local\n"


@pytest.mark.parametrize("detached", [False, True])
def test_preservation_recovers_index_offline(
    git_repo: GitSync, tmp_path: pathlib.Path, detached: bool
) -> None:
    """A retained stash recovers both index and working contents at the saved base."""
    base = _preservation_update(git_repo)
    target = None
    if detached:
        target = SyncTarget(commit=git_repo.run(["rev-parse", "@{upstream}"]).strip())
        git_repo.run(["checkout", "--detach", base])
    original = git_repo.get_position()
    local = git_repo.path / "local.txt"
    local.write_text("staged\n")
    git_repo.run(["add", "local.txt"])
    local.write_text("unstaged\n")
    result = git_repo.update_repo(target=target, policy=SyncPolicy(dirty="preserve"))
    assert result.ok, result.errors
    assert result.preservation_state == "restored"
    assert result.recovery is not None
    assert git_repo.run(["show", ":local.txt"]) == "staged\n"
    assert local.read_text() == "unstaged\n"
    git_repo.run(["remote", "set-url", "origin", str(tmp_path / "absent")])
    destination = tmp_path / "recovered"
    recovered = git_repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    assert GitSync(url=git_repo.url, path=destination).get_position() == original
    assert run(["git", "rev-parse", "HEAD"], cwd=destination).strip() == base
    assert run(["git", "show", ":local.txt"], cwd=destination) == "staged\n"
    assert (destination / "local.txt").read_text() == "unstaged\n"
    assert git_repo.list_recoveries()[0].recovery == result.recovery
    git_repo.release_changes(result.recovery)
    assert git_repo.list_recoveries() == ()


def test_preservation_drift_keep_leaves_dirty_branch(git_repo: GitSync) -> None:
    """Keep policy does not capture or switch a differing configured branch."""
    _preservation_update(git_repo)
    git_repo.run(["branch", "other", "@{upstream}"])
    (git_repo.path / "local.txt").write_text("local\n")
    original = git_repo.get_position()
    result = git_repo.update_repo(
        target=SyncTarget(branch="other"), policy=SyncPolicy(drift="keep")
    )
    assert result.ok, result.errors
    assert git_repo.get_position() == original
    assert result.recovery is None


def test_preservation_divergence_retains_local_commit(git_repo: GitSync) -> None:
    """Follow refuses divergent histories before capturing dirty changes."""
    _preservation_update(git_repo)
    (git_repo.path / "commit.txt").write_text("local commit\n")
    git_repo.run(["add", "commit.txt"])
    git_repo.run(["commit", "-m", "local"])
    head = git_repo.get_revision()
    (git_repo.path / "local.txt").write_text("dirty\n")
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is None
    assert git_repo.get_revision() == head
    assert (git_repo.path / "local.txt").read_text() == "dirty\n"


@pytest.mark.parametrize("selector", ["branch", "tag", "commit"])
def test_preservation_equal_alias_keeps_attachment(
    git_repo: GitSync, selector: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Equal object IDs do not warn or change attachment under drift keep/warn."""
    git_repo.run(["branch", "alias"])
    git_repo.run(["tag", "alias"])
    target = SyncTarget(
        **{selector: git_repo.get_revision() if selector == "commit" else "alias"}
    )
    original = git_repo.get_position()
    for drift in ("keep", "warn"):
        result = git_repo.update_repo(target=target, policy=SyncPolicy(drift=drift))
        assert result.ok, result.errors
        assert git_repo.get_position() == original
    assert not [record for record in caplog.records if record.name == "libvcs.sync.git"]


@pytest.mark.parametrize(
    "fault", ["capture", "update", "restore", "inspection", "publication"]
)
def test_preservation_retains_token_after_fault(
    git_repo: GitSync,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    tmp_path: pathlib.Path,
) -> None:
    """Every failure after capture retains recovery and the first operation error."""
    from libvcs._internal import preservation

    _preservation_update(git_repo)
    (git_repo.path / "local.txt").write_text("local\n")
    real_run = git_repo.cmd.run
    real_read = git_repo._read_git

    def fail_command(args: t.Any, **kwargs: t.Any) -> str:
        if (fault == "update" and args[0] == "merge") or (
            fault == "restore" and args[:2] == ["stash", "apply"]
        ):
            raise exc.CommandError(output=fault, cmd=args, returncode=1)
        output = real_run(args, **kwargs)
        if fault == "capture" and args[:2] == ["stash", "push"]:
            raise exc.CommandError(output=fault, cmd=args, returncode=1)
        return output

    def fail_read(args: list[str], **kwargs: t.Any) -> str:
        if fault == "inspection" and args[:2] == ["ls-files", "--unmerged"]:
            raise exc.CommandError(output=fault, cmd=args, returncode=1)
        return real_read(args, **kwargs)

    def fail_finish(*args: t.Any, **kwargs: t.Any) -> None:
        message = "publication"
        raise OSError(message)

    with monkeypatch.context() as patch:
        patch.setattr(git_repo.cmd, "run", fail_command)
        patch.setattr(git_repo, "_read_git", fail_read)
        if fault == "publication":
            patch.setattr(preservation.RecoveryStore, "finish", fail_finish)
        result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is not None
    assert result.errors[0].step == fault
    assert git_repo.list_recoveries()[0].recovery == result.recovery
    recovered = git_repo.recover_changes(
        result.recovery, destination=tmp_path / "recovered"
    )
    assert recovered.ok, recovered.errors
    assert (tmp_path / "recovered" / "local.txt").read_text() == "local\n"


@pytest.mark.parametrize("collision", [False, True])
def test_preservation_ignored_output(git_repo: GitSync, collision: bool) -> None:
    """Ignored output only blocks updates that write an overlapping path."""
    base = _preservation_update(git_repo)
    (git_repo.path / ".git" / "info" / "exclude").write_text("*.txt\n")
    output = git_repo.path / ("upstream.txt" if collision else "build.txt")
    output.write_text("ignored\n")
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.ok is not collision, result.errors
    assert output.read_text() == "ignored\n"
    assert (git_repo.get_revision() == base) is collision
    assert result.recovery is None


@pytest.mark.parametrize("kind", ["text", "binary", "unknown", "disjoint"])
def test_preservation_native_merge_outcomes(
    git_repo: GitSync, kind: str, tmp_path: pathlib.Path
) -> None:
    """Native indexed apply reports collisions and merges disjoint text changes."""
    file = git_repo.path / "shared"
    if kind != "unknown":
        file.write_bytes(
            b"base\0binary"
            if kind == "binary"
            else b"first\n" + b"middle\n" * 12 + b"last\n"
        )
        git_repo.run(["add", "shared"])
        git_repo.run(["commit", "-m", "base"])
    base = git_repo.get_revision()
    file.write_bytes(
        b"upstream\0binary"
        if kind == "binary"
        else b"upstream\n" + b"middle\n" * 12 + b"last\n"
    )
    git_repo.run(["add", "shared"])
    git_repo.run(["commit", "-m", "upstream"])
    git_repo.run(
        ["push", "--set-upstream", "origin", f"HEAD:merge-{git_repo.path.name}"]
    )
    git_repo.run(["reset", "--hard", base])
    local = (
        b"local\0binary"
        if kind == "binary"
        else (
            b"first\n" + b"middle\n" * 12 + b"local\n"
            if kind == "disjoint"
            else b"local\n"
        )
    )
    file.write_bytes(local)
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.recovery is not None
    assert result.ok is (kind == "disjoint"), result.errors
    assert result.update_state == "completed"
    if kind == "disjoint":
        assert file.read_bytes().startswith(b"upstream\n")
        assert file.read_bytes().endswith(b"local\n")
    recovered = git_repo.recover_changes(
        result.recovery, destination=tmp_path / "recovered"
    )
    assert recovered.ok, recovered.errors
    assert (tmp_path / "recovered" / "shared").read_bytes() == local
    assert run(["git", "rev-parse", "HEAD"], cwd=tmp_path / "recovered").strip() == base


def test_preservation_unchanged_preserves_existing_stash(git_repo: GitSync) -> None:
    """No-change updates never adopt or remove a caller-owned stash."""
    (git_repo.path / "caller").write_text("caller\n")
    git_repo.run(["stash", "push", "-u", "-m", "caller"])
    before = git_repo.run(["stash", "list", "--format=%H"])
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.ok, result.errors
    assert result.recovery is None
    assert git_repo.run(["stash", "list", "--format=%H"]) == before


@pytest.mark.parametrize(
    "busy", ["MERGE_HEAD", "rebase-merge", "index.lock", "nested", "submodule"]
)
def test_preservation_native_preconditions(git_repo: GitSync, busy: str) -> None:
    """Native activity and independent repositories fail before fetch or capture."""
    _preservation_update(git_repo)
    if busy == "nested":
        (git_repo.path / "nested" / ".git").mkdir(parents=True)
    elif busy == "submodule":
        git_repo.run(
            [
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{git_repo.get_revision()},module",
            ]
        )
    elif busy == "rebase-merge":
        (git_repo.path / ".git" / busy).mkdir()
    else:
        (git_repo.path / ".git" / busy).write_text(git_repo.get_revision())
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.errors[0].step == "precondition"
    assert result.recovery is None


def test_preservation_rename_paths(git_repo: GitSync) -> None:
    """NUL status preserves both rename paths including whitespace and newlines."""
    original = git_repo.path / "old\nname"
    original.write_text("contents")
    git_repo.run(["add", "--", original.name])
    git_repo.run(["commit", "-m", "original"])
    git_repo.run(["mv", "--", original.name, "new name"])
    assert set(git_repo._dirty_paths()) == {"old\nname", "new name"}


def test_preservation_interrupted_save_is_discoverable(
    git_repo: GitSync, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """An interrupted save retains discoverable intent and native stash identity."""
    _preservation_update(git_repo)
    (git_repo.path / "local.txt").write_text("local\n")
    real_run = git_repo.cmd.run

    def interrupt(args: t.Any, **kwargs: t.Any) -> str:
        output = real_run(args, **kwargs)
        if args[:2] == ["stash", "push"]:
            raise KeyboardInterrupt
        return output

    with monkeypatch.context() as patch:
        patch.setattr(git_repo.cmd, "run", interrupt)
        with pytest.raises(KeyboardInterrupt):
            git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    interrupted = git_repo.list_recoveries()[0]
    assert not interrupted.ok
    assert interrupted.recovery is not None
    assert interrupted.errors[0].step == "interrupted"
    blocked = git_repo.update_repo()
    assert not blocked.ok
    assert blocked.recovery == interrupted.recovery
    recovered = git_repo.recover_changes(
        interrupted.recovery, destination=tmp_path / "recovered"
    )
    assert recovered.ok, recovered.errors
    assert (tmp_path / "recovered" / "local.txt").read_text() == "local\n"


def test_preservation_release_keeps_caller_stash(git_repo: GitSync) -> None:
    """Release identifies the owned stash beneath a newer caller stash."""
    _preservation_update(git_repo)
    (git_repo.path / "local.txt").write_text("local\n")
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.ok, result.errors
    assert result.recovery is not None
    git_repo.run(["stash", "push", "-u", "-m", "caller"])
    caller = git_repo.run(["rev-parse", "refs/stash"])
    git_repo.release_changes(result.recovery)
    assert git_repo.run(["rev-parse", "refs/stash"]) == caller
    assert git_repo.run(["stash", "list", "--format=%H"]) == caller


def test_preservation_missing_promised_objects_fail_offline(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    git_commit_envvars: GitCommitEnvVars,
) -> None:
    """Partial history recovery refuses absent blobs without contacting the promisor."""
    monkeypatch.delenv("GIT_CONFIG", raising=False)
    remote = tmp_path / "remote"
    run(["git", "init", str(remote)], env=git_commit_envvars)
    run(["git", "config", "uploadpack.allowFilter", "true"], cwd=remote)
    for version in range(3):
        (remote / "tracked").write_text(f"version {version}\n")
        run(["git", "add", "tracked"], cwd=remote)
        run(
            ["git", "commit", "-m", f"version {version}"],
            cwd=remote,
            env=git_commit_envvars,
        )
    repo = GitSync(
        url=remote.as_uri(),
        path=tmp_path / "checkout",
        options=GitOptions(filter=BlobNone()),
    )
    repo.obtain()
    (remote / "upstream").write_text("upstream\n")
    run(["git", "add", "upstream"], cwd=remote)
    run(["git", "commit", "-m", "upstream"], cwd=remote, env=git_commit_envvars)
    (repo.path / "local").write_text("local\n")
    result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.ok, result.errors
    assert result.recovery is not None
    remote.rename(tmp_path / "offline-remote")
    destination = tmp_path / "recovered"
    recovered = repo.recover_changes(result.recovery, destination=destination)
    assert not recovered.ok
    assert recovered.recovery == result.recovery
    assert not destination.exists()
    assert repo.list_recoveries()[0].recovery == result.recovery


def test_preservation_linked_checkout_shares_interruption_guard(
    git_repo: GitSync, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interrupted operations block another worktree sharing the stash namespace."""
    _preservation_update(git_repo)
    linked = tmp_path / "linked"
    git_repo.run(["worktree", "add", "-b", "linked", str(linked)])
    other = GitSync(url=git_repo.url, path=linked)
    (git_repo.path / "local").write_text("local\n")
    real_run = git_repo.cmd.run

    def interrupt(args: t.Any, **kwargs: t.Any) -> str:
        output = real_run(args, **kwargs)
        if args[:2] == ["stash", "push"]:
            raise KeyboardInterrupt
        return output

    with monkeypatch.context() as patch:
        patch.setattr(git_repo.cmd, "run", interrupt)
        with pytest.raises(KeyboardInterrupt):
            git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    result = other.update_repo()
    assert not result.ok
    assert result.recovery == git_repo.list_recoveries()[0].recovery
    assert result.errors[0].step == "interrupted"


def test_preservation_follow_attaches_equal_branch(git_repo: GitSync) -> None:
    """Follow may attach an explicit equal-OID branch to govern future updates."""
    git_repo.run(["branch", "alias"])
    result = git_repo.update_repo(target=SyncTarget(branch="alias"))
    assert result.ok, result.errors
    assert git_repo.get_position().ref_name == "alias"


def test_preservation_discard_preserves_commits_and_ignored(git_repo: GitSync) -> None:
    """Explicit discard removes ordinary dirt without rewriting local commits."""
    _preservation_update(git_repo)
    git_repo.run(["merge", "--ff-only", "@{upstream}"])
    (git_repo.path / "commit").write_text("local commit\n")
    git_repo.run(["add", "commit"])
    git_repo.run(["commit", "-m", "local"])
    head = git_repo.get_revision()
    (git_repo.path / "commit").write_text("dirt\n")
    (git_repo.path / "unknown").write_text("unknown\n")
    (git_repo.path / ".git" / "info" / "exclude").write_text("ignored\n")
    (git_repo.path / "ignored").write_text("ignored\n")
    result = git_repo.update_repo(policy=SyncPolicy(dirty="discard"))
    assert result.ok, result.errors
    assert git_repo.get_revision() == head
    assert (git_repo.path / "commit").read_text() == "local commit\n"
    assert not (git_repo.path / "unknown").exists()
    assert (git_repo.path / "ignored").read_text() == "ignored\n"


def test_preservation_phase_write_stops_update(
    git_repo: GitSync, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unpublished updating phase cannot start the native update."""
    from libvcs._internal import preservation

    base = _preservation_update(git_repo)
    (git_repo.path / "local").write_text("local\n")
    phase = preservation.RecoveryStore.phase

    def fail_updating(
        store: preservation.RecoveryStore,
        token: t.Any,
        record: t.Any,
        value: str,
    ) -> None:
        if value == "updating":
            message = "updating publication failed"
            raise OSError(message)
        phase(store, token, record, value)

    monkeypatch.setattr(preservation.RecoveryStore, "phase", fail_updating)
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is not None
    assert result.update_state == "not-started"
    assert git_repo.get_revision() == base
    assert (git_repo.path / "local").read_text() == "local\n"


def test_preservation_clean_submodule_failure_is_reported(
    git_repo: GitSync, mocker: MockerFixture
) -> None:
    """Clean update reports native submodule errors without discarding checkout data."""
    mocker.patch.object(
        git_repo.cmd.submodule,
        "update",
        side_effect=exc.CommandError(
            output="submodule failure", returncode=1, cmd="git submodule update"
        ),
    )
    result = git_repo.update_repo()
    assert not result.ok
    assert result.errors[0].step == "submodule-update"


def test_preservation_ignored_obstruction_at_capture_base(git_repo: GitSync) -> None:
    """Native stash cleanup cannot overwrite ignored obstructions at the old base."""
    directory = git_repo.path / "directory"
    directory.mkdir()
    (directory / "tracked").write_text("tracked\n")
    git_repo.run(["add", "directory"])
    git_repo.run(["commit", "-m", "base directory"])
    base = _preservation_update(git_repo)
    (directory / "tracked").unlink()
    directory.rmdir()
    (git_repo.path / ".git" / "info" / "exclude").write_text("directory\n")
    directory.write_text("ignored obstruction\n")
    result = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is None
    assert git_repo.get_revision() == base
    assert directory.read_text() == "ignored obstruction\n"


def test_preservation_damaged_record_retains_token(git_repo: GitSync) -> None:
    """Damaged retained records block updates with their discoverable token."""
    _preservation_update(git_repo)
    (git_repo.path / "local").write_text("local\n")
    saved = git_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert saved.ok, saved.errors
    assert saved.recovery is not None
    (pathlib.Path(saved.recovery.location) / "operation.json").write_text("{")
    result = git_repo.update_repo()
    assert not result.ok
    assert result.recovery == saved.recovery
    assert result.update_state == "unknown"
