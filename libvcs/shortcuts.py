"""Shortcuts"""
from typing import Union

from libvcs import GitRepo, MercurialRepo, SubversionRepo
from libvcs.exc import InvalidPipURL, InvalidVCS


def create_repo(
    url, vcs, progress_callback=None, *args, **kwargs
) -> Union[GitRepo, MercurialRepo, SubversionRepo]:
    r"""Return an object representation of a VCS repository.

    Examples
    --------
    >>> tmp_path = getfixture('tmp_path')
    >>> git_remote = getfixture('git_remote')
    >>> from libvcs.shortcuts import create_repo
    >>>
    >>> r = create_repo(
    ...     url=f'file://{str(git_remote)}',
    ...     vcs='git',
    ...     repo_dir=str(tmp_path)
    ... )

    >>> isinstance(r, GitRepo)
    True
    """
    if vcs == "git":
        return GitRepo(url, progress_callback=progress_callback, *args, **kwargs)
    elif vcs == "hg":
        return MercurialRepo(url, progress_callback=progress_callback, *args, **kwargs)
    elif vcs == "svn":
        return SubversionRepo(url, progress_callback=progress_callback, *args, **kwargs)
    else:
        raise InvalidVCS("VCS %s is not a valid VCS" % vcs)


def create_repo_from_pip_url(
    pip_url, **kwargs
) -> Union[GitRepo, MercurialRepo, SubversionRepo]:
    r"""Return an object representation of a VCS repository via pip-style url.

    Examples
    --------

    >>> from libvcs.shortcuts import create_repo_from_pip_url

    >>> tmp_path = getfixture('tmp_path')
    >>> git_remote = getfixture('git_remote')
    >>> r = create_repo_from_pip_url(
    ...         pip_url=f'git+{str(git_remote)}',
    ...         repo_dir=str(tmp_path)
    ...     )

    >>> isinstance(r, GitRepo)
    True
    """
    if pip_url.startswith("git+"):
        return GitRepo.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("hg+"):
        return MercurialRepo.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("svn+"):
        return SubversionRepo.from_pip_url(pip_url, **kwargs)
    else:
        raise InvalidPipURL(pip_url)
