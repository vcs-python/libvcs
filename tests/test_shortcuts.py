import pathlib

import pytest

from libvcs import GitProject, MercurialProject, SubversionProject
from libvcs._internal.shortcuts import create_project
from libvcs.exc import InvalidVCS


@pytest.mark.parametrize(
    "repo_dict,repo_class,raises_exception",
    [
        (
            {"url": "https://github.com/freebsd/freebsd.git", "vcs": "git"},
            GitProject,
            False,
        ),
        (
            {"url": "https://bitbucket.org/birkenfeld/sphinx", "vcs": "hg"},
            MercurialProject,
            False,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svn"},
            SubversionProject,
            False,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svna"},
            None,
            InvalidVCS,
        ),
    ],
)
def test_create_project(
    tmp_path: pathlib.Path, repo_dict, repo_class, raises_exception
):
    # add parent_dir via fixture
    repo_dict["dir"] = tmp_path / "repo_name"

    if raises_exception:
        with pytest.raises(raises_exception):
            create_project(**repo_dict)
    else:
        repo = create_project(**repo_dict)
        assert isinstance(repo, repo_class)
