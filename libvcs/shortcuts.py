# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from libvcs import GitRepo, MercurialRepo, SubversionRepo
from libvcs.exc import InvalidPipURL, InvalidVCS


def create_repo(url, vcs, **kwargs):
    r"""Return object with base class :class:`BaseRepo` depending on url.

    Return instance of :class:`libvcs.svn.SubversionRepo`,
    :class:`libvcs.git.GitRepo` or
    :class:`libvcs.hg.MercurialRepo`.
    The object returned is a child of :class:`libvcs.base.BaseRepo`."""
    if vcs == 'git':
        return GitRepo(url, **kwargs)
    elif vcs == 'hg':
        return MercurialRepo(url, **kwargs)
    elif vcs == 'svn':
        return SubversionRepo(url, **kwargs)
    else:
        raise InvalidVCS('VCS %s is not a valid VCS' % vcs)


def create_repo_from_pip_url(pip_url, **kwargs):
    r"""Return object with base class :class:`BaseRepo` depending on url.

    Return instance of :class:`libvcs.svn.SubversionRepo`,
    :class:`libvcs.git.GitRepo` or
    :class:`libvcs.hg.MercurialRepo`.
    The object returned is a child of :class:`libvcs.base.BaseRepo`.

    Usage Example::

        In [1]: from libvcs import create_repo_from_pip_url

        In [2]: r = create_repo_from_pip_url(
                    url='git+https://www.github.com/you/myrepo',
                    parent_dir='/tmp/',
                    name='myrepo')

        In [3]: r.update_repo()
        |myrepo| (git)  Repo directory for myrepo (git) does not exist @ \
            /tmp/myrepo
        |myrepo| (git)  Cloning.
        |myrepo| (git)  git clone --progress https://www.github.com/tony/myrepo
            /tmp/myrepo
        Cloning into '/tmp/myrepo'...
        Checking connectivity... done.
        |myrepo| (git)  git fetch
        |myrepo| (git)  git pull
        Already up-to-date.
    """
    if pip_url.startswith('git+'):
        return GitRepo.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith('hg+'):
        return MercurialRepo.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith('svn+'):
        return SubversionRepo.from_pip_url(pip_url, **kwargs)
    else:
        raise InvalidPipURL(pip_url)
