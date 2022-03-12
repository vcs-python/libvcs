"""Tests for libvcs hg repos."""
import getpass
import pathlib
import textwrap

import pytest

from libvcs.shortcuts import create_repo, create_repo_from_pip_url
from libvcs.util import run, which

if not which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


@pytest.fixture(autouse=True, scope="session")
def hgrc(user_path: pathlib.Path):
    hgrc = user_path / ".hgrc"
    hgrc.write_text(
        textwrap.dedent(
            f"""
        [ui]
        username = libvcs tests <libvcs@git-pull.com>
        merge = internal:merge

        [trusted]
        users = {getpass.getuser()}
    """
        ),
        encoding="utf-8",
    )
    return hgrc


@pytest.fixture(autouse=True)
def hgrc_default(monkeypatch: pytest.MonkeyPatch, user_path: pathlib.Path):
    monkeypatch.setenv("HOME", str(user_path))


@pytest.fixture
def hg_remote(repos_path):
    """Create a git repo with 1 commit, used as a remote."""
    name = "test_hg_repo"
    repo_path = repos_path / name

    run(["hg", "init", name], cwd=repos_path)

    testfile_filename = "testfile.test"

    run(["touch", testfile_filename], cwd=repo_path)
    run(["hg", "add", testfile_filename], cwd=repo_path)
    run(["hg", "commit", "-m", "test file for %s" % name], cwd=repo_path)

    return repo_path


def test_repo_mercurial(tmp_path: pathlib.Path, repos_path, hg_remote):
    repo_name = "my_mercurial_project"

    mercurial_repo = create_repo_from_pip_url(
        **{
            "pip_url": f"hg+file://{hg_remote}",
            "repo_dir": repos_path / repo_name,
        }
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"], cwd=repos_path / repo_name
    )

    assert mercurial_repo.get_revision() == test_repo_revision


def test_vulnerability_2022_03_12_command_injection(
    monkeypatch: pytest.MonkeyPatch,
    user_path: pathlib.Path,
    tmp_path: pathlib.Path,
    hg_remote,
):
    """Prevent hg aliases from executed arbitrary commands via URLs.

    As of 0.11 this code path is/was only executed via .obtain(), so this only would
    effect explicit invocation of .object() or update_repo() of uncloned destination.
    """
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    monkeypatch.chdir(str(random_dir))
    mercurial_repo = create_repo(
        url="--config=alias.clone=!touch ./HELLO", vcs="hg", repo_dir="./"
    )
    with pytest.raises(Exception):
        mercurial_repo.update_repo()

    assert not pathlib.Path(
        random_dir / "HELLO"
    ).exists(), "Prevent command injection in hg aliases"
