"""tests for libvcs repo abstract base class."""
import pathlib
import sys

import pytest

from libvcs.projects.base import BaseProject, convert_pip_url
from libvcs.shortcuts import create_project


def test_repr():
    repo = create_project(url="file://path/to/myrepo", dir="/hello/", vcs="git")

    str_repo = str(repo)
    assert "GitProject" in str_repo
    assert "hello" in str_repo
    assert "<GitProject hello>" == str_repo


def test_repr_base():
    repo = BaseProject(url="file://path/to/myrepo", dir="/hello/")

    str_repo = str(repo)
    assert "Project" in str_repo
    assert "hello" in str_repo
    assert "<BaseProject hello>" == str_repo


def test_ensure_dir_creates_parent_if_not_exist(tmp_path: pathlib.Path):
    projects_path = tmp_path / "projects_path"  # doesn't exist yet
    dir = projects_path / "myrepo"
    repo = BaseProject(url="file://path/to/myrepo", dir=dir)

    repo.ensure_dir()
    assert projects_path.is_dir()


def test_convert_pip_url():
    url, rev = convert_pip_url(pip_url="git+file://path/to/myrepo@therev")

    assert url, rev == "therev"
    assert url, rev == "file://path/to/myrepo"


def test_progress_callback(
    capsys: pytest.LogCaptureFixture,
    tmp_path: pathlib.Path,
    git_remote_repo: pathlib.Path,
):
    def progress_cb(output, timestamp):
        sys.stdout.write(output)
        sys.stdout.flush()

    class Project(BaseProject):
        bin_name = "git"

        def obtain(self, *args, **kwargs):
            self.ensure_dir()
            self.run(["clone", "--progress", self.url, self.dir], log_in_real_time=True)

    r = Project(
        url=f"file://{str(git_remote_repo)}",
        dir=str(tmp_path),
        progress_callback=progress_cb,
    )
    r.obtain()
    captured = capsys.readouterr()
    assert "Cloning into" in captured.out
