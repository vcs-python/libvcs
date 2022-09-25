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
from libvcs.exc import InvalidVCS, LibVCSException
from libvcs.url import registry as url_tools

if t.TYPE_CHECKING:
    from typing_extensions import TypeGuard


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["git"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any],
) -> GitSync:
    ...


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["svn"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any],
) -> SvnSync:
    ...


@t.overload
def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Literal["hg"],
    progress_callback: t.Optional[ProgressCallbackProtocol] = ...,
    **kwargs: dict[t.Any, t.Any],
) -> HgSync:
    ...


def create_project(
    *,
    url: str,
    dir: StrPath,
    vcs: t.Optional[VCSLiteral] = None,
    progress_callback: t.Optional[ProgressCallbackProtocol] = None,
    **kwargs: dict[t.Any, t.Any],
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

    create_project can also guess VCS for certain URLs:

    >>> r = create_project(
    ...     # Note the git+ before the URL
    ...     url=f'git+file://{create_git_remote_repo()}',
    ...     dir=tmp_path
    ... )

    >>> isinstance(r, GitSync)
    True
    """
    if vcs is None:
        vcs_matches = url_tools.registry.match(url=url, is_explicit=True)

        if len(vcs_matches) == 0:
            raise LibVCSException(f"No vcs found for {url}")
        if len(vcs_matches) > 1:
            raise LibVCSException(f"No exact matches for {url}")

        assert vcs_matches[0].vcs is not None

        def is_vcs(val: t.Any) -> "TypeGuard[VCSLiteral]":
            return isinstance(val, str) and val in ["git", "hg", "svn"]

        if is_vcs(vcs_matches[0].vcs):
            vcs = vcs_matches[0].vcs
        else:
            raise InvalidVCS(f"{url} does not have supported vcs: {vcs}")

    if vcs == "git":
        return GitSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    elif vcs == "hg":
        return HgSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    elif vcs == "svn":
        return SvnSync(url=url, dir=dir, progress_callback=progress_callback, **kwargs)
    else:
        raise InvalidVCS("VCS %s is not a valid VCS" % vcs)
