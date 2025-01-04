"""Tests for libvcs hg repos."""

from __future__ import annotations

import pathlib
import shutil

import pytest

from libvcs import exc
from libvcs._internal.run import run
from libvcs._internal.shortcuts import create_project
from libvcs.sync.hg import HgSync

if not shutil.which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


@pytest.fixture(autouse=True)
def set_hgconfig(
    set_hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Set mercurial configuration."""
    return set_hgconfig


def test_hg_sync(
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Test HgSync."""
    repo_name = "my_mercurial_project"

    mercurial_repo = HgSync(
        url=f"file://{hg_remote_repo}",
        path=projects_path / repo_name,
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"],
        cwd=projects_path / repo_name,
    )

    assert mercurial_repo.get_revision() == test_repo_revision


def test_repo_mercurial_via_create_project(
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Test HgSync via create_project()."""
    repo_name = "my_mercurial_project"

    mercurial_repo = create_project(
        url=f"file://{hg_remote_repo}",
        path=projects_path / repo_name,
        vcs="hg",
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"],
        cwd=projects_path / repo_name,
    )

    assert mercurial_repo.get_revision() == test_repo_revision


def test_vulnerability_2022_03_12_command_injection(
    monkeypatch: pytest.MonkeyPatch,
    user_path: pathlib.Path,
    tmp_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Prevent hg aliases from executed arbitrary commands via URLs.

    As of 0.11 this code path is/was only executed via .obtain(), so this only would
    effect explicit invocation of .object() or update_repo() of uncloned destination.
    """
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    monkeypatch.chdir(str(random_dir))
    mercurial_repo = create_project(
        url="--config=alias.clone=!touch ./HELLO",
        vcs="hg",
        path="./",
    )
    with pytest.raises(exc.CommandError):
        mercurial_repo.update_repo()

    assert not pathlib.Path(
        random_dir / "HELLO",
    ).exists(), "Prevent command injection in hg aliases"
