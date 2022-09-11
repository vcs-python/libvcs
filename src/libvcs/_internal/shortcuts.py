"""Shortcuts for creating repos.

Note
----
This is an internal API not covered by versioning policy.
"""
import typing as t
from typing import Union

from libvcs import GitSync, HgSync, SvnSync
from libvcs._internal.run import ProgressCallbackProtocol
from libvcs._internal.types import StrPath, VCSLiteral
from libvcs.exc import InvalidVCS


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["git"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any]
) -> GitSync:
    ...


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["svn"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any]
) -> SvnSync:
    ...


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["hg"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = ...,
    **kwargs: dict[t.Any, t.Any]
) -> HgSync:
    ...


def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: VCSLiteral,
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any]
) -> Union[GitSync, HgSync, SvnSync]:
    r"""Return an object representation of a VCS repository.

    Examples
    --------
    >>> from libvcs._internal.shortcuts import create_project
    >>> r = create_project(
    ...     url=f'file://{create_git_remote_repo()}',
    ...     vcs='git',
    ...     dir=tmp_path
    ... )

    >>> isinstance(r, GitSync)
    True
    """
    if vcs == "git":
        return GitSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    elif vcs == "hg":
        return HgSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    elif vcs == "svn":
        return SvnSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    else:
        raise InvalidVCS("VCS %s is not a valid VCS" % vcs)
