"""Shortcuts for creating repos.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import typing as t

from libvcs import GitSync, HgSync, SvnSync, exc
from libvcs.exc import InvalidVCS
from libvcs.url import registry as url_tools

if t.TYPE_CHECKING:
    from typing_extensions import TypeGuard

    from libvcs._internal.run import ProgressCallbackProtocol
    from libvcs._internal.types import StrPath, VCSLiteral


class VCSNoMatchFoundForUrl(exc.LibVCSException):
    def __init__(self, url: str, *args: object) -> None:
        return super().__init__(f"No VCS found for url: {url}")


class VCSMultipleMatchFoundForUrl(exc.LibVCSException):
    def __init__(self, url: str, *args: object) -> None:
        return super().__init__(f"Multiple VCS found for url: {url}")


class VCSNotSupported(exc.LibVCSException):
    def __init__(self, url: str, vcs: str, *args: object) -> None:
        return super().__init__(f"VCS '{vcs}' not supported, based on URL: {url}")


@t.overload
def create_project(
    *,
    url: str,
    path: StrPath,
    vcs: t.Literal["git"],
    progress_callback: ProgressCallbackProtocol | None = None,
    **kwargs: dict[t.Any, t.Any],
) -> GitSync: ...


@t.overload
def create_project(
    *,
    url: str,
    path: StrPath,
    vcs: t.Literal["svn"],
    progress_callback: ProgressCallbackProtocol | None = None,
    **kwargs: dict[t.Any, t.Any],
) -> SvnSync: ...


@t.overload
def create_project(
    *,
    url: str,
    path: StrPath,
    vcs: t.Literal["hg"],
    progress_callback: ProgressCallbackProtocol | None = ...,
    **kwargs: dict[t.Any, t.Any],
) -> HgSync: ...


@t.overload
def create_project(
    *,
    url: str,
    path: StrPath,
    vcs: None = None,
    progress_callback: ProgressCallbackProtocol | None = None,
    **kwargs: dict[t.Any, t.Any],
) -> GitSync | HgSync | SvnSync: ...


def create_project(
    *,
    url: str,
    path: StrPath,
    vcs: VCSLiteral | None = None,
    progress_callback: ProgressCallbackProtocol | None = None,
    **kwargs: dict[t.Any, t.Any],
) -> GitSync | HgSync | SvnSync:
    r"""Return an object representation of a VCS repository.

    Examples
    --------
    >>> from libvcs._internal.shortcuts import create_project
    >>> r = create_project(
    ...     url=f'file://{create_git_remote_repo()}',
    ...     vcs='git',
    ...     path=tmp_path
    ... )

    >>> isinstance(r, GitSync)
    True

    create_project can also guess VCS for certain URLs:

    >>> r = create_project(
    ...     # Note the git+ before the URL
    ...     url=f'git+file://{create_git_remote_repo()}',
    ...     path=tmp_path
    ... )

    >>> isinstance(r, GitSync)
    True

    It also supports unprefixed SSH-style Git URLs:

    >>> r = create_project(
    ...     url='git@github.com:tmux-python/tmuxp.git',
    ...     path=tmp_path
    ... )
    >>> isinstance(r, GitSync)
    True
    """
    if vcs is None:
        vcs_matches = url_tools.registry.match(url=url, is_explicit=True)

        if len(vcs_matches) == 0:
            raise VCSNoMatchFoundForUrl(url=url)
        if len(vcs_matches) > 1:
            raise VCSMultipleMatchFoundForUrl(url=url)

        assert vcs_matches[0].vcs is not None

        def is_vcs(val: t.Any) -> TypeGuard[VCSLiteral]:
            return isinstance(val, str) and val in {"git", "hg", "svn"}

        if is_vcs(vcs_matches[0].vcs):
            vcs = vcs_matches[0].vcs
        else:
            raise VCSNotSupported(url=url, vcs=vcs_matches[0].vcs)

    if vcs == "git":
        return GitSync(
            url=url,
            path=path,
            progress_callback=progress_callback,
            **kwargs,
        )
    if vcs == "hg":
        return HgSync(url=url, path=path, progress_callback=progress_callback, **kwargs)
    if vcs == "svn":
        return SvnSync(
            url=url,
            path=path,
            progress_callback=progress_callback,
            **kwargs,
        )
    msg = f"VCS {vcs} is not a valid VCS"
    raise InvalidVCS(msg)
