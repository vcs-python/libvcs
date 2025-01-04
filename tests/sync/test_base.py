"""tests for libvcs.sync abstract base class."""

from __future__ import annotations

import pathlib
import sys
import typing as t

from libvcs._internal.shortcuts import create_project
from libvcs.sync.base import BaseSync, convert_pip_url

if t.TYPE_CHECKING:
    import datetime

    import pytest


def test_repr_via_create_project() -> None:
    """Test BaseSync repr, via create_project()."""
    repo = create_project(url="file://path/to/myrepo", path="/hello/", vcs="git")

    str_repo = str(repo)
    assert "GitSync" in str_repo
    assert "hello" in str_repo
    assert str_repo == "<GitSync hello>"


def test_repr_base() -> None:
    """Test BaseSync constructor and repr."""
    repo = BaseSync(url="file://path/to/myrepo", path="/hello/")

    str_repo = str(repo)
    assert "Sync" in str_repo
    assert "hello" in str_repo
    assert str_repo == "<BaseSync hello>"


def test_ensure_dir_creates_parent_if_not_exist(tmp_path: pathlib.Path) -> None:
    """Test BaseDir.ensure_dir()."""
    projects_path = tmp_path / "projects_path"  # doesn't exist yet
    path = projects_path / "myrepo"
    repo = BaseSync(url="file://path/to/myrepo", path=path)

    repo.ensure_dir()
    assert projects_path.is_dir()


def test_convert_pip_url() -> None:
    """Test convert_pip_url()."""
    url, rev = convert_pip_url(pip_url="git+file://path/to/myrepo@therev")

    assert url, rev == "therev"
    assert url, rev == "file://path/to/myrepo"


def test_progress_callback(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
) -> None:
    """Test GitSync with progress callback."""

    def progress_cb(output: t.AnyStr, timestamp: datetime.datetime) -> None:
        sys.stdout.write(str(output))
        sys.stdout.flush()

    class Project(BaseSync):
        bin_name = "git"

        def obtain(self, *args: list[str], **kwargs: dict[str, str]) -> None:
            self.ensure_dir()
            self.run(
                ["clone", "--progress", self.url, pathlib.Path(self.path)],
                log_in_real_time=True,
            )

    r = Project(
        url=f"file://{git_remote_repo!s}",
        path=str(tmp_path),
        progress_callback=progress_cb,
    )
    r.obtain()
    captured = capsys.readouterr()
    assert "Cloning into" in captured.out
