"""Tests for typed backend synchronization options."""

from __future__ import annotations

import dataclasses
import inspect
import pathlib
import typing as t

import pytest

from libvcs import (
    BaseSync,
    GitOptions,
    GitSync,
    HgOptions,
    HgSync,
    SvnOptions,
    SvnSync,
    SyncTarget,
)
from libvcs._internal.shortcuts import create_project
from libvcs.cmd.git_filter import BlobNone, filter_specs

if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("options_type", "field_names"),
    [
        (GitOptions, ["depth", "filter", "tls_verify"]),
        (HgOptions, ["ssh", "remote_cmd", "pull", "stream", "tls_verify"]),
        (
            SvnOptions,
            [
                "username",
                "password",
                "depth",
                "trust_server_cert",
                "ignore_externals",
            ],
        ),
    ],
)
def test_backend_options_expose_exact_config_fields(
    options_type: type[GitOptions | HgOptions | SvnOptions],
    field_names: list[str],
) -> None:
    """Dataclass introspection exposes only user-configurable backend fields."""
    assert [field.name for field in dataclasses.fields(options_type)] == field_names


def test_backend_sync_classes_publish_their_options_type() -> None:
    """Generic callers can discover each backend's options dataclass."""
    assert GitSync.options_type is GitOptions
    assert HgSync.options_type is HgOptions
    assert SvnSync.options_type is SvnOptions


def test_backend_options_have_secure_neutral_defaults() -> None:
    """Defaults preserve full clones and verify Git and Mercurial TLS."""
    assert GitOptions() == GitOptions(depth=None, filter=None, tls_verify=True)
    assert HgOptions() == HgOptions(
        ssh=None,
        remote_cmd=None,
        pull=False,
        stream=False,
        tls_verify=True,
    )
    assert SvnOptions() == SvnOptions(
        username=None,
        password=None,
        depth=None,
        trust_server_cert=False,
        ignore_externals=False,
    )


def test_backend_options_are_frozen_and_hide_svn_password() -> None:
    """Options are immutable, and repr never reveals a Subversion password."""
    options = SvnOptions(password="secret")

    with pytest.raises(dataclasses.FrozenInstanceError):
        options.depth = "files"  # type: ignore[misc]

    assert "secret" not in repr(options)


def test_git_options_validate_depth_and_snapshot_filter() -> None:
    """Git options reject invalid depth and detach filter config from callers."""
    filters: list[object] = [BlobNone(), {"kind": "tree", "depth": 2}]
    options = GitOptions(depth=2, filter=filters)
    filters.append("object:type=commit")

    assert options.filter == ("blob:none", "tree:2")
    with pytest.raises(ValueError, match="depth"):
        GitOptions(depth=True)
    with pytest.raises(ValueError, match="depth"):
        GitOptions(depth=0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: GitOptions(tls_verify=t.cast(t.Any, 1)),
        lambda: HgOptions(ssh=t.cast(t.Any, False)),
        lambda: HgOptions(pull=t.cast(t.Any, 1)),
        lambda: SvnOptions(username=t.cast(t.Any, False)),
        lambda: SvnOptions(depth=t.cast(t.Any, "children")),
        lambda: SvnOptions(ignore_externals=t.cast(t.Any, 1)),
    ],
)
def test_backend_options_reject_wrong_field_types(
    factory: t.Callable[[], object],
) -> None:
    """Options reject values outside their documented runtime types."""
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_git_options_normalization_preserves_filter_nesting_limit() -> None:
    """Canonical repeated flags retain the nesting accepted at construction."""
    spec = "combine:" * 32 + "blob:none"
    options = GitOptions(filter=spec)

    assert filter_specs(options.filter) == filter_specs(spec)
    with pytest.raises(ValueError, match="nesting"):
        GitOptions(filter="combine:" + spec)


