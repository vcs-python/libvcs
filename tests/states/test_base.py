"""tests for libvcs repo abstract base class."""
import pathlib
import sys

import pytest

from libvcs.shortcuts import create_repo
from libvcs.states.base import BaseRepo, convert_pip_url


def test_repr():
    repo = create_repo(url="file://path/to/myrepo", repo_dir="/hello/", vcs="git")

    str_repo = str(repo)
    assert "GitRepo" in str_repo
    assert "hello" in str_repo
    assert "<GitRepo hello>" == str_repo


def test_repr_base():
    repo = BaseRepo(url="file://path/to/myrepo", repo_dir="/hello/")

    str_repo = str(repo)
    assert "Repo" in str_repo
    assert "hello" in str_repo
    assert "<BaseRepo hello>" == str_repo


def test_ensure_dir_creates_parent_if_not_exist(tmp_path: pathlib.Path):
    repos_path = tmp_path / "repos_path"  # doesn't exist yet
    repo_dir = repos_path / "myrepo"
    repo = BaseRepo(url="file://path/to/myrepo", repo_dir=repo_dir)

    repo.ensure_dir()
    assert repos_path.is_dir()


def test_convert_pip_url():
    url, rev = convert_pip_url(pip_url="git+file://path/to/myrepo@therev")

    assert url, rev == "therev"
    assert url, rev == "file://path/to/myrepo"


def test_progress_callback(
    capsys: pytest.LogCaptureFixture, tmp_path: pathlib.Path, git_remote: pathlib.Path
):
    def progress_cb(output, timestamp):
        sys.stdout.write(output)
        sys.stdout.flush()

    class Repo(BaseRepo):
        bin_name = "git"

        def obtain(self, *args, **kwargs):
            self.ensure_dir()
            self.run(
                ["clone", "--progress", self.url, self.path], log_in_real_time=True
            )

    r = Repo(
        url=f"file://{str(git_remote)}",
        repo_dir=str(tmp_path),
        progress_callback=progress_cb,
    )
    r.obtain()
    captured = capsys.readouterr()
    assert "Cloning into" in captured.out
