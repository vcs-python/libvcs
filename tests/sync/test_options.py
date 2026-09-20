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
)
from libvcs._internal.shortcuts import create_project
from libvcs.cmd.git_filter import BlobNone

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
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> None:
    """Disabled verification reaches fetch and existing submodule updates."""
    (tmp_path / ".git").mkdir()
    repo = GitSync(
        url="https://example.com/repo.git",
        path=tmp_path,
        options=GitOptions(tls_verify=False),
    )
    mocker.patch.object(repo.cmd, "symbolic_ref", return_value="main")
    mocker.patch.object(repo.cmd, "rev_list", side_effect=["head", "next"])
    mocker.patch.object(repo.cmd, "show_ref", return_value="next refs/heads/main\n")
    mocker.patch.object(repo, "get_current_remote_name", return_value="origin")
    fetch = mocker.patch.object(repo.cmd, "fetch", return_value="")
    mocker.patch.object(repo.cmd, "checkout", return_value="")
    submodules = mocker.patch.object(repo.cmd.submodule, "update", return_value="")

    result = repo.update_repo()

    assert result.ok
    assert fetch.call_args.kwargs["config"] == {"http.sslVerify": False}
    assert submodules.call_args.kwargs["config"] == {"http.sslVerify": False}


def test_hg_options_forward_clone_and_network_update(
    tmp_path: pathlib.Path,
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

    (tmp_path / ".hg").mkdir()
    pull = mocker.patch.object(repo.cmd, "pull", return_value="")
    repo.update_repo()
    assert pull.call_args.kwargs == {
        "update": True,
        "ssh": "ssh -i key",
        "remote_cmd": "hg-custom",
        "insecure": True,
    }


def test_svn_options_forward_checkout_and_update(
    tmp_path: pathlib.Path,
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

    (tmp_path / ".svn").mkdir()
    repo.update_repo()
    assert checkout.call_args.kwargs == {
        "url": repo.url,
        "revision": None,
        "username": "reader",
        "password": "secret",
        "trust_server_cert": True,
        "ignore_externals": True,
        "non_interactive": True,
        "quiet": True,
        "check_returncode": True,
    }
