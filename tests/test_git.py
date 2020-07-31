# -*- coding: utf-8 -*-
"""Tests for libvcs git repos."""
from __future__ import absolute_import, print_function, unicode_literals

import datetime
import os

import pytest

from libvcs import exc
from libvcs._compat import string_types
from libvcs.git import GitRemote, GitRepo
from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.util import run, which

if not which('git'):
    pytestmark = pytest.mark.skip(reason="git is not available")


def test_repo_git_obtain_initial_commit_repo(tmpdir):
    """initial commit repos return 'initial'.

    note: this behaviors differently from git(1)'s use of the word "bare".
    running `git rev-parse --is-bare-repository` would return false.
    """
    repo_name = 'my_git_project'

    run(['git', 'init', repo_name], cwd=str(tmpdir))

    bare_repo_dir = tmpdir.join(repo_name)

    git_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'git+file://' + str(bare_repo_dir),
            'repo_dir': str(tmpdir.join('obtaining a bare repo')),
        }
    )

    git_repo.obtain()
    assert git_repo.get_revision() == 'initial'


def test_repo_git_obtain_full(tmpdir, git_remote):
    git_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'git+file://' + git_remote,
            'repo_dir': str(tmpdir.join('myrepo')),
        }
    )

    git_repo.obtain()

    test_repo_revision = run(['git', 'rev-parse', 'HEAD'], cwd=git_remote)

    assert git_repo.get_revision() == test_repo_revision
    assert os.path.exists(str(tmpdir.join('myrepo')))


def test_repo_update_handle_cases(tmpdir, git_remote, mocker):
    git_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'git+file://' + git_remote,
            'repo_dir': str(tmpdir.join('myrepo')),
        }
    )

    git_repo.obtain()  # clone initial repo
    mocka = mocker.spy(git_repo, 'run')
    git_repo.update_repo()

    mocka.assert_any_call(['symbolic-ref', '--short', 'HEAD'])

    mocka.reset_mock()

    # will only look up symbolic-ref if no rev specified for object
    git_repo.rev = 'HEAD'
    git_repo.update_repo()
    assert mocker.call(['symbolic-ref', '--short', 'HEAD']) not in mocka.mock_calls


def test_progress_callback(tmpdir, git_remote, mocker):
    def progress_callback_spy(output, timestamp):
        assert isinstance(output, string_types)
        assert isinstance(timestamp, datetime.datetime)

    progress_callback = mocker.Mock(
        name='progress_callback_stub', side_effect=progress_callback_spy
    )

    run(['git', 'rev-parse', 'HEAD'], cwd=git_remote)

    # create a new repo with the repo as a remote
    git_repo = create_repo_from_pip_url(
        **{
            'pip_url': 'git+file://' + git_remote,
            'repo_dir': str(tmpdir.join('myrepo')),
            'progress_callback': progress_callback,
        }
    )
    git_repo.obtain()

    assert progress_callback.called


def test_remotes(parentdir, git_remote):
    repo_name = 'myrepo'
    remote_name = 'myremote'
    remote_url = 'https://localhost/my/git/repo.git'

    git_repo = create_repo_from_pip_url(
        pip_url='git+file://{git_remote}'.format(git_remote=git_remote),
        repo_dir=os.path.join(str(parentdir), repo_name),
    )
    git_repo.obtain()
    git_repo.set_remote(name=remote_name, url=remote_url)

    assert (remote_name, remote_url, remote_url) == git_repo.remote(remote_name)


def test_git_get_url_and_rev_from_pip_url():
    pip_url = 'git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git'
    url, rev = GitRepo.get_url_and_revision_from_pip_url(pip_url)
    assert 'ssh://git@bitbucket.example.com:7999/PROJ/repo.git' == url
    assert rev is None

    pip_url = '%s@%s' % (
        'git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git',
        'eucalyptus',
    )
    url, rev = GitRepo.get_url_and_revision_from_pip_url(pip_url)
    assert 'ssh://git@bitbucket.example.com:7999/PROJ/repo.git' == url
    assert rev == 'eucalyptus'

    # the git manual refers to this as "scp-like syntax"
    # https://git-scm.com/docs/git-clone
    pip_url = '%s@%s' % ('git+user@hostname:user/repo.git', 'eucalyptus')
    url, rev = GitRepo.get_url_and_revision_from_pip_url(pip_url)
    assert 'user@hostname:user/repo.git' == url
    assert rev == 'eucalyptus'


def test_remotes_preserves_git_ssh(parentdir, git_remote):
    # Regression test for #14
    repo_name = 'myexamplegit'
    repo_dir = os.path.join(str(parentdir), repo_name)
    remote_name = 'myremote'
    remote_url = 'git+ssh://git@github.com/tony/AlgoXY.git'

    git_repo = create_repo_from_pip_url(pip_url=remote_url, repo_dir=repo_dir)
    git_repo.obtain()
    git_repo.set_remote(name=remote_name, url=remote_url)

    assert (
        GitRemote(remote_name, remote_url, remote_url)._asdict()
        in git_repo.remotes.values()
    )


def test_private_ssh_format(pip_url_kwargs):
    pip_url_kwargs.update(
        **{'pip_url': 'git+ssh://github.com:' + '/tmp/omg/private_ssh_repo'}
    )

    with pytest.raises(exc.LibVCSException) as excinfo:
        create_repo_from_pip_url(**pip_url_kwargs)
    excinfo.match(r'is malformatted')


def test_ls_remotes(git_repo):
    remotes = git_repo.remotes

    assert 'origin' in remotes


def test_get_remotes(git_repo):
    assert 'origin' in git_repo.remotes


@pytest.mark.parametrize('repo_name,new_repo_url', [['myrepo', 'file:///apples'],])
def test_set_remote(git_repo, repo_name, new_repo_url):
    mynewremote = git_repo.set_remote(name=repo_name, url='file:///')

    assert 'file:///' in mynewremote, 'set_remote returns remote'

    assert 'file:///' in git_repo.remote(name=repo_name), 'remote returns remote'

    assert 'myrepo' in git_repo.remotes, '.remotes() returns new remote'

    with pytest.raises(
        exc.CommandError,
        match='.*remote {repo_name} already exists.*'.format(repo_name=repo_name),
    ):
        mynewremote = git_repo.set_remote(name='myrepo', url=new_repo_url)

    mynewremote = git_repo.set_remote(name='myrepo', url=new_repo_url, overwrite=True)

    assert new_repo_url in git_repo.remote(
        name='myrepo'
    ), 'Running remove_set should overwrite previous remote'