@pytest.mark.parametrize(
    ("options_type", "field"),
    [
        (HgOptions, "ssh"),
        (HgOptions, "remote_cmd"),
        (SvnOptions, "username"),
        (SvnOptions, "password"),
    ],
)
def test_backend_options_reject_nul_before_command_creation(
    options_type: type[HgOptions | SvnOptions],
    field: str,
) -> None:
    """Strings destined for native argv cannot contain embedded NUL bytes."""
    with pytest.raises(ValueError, match=field):
        options_type(**{field: "value\0suffix"})  # type: ignore[arg-type]


def test_sync_constructors_reject_unknown_and_wrong_backend_options(
    tmp_path: pathlib.Path,
) -> None:
    """Explicit constructors reject misspellings and backend mismatches."""
    with pytest.raises(TypeError, match="unexpected"):
        GitSync(url="file:///unused", path=tmp_path, tls_verfy=False)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="unexpected"):
        BaseSync(url="file:///unused", path=tmp_path, revision="main")  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="unexpected"):
        GitOptions(dept=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="GitOptions"):
        GitSync(url="file:///unused", path=tmp_path, options=HgOptions())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="unexpected"):
        create_project(  # type: ignore[call-overload]
            url="file:///unused",
            path=tmp_path,
            vcs="git",
            tls_verfy=False,
        )

    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in inspect.signature(GitSync).parameters.values()
    )


def test_create_project_forwards_backend_options(tmp_path: pathlib.Path) -> None:
    """The backend-neutral shortcut preserves the selected typed options."""
    options = HgOptions(stream=True)

    repo = create_project(
        url="https://example.com/repo",
        path=tmp_path,
        vcs="hg",
        options=options,
    )

    assert repo.options is options
    with pytest.raises(TypeError, match="HgOptions"):
        create_project(  # type: ignore[call-overload]
            url="https://example.com/repo",
            path=tmp_path,
            vcs="hg",
            options=GitOptions(),
        )


def test_create_project_forwards_hg_remotes(
    tmp_path: pathlib.Path, hg_repo: HgSync
) -> None:
    """The factory applies Mercurial fetch and push destinations separately."""
    from libvcs import HgRemote

    remote = HgRemote(
        "upstream", hg_repo.path.as_uri(), (tmp_path / "push-only").as_uri()
    )
    repo = create_project(
        url=hg_repo.url,
        path=tmp_path / "checkout",
        vcs="hg",
        remotes={"upstream": remote},
    )
    assert repo.update_repo().ok
    assert repo.remotes()["upstream"] == remote


def test_git_disabled_tls_option_runs_native_clone_and_fetch(
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
) -> None:
    """Clone, fetch, and submodule commands accept the TLS override as argv."""
    repo = GitSync(
        url=git_remote_repo.as_uri(),
        path=tmp_path / "checkout",
        options=GitOptions(tls_verify=False),
    )
    repo.obtain()
    revision = repo.get_position().revision
    result = repo.update_repo()

    assert result.ok
    assert repo.get_position().revision == revision


