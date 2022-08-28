"""Tests for libvcs hg repos."""
import pathlib
import shutil

import pytest

from libvcs._internal.run import run
from libvcs._internal.shortcuts import create_project

if not shutil.which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


def test_repo_mercurial(
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    repo_name = "my_mercurial_project"

    mercurial_repo = create_project(
        url=f"file://{hg_remote_repo}",
        dir=projects_path / repo_name,
        vcs="hg",
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"], cwd=projects_path / repo_name
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
        url="--config=alias.clone=!touch ./HELLO", vcs="hg", dir="./"
    )
    with pytest.raises(Exception):
        mercurial_repo.update_repo()

    assert not pathlib.Path(
        random_dir / "HELLO"
    ).exists(), "Prevent command injection in hg aliases"
