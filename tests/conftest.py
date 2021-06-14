import os

import pytest

from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run


@pytest.fixture
def parentdir(tmpdir_factory, scope='function'):
    """Return temporary directory for repository checkout guaranteed unique."""
    fn = tmpdir_factory.mktemp("repo")
    return fn


@pytest.fixture
def pip_url_kwargs(parentdir, git_remote):
    """Return kwargs for :func:`create_repo_from_pip_url`."""
    repo_name = 'repo_clone'
    return {
        'pip_url': 'git+file://' + git_remote,
        'repo_dir': os.path.join(str(parentdir), repo_name),
    }


@pytest.fixture
def git_repo(pip_url_kwargs):
    """Create an git repository for tests. Return repo."""
    git_repo = create_repo_from_pip_url(**pip_url_kwargs)
    git_repo.obtain()
    return git_repo


@pytest.fixture
def git_remote(parentdir, scope='session'):
    """Create a git repo with 1 commit, used as a remote."""
    name = 'dummyrepo'
    repo_dir = str(parentdir.join(name))

    run(['git', 'init', name], cwd=str(parentdir))

    testfile_filename = 'testfile.test'

    run(['touch', testfile_filename], cwd=repo_dir)
    run(['git', 'add', testfile_filename], cwd=repo_dir)
    run(['git', 'commit', '-m', 'test file for %s' % name], cwd=repo_dir)

    return repo_dir