def test_git_options_forward_clone_filter_depth_and_tls_polarity(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Git clone receives typed depth, filter, and disabled TLS verification."""
    repo = GitSync(
        url="https://example.com/repo.git",
        path=tmp_path / "checkout",
        options=GitOptions(depth=3, filter=BlobNone(), tls_verify=False),
    )
    clone = mocker.patch.object(repo.cmd, "clone", return_value="")
    mocker.patch.object(repo.cmd.submodule, "init", return_value="")
    update = mocker.patch.object(repo.cmd.submodule, "update", return_value="")
    mocker.patch.object(repo, "set_remotes")

    repo.obtain()

    assert clone.call_args.kwargs["depth"] == 3
    assert clone.call_args.kwargs["_filter"] == ("blob:none",)
    assert clone.call_args.kwargs["config"] == {"http.sslVerify": False}
    assert update.call_args.kwargs["_filter"] == ("blob:none",)
    assert update.call_args.kwargs["config"] == {"http.sslVerify": False}


def test_git_tls_option_applies_to_existing_checkout_network_operations(
    git_repo: GitSync,
    mocker: MockerFixture,
) -> None:
    """Disabled verification reaches fetch and clean submodule updates."""
    git_repo.options = GitOptions(tls_verify=False)
    commands = mocker.spy(git_repo.cmd, "run")
    submodules = mocker.spy(git_repo.cmd.submodule, "update")

    result = git_repo.update_repo()

    assert result.ok, result.errors
    fetch = next(call for call in commands.call_args_list if call.args[0][0] == "fetch")
    assert fetch.kwargs["config"] == {"http.sslVerify": False}
    assert "--all" in fetch.args[0]
    assert submodules.call_args.kwargs["config"] == {"http.sslVerify": False}


def test_git_target_fetches_named_remote(git_repo: GitSync) -> None:
    """A configured target can resolve a remote other than the default origin."""
    original = git_repo.get_position()
    git_repo.cmd.run(
        ["remote", "add", "secondary", git_repo.url], check_returncode=True
    )

    result = git_repo.update_repo(
        target=SyncTarget(branch=original.ref_name, remote="secondary")
    )

    assert result.ok, result.errors
    assert (
        git_repo.cmd.run(
            ["rev-parse", f"refs/remotes/secondary/{original.ref_name}"],
            check_returncode=True,
        ).strip()
        == original.revision
    )


def test_hg_options_forward_clone_and_network_update(
    tmp_path: pathlib.Path,
    hg_repo: HgSync,
    mocker: MockerFixture,
) -> None:
    """Mercurial transport options reach clone and pull operations."""
    options = HgOptions(
        ssh="ssh -i key",
        remote_cmd="hg-custom",
        pull=True,
        stream=True,
        tls_verify=False,
    )
    repo = HgSync(url="https://example.com/repo", path=tmp_path, options=options)
    clone = mocker.patch.object(repo.cmd, "clone", return_value="")
    mocker.patch.object(repo.cmd, "update", return_value="")

    repo.obtain()

    assert clone.call_args.kwargs == {
        "no_update": True,
        "quiet": True,
        "url": repo.url,
        "ssh": "ssh -i key",
        "remote_cmd": "hg-custom",
        "pull": True,
        "stream": True,
        "insecure": True,
        "check_returncode": True,
    }

    hg_repo.options = options
    pull = mocker.patch.object(hg_repo.cmd, "pull", return_value="")
    result = hg_repo.update_repo()
    assert result.ok, result.errors
    assert pull.call_args.kwargs == {
        "source": None,
        "update": False,
        "ssh": "ssh -i key",
        "remote_cmd": "hg-custom",
        "insecure": True,
        "check_returncode": True,
    }


def test_svn_options_forward_checkout_and_update(
    tmp_path: pathlib.Path,
    svn_remote_repo: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Subversion checkout and network update receive their typed options."""
    options = SvnOptions(
        username="reader",
        password="secret",
        depth="files",
        trust_server_cert=True,
        ignore_externals=True,
    )
    repo = SvnSync(url="https://example.com/repo", path=tmp_path, options=options)
    checkout = mocker.patch.object(repo.cmd, "checkout", return_value="")

    repo.obtain()

    assert checkout.call_args.kwargs == {
        "url": repo.url,
        "revision": None,
        "username": "reader",
        "password": "secret",
        "depth": "files",
        "trust_server_cert": True,
        "ignore_externals": True,
        "non_interactive": True,
        "quiet": True,
        "check_returncode": True,
    }

    native = SvnSync(
        url=svn_remote_repo.as_uri(), path=tmp_path / "native", options=options
    )
    native.obtain()
    run = mocker.spy(native.cmd, "run")
    result = native.update_repo()
    assert result.ok, result.errors
    update = next(call for call in run.call_args_list if call.args[0][0] == "update")
    assert update.kwargs == {
        "username": "reader",
        "password": "secret",
        "trust_server_cert": True,
        "non_interactive": True,
        "check_returncode": True,
    }
    assert "--ignore-externals" in update.args[0]
    assert "--accept" in update.args[0]
    assert "postpone" in update.args[0]
