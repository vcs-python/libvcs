"""Benchmark suite for git sync operations via pytest-codspeed."""

from __future__ import annotations

import typing as t

import pytest

from libvcs.pytest_plugin import CreateRepoFn
from libvcs.sync.git import GitSync

if t.TYPE_CHECKING:
    import pathlib

    from pytest_codspeed.plugin import BenchmarkFixture


@pytest.mark.benchmark
def test_git_obtain_initial_commit_repo(
    create_git_remote_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark `GitSync.obtain` against a remote with one initial commit."""
    remote = create_git_remote_repo()
    repo = GitSync(url=f"file://{remote}", path=tmp_path / "checkout")

    benchmark(repo.obtain)

    assert repo.get_revision() == "initial"
