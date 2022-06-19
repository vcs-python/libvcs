import warnings
from typing import Union

from libvcs import GitProject, MercurialProject, SubversionProject
from libvcs._internal.shortcuts import create_project as _create_project
from libvcs.exc import InvalidPipURL


def create_project(*args, **kwargs):
    warnings.warn(
        "This function will be moved to an internal API in v0.14",
        PendingDeprecationWarning,
    )
    return _create_project(*args, **kwargs)


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
    warnings.warn("This function will be removed in v0.14", PendingDeprecationWarning)
    if pip_url.startswith("git+"):
        return GitProject.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("hg+"):
        return MercurialProject.from_pip_url(pip_url, **kwargs)
    elif pip_url.startswith("svn+"):
        return SubversionProject.from_pip_url(pip_url, **kwargs)
    else:
        raise InvalidPipURL(pip_url)
