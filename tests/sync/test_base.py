"""tests for libvcs.sync abstract base class."""
import datetime
import pathlib
import sys
from typing import AnyStr

import pytest

from libvcs._internal.shortcuts import create_project
from libvcs.sync.base import BaseSync, convert_pip_url


def test_repr() -> None:
    repo = create_project(url="file://path/to/myrepo", dir="/hello/", vcs="git")

    str_repo = str(repo)
    assert "GitSync" in str_repo
    assert "hello" in str_repo
    assert "<GitSync hello>" == str_repo


def test_repr_base() -> None:
    repo = BaseSync(url="file://path/to/myrepo", dir="/hello/")

    str_repo = str(repo)
    assert "Sync" in str_repo
    assert "hello" in str_repo
    assert "<BaseSync hello>" == str_repo


def test_ensure_dir_creates_parent_if_not_exist(tmp_path: pathlib.Path) -> None:
    projects_path = tmp_path / "projects_path"  # doesn't exist yet
    dir = projects_path / "myrepo"
    repo = BaseSync(url="file://path/to/myrepo", dir=dir)

    repo.ensure_dir()
    assert projects_path.is_dir()


def test_convert_pip_url() -> None:
    url, rev = convert_pip_url(pip_url="git+file://path/to/myrepo@therev")

    assert url, rev == "therev"
    assert url, rev == "file://path/to/myrepo"


def test_progress_callback(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
) -> None:
    def progress_cb(output: AnyStr, timestamp: datetime.datetime) -> None:
        sys.stdout.write(str(output))
        sys.stdout.flush()

    class Project(BaseSync):
        bin_name = "git"

        def obtain(self, *args: list[str], **kwargs: dict[str, str]) -> None:
            self.ensure_dir()
            self.run(
                ["clone", "--progress", self.url, pathlib.Path(self.dir)],
                log_in_real_time=True,
            )

    r = Project(
        url=f"file://{str(git_remote_repo)}",
        dir=str(tmp_path),
        progress_callback=progress_cb,
    )
    r.obtain()
    captured = capsys.readouterr()
    assert "Cloning into" in captured.out
