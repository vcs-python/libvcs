import pathlib

import pytest

from libvcs import GitProject, MercurialProject, SubversionProject
from libvcs.exc import InvalidPipURL, InvalidVCS
from libvcs.shortcuts import create_project, create_project_from_pip_url


@pytest.mark.parametrize(
    "repo_dict,repo_class,raises_exception",
    [
        ({"pip_url": "git+https://github.com/freebsd/freebsd.git"}, GitProject, False),
        (
            {"pip_url": "hg+https://bitbucket.org/birkenfeld/sphinx"},
            MercurialProject,
            False,
        ),
        (
            {"pip_url": "svn+http://svn.code.sf.net/p/docutils/code/trunk"},
            SubversionProject,
            False,
        ),
        (
            {"pip_url": "sv+http://svn.code.sf.net/p/docutils/code/trunk"},
            None,
            InvalidPipURL,
        ),
    ],
)
def test_create_project_from_pip_url(
    tmp_path: pathlib.Path, repo_dict, repo_class, raises_exception
):
    # add parent_dir via fixture
    repo_dict["dir"] = tmp_path / "repo_name"

    if raises_exception:
        with pytest.raises(raises_exception):
            create_project_from_pip_url(**repo_dict)
    else:
        repo = create_project_from_pip_url(**repo_dict)
        assert isinstance(repo, repo_class)


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
