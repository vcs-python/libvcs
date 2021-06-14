"""Tests for libvcs hg repos."""
import os

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run, which

if not which('hg'):
    pytestmark = pytest.mark.skip(reason="hg is not available")


@pytest.fixture
def hg_remote(parentdir, scope='session'):
    """Create a git repo with 1 commit, used as a remote."""
    name = 'dummyrepo'
    repo_path = str(parentdir.join(name))

    run(['hg', 'init', name], cwd=str(parentdir))

    testfile_filename = 'testfile.test'

    run(['touch', testfile_filename], cwd=repo_path)
    run(['hg', 'add', testfile_filename], cwd=repo_path)
    run(['hg', 'commit', '-m', 'test file for %s' % name], cwd=repo_path)

    return repo_path


def test_repo_mercurial(tmpdir, parentdir, hg_remote):
    repo_name = 'my_mercurial_project'

    mercurial_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'hg+file://' + hg_remote,
            'repo_dir': str(parentdir.join(repo_name)),
        }
    )

    run(['hg', 'init', mercurial_repo.repo_name], cwd=str(tmpdir))

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ['hg', 'parents', '--template={rev}'], cwd=str(parentdir.join(repo_name))
    )

    assert mercurial_repo.get_revision() == test_repo_revision
    assert os.path.exists(str(tmpdir.join(repo_name)))
