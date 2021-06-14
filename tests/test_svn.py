"""tests for libvcs svn repos."""
import os

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run, which

if not which('svn'):
    pytestmark = pytest.mark.skip(reason="svn is not available")


@pytest.fixture
def svn_remote(parentdir, scope='session'):
    """Create a git repo with 1 commit, used as a remote."""
    server_dirname = 'server_dir'
    server_dir = parentdir.join(server_dirname)

    run(['svnadmin', 'create', str(server_dir)])

    return str(server_dir)


def test_repo_svn(tmpdir, svn_remote):
    repo_name = 'my_svn_project'

    svn_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'svn+file://' + svn_remote,
            'repo_dir': str(tmpdir.join(repo_name)),
        }
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file('./') == 0

    assert os.path.exists(str(tmpdir.join(repo_name)))
