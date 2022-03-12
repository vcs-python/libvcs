"""Tests for libvcs hg repos."""
import getpass
import pathlib
import textwrap

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
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
def hg_remote(parentdir):
    """Create a git repo with 1 commit, used as a remote."""
    name = "test_hg_repo"
    repo_path = parentdir / name

    run(["hg", "init", name], cwd=parentdir)

    testfile_filename = "testfile.test"

    run(["touch", testfile_filename], cwd=repo_path)
    run(["hg", "add", testfile_filename], cwd=repo_path)
    run(["hg", "commit", "-m", "test file for %s" % name], cwd=repo_path)

    return repo_path


def test_repo_mercurial(tmp_path: pathlib.Path, parentdir, hg_remote):
    repo_name = "my_mercurial_project"

    mercurial_repo = create_repo_from_pip_url(
        **{
            "pip_url": f"hg+file://{hg_remote}",
            "repo_dir": parentdir / repo_name,
        }
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"], cwd=parentdir / repo_name
    )

    assert mercurial_repo.get_revision() == test_repo_revision
