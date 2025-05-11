"""Tests for libvcs.cmd.git."""

from __future__ import annotations

import pathlib
import typing as t

import pytest

from libvcs._vendor.version import InvalidVersion, Version
from libvcs.cmd import git


@pytest.mark.parametrize("path_type", [str, pathlib.Path])
def test_git_constructor(
    path_type: t.Callable[[str | pathlib.Path], t.Any],
    tmp_path: pathlib.Path,
) -> None:
    """Test Git constructor."""
    repo = git.Git(path=path_type(tmp_path))

    assert repo.path == tmp_path


def test_version_basic(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test basic git version output."""
    git_cmd = git.Git(path=tmp_path)

    monkeypatch.setattr(git_cmd, "run", lambda *args, **kwargs: "git version 2.43.0")

    result = git_cmd.version()
    assert isinstance(result, Version)
    assert result.major == 2
    assert result.minor == 43
    assert result.micro == 0
    assert str(result) == "2.43.0"


def test_build_options(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test build_options() method."""
    git_cmd = git.Git(path=tmp_path)

    sample_output = """git version 2.43.0
cpu: x86_64
no commit associated with this build
sizeof-long: 8
sizeof-size_t: 8
shell-path: /bin/sh"""

    # Mock run() directly instead of version()
    def mock_run(cmd_args: list[str], **kwargs: t.Any) -> str:
        assert cmd_args == ["version", "--build-options"]
        return sample_output

    monkeypatch.setattr(git_cmd, "run", mock_run)

    result = git_cmd.build_options()

    assert isinstance(result, git.GitVersionInfo)
    assert result.version == "2.43.0"
    assert result.version_info == (2, 43, 0)
    assert result.cpu == "x86_64"
    assert result.commit == "no commit associated with this build"
    assert result.sizeof_long == "8"
    assert result.sizeof_size_t == "8"
    assert result.shell_path == "/bin/sh"


def test_build_options_invalid_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test build_options() with invalid version string."""
    git_cmd = git.Git(path=tmp_path)

    sample_output = """git version development
cpu: x86_64
commit: abcdef123456
sizeof-long: 8
sizeof-size_t: 8
shell-path: /bin/sh"""

    def mock_run(cmd_args: list[str], **kwargs: t.Any) -> str:
        assert cmd_args == ["version", "--build-options"]
        return sample_output

    monkeypatch.setattr(git_cmd, "run", mock_run)

    result = git_cmd.build_options()

    assert isinstance(result, git.GitVersionInfo)
    assert result.version == "development"
    assert result.version_info is None
    assert result.commit == "abcdef123456"


def test_version_invalid_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test version() with invalid output format."""
    git_cmd = git.Git(path=tmp_path)

    invalid_output = "not a git version format"

    monkeypatch.setattr(git_cmd, "run", lambda *args, **kwargs: invalid_output)

    with pytest.raises(InvalidVersion) as excinfo:
        git_cmd.version()

    assert f"Invalid version: '{invalid_output}'" in str(excinfo.value)


def test_build_options_invalid_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test build_options() with invalid output format."""
    git_cmd = git.Git(path=tmp_path)

    invalid_output = "not a git version format"

    monkeypatch.setattr(git_cmd, "run", lambda *args, **kwargs: invalid_output)

    with pytest.raises(git.InvalidBuildOptions) as excinfo:
        git_cmd.build_options()

    assert "Unexpected git version output format" in str(excinfo.value)
