"""Tests for libvcs.shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, TypeVar

import pytest

from libvcs import GitSync, HgSync, SvnSync
from libvcs._internal.shortcuts import create_project
from libvcs.exc import InvalidVCS

if TYPE_CHECKING:
    import pathlib

    from libvcs._internal.run import ProgressCallbackProtocol
    from libvcs._internal.types import StrPath


class CreateProjectKwargsDict(TypedDict, total=False):
    """Test fixtures for create_project()."""

    url: str
    path: StrPath
    vcs: Literal["git"]
    progress_callback: ProgressCallbackProtocol | None


E = TypeVar("E", bound=BaseException)


@pytest.mark.parametrize(
    ("repo_dict", "repo_class", "raises_exception"),
    [
        (
            {"url": "https://github.com/freebsd/freebsd.git", "vcs": "git"},
            GitSync,
            None,
        ),
        (
            {"url": "https://bitbucket.org/birkenfeld/sphinx", "vcs": "hg"},
            HgSync,
            None,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svn"},
            SvnSync,
            None,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svna"},
            None,
            InvalidVCS,
        ),
    ],
)
def test_create_project(
    tmp_path: pathlib.Path,
    repo_dict: CreateProjectKwargsDict,
    repo_class: type[SvnSync | GitSync | HgSync],
    raises_exception: None | type[E] | tuple[type[E], ...],
) -> None:
    """Tests for create_project()."""
    # add parent_dir via fixture
    repo_dict["path"] = tmp_path / "repo_name"

    if raises_exception is not None:
        with pytest.raises(raises_exception):
            create_project(**repo_dict)
    else:
        repo = create_project(**repo_dict)
        assert isinstance(repo, repo_class)
