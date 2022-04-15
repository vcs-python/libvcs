"""Shortcuts"""
from typing import Union

from libvcs import GitProject, MercurialProject, SubversionProject
from libvcs.exc import InvalidPipURL, InvalidVCS


def create_project(
    url, vcs, progress_callback=None, *args, **kwargs
) -> Union[GitProject, MercurialProject, SubversionProject]:
    r"""Return an object representation of a VCS repository.

    Examples
    --------
    >>> from libvcs.shortcuts import create_project
    >>> r = create_project(
    ...     url=f'file://{create_git_remote_repo()}',
    ...     vcs='git',
    ...     dir=tmp_path
    ... )

    >>> isinstance(r, GitProject)
    True
    """
    if vcs == "git":
        return GitProject(url, progress_callback=progress_callback, *args, **kwargs)
    elif vcs == "hg":
        return MercurialProject(
            url, progress_callback=progress_callback, *args, **kwargs
        )
    elif vcs == "svn":
        return SubversionProject(
            url, progress_callback=progress_callback, *args, **kwargs
        )
    else:
        raise InvalidVCS("VCS %s is not a valid VCS" % vcs)


def create_project_from_pip_url(
    pip_url, **kwargs
) -> Union[GitProject, MercurialProject, SubversionProject]:
    r"""Return an object representation of a VCS repository via pip-style url.

    Examples
    --------

    >>> from libvcs.shortcuts import create_project_from_pip_url
    >>> r = create_project_from_pip_url(
    ...     pip_url=f'git+{create_git_remote_repo()}',
    ...     dir=tmp_path
    ... )
    >>> isinstance(r, GitProject)
    True
    """
    if pip_url.startswith("git+"):
        return GitProject.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("hg+"):
        return MercurialProject.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("svn+"):
        return SubversionProject.from_pip_url(pip_url, **kwargs)
    else:
        raise InvalidPipURL(pip_url)
