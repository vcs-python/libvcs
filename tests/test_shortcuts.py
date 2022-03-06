import pathlib

import pytest

from libvcs import GitRepo, MercurialRepo, SubversionRepo
from libvcs.exc import InvalidPipURL, InvalidVCS
from libvcs.shortcuts import create_repo, create_repo_from_pip_url


@pytest.mark.parametrize(
    "repo_dict,repo_class,raises_exception",
    [
        ({"pip_url": "git+https://github.com/freebsd/freebsd.git"}, GitRepo, False),
        (
            {"pip_url": "hg+https://bitbucket.org/birkenfeld/sphinx"},
            MercurialRepo,
            False,
        ),
        (
            {"pip_url": "svn+http://svn.code.sf.net/p/docutils/code/trunk"},
            SubversionRepo,
            False,
        ),
        (
            {"pip_url": "sv+http://svn.code.sf.net/p/docutils/code/trunk"},
            None,
            InvalidPipURL,
        ),
    ],
)
def test_create_repo_from_pip_url(
    tmp_path: pathlib.Path, repo_dict, repo_class, raises_exception
):
    # add parent_dir via fixture
    repo_dict["repo_dir"] = tmp_path / "repo_name"

    if raises_exception:
        with pytest.raises(raises_exception):
            create_repo_from_pip_url(**repo_dict)
    else:
        repo = create_repo_from_pip_url(**repo_dict)
        assert isinstance(repo, repo_class)


@pytest.mark.parametrize(
    "repo_dict,repo_class,raises_exception",
    [
        (
            {"url": "https://github.com/freebsd/freebsd.git", "vcs": "git"},
            GitRepo,
            False,
        ),
        (
            {"url": "https://bitbucket.org/birkenfeld/sphinx", "vcs": "hg"},
            MercurialRepo,
            False,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svn"},
            SubversionRepo,
            False,
        ),
        (
            {"url": "http://svn.code.sf.net/p/docutils/code/trunk", "vcs": "svna"},
            None,
            InvalidVCS,
        ),
    ],
)
def test_create_repo(tmp_path: pathlib.Path, repo_dict, repo_class, raises_exception):
    # add parent_dir via fixture
    repo_dict["repo_dir"] = tmp_path / "repo_name"

    if raises_exception:
        with pytest.raises(raises_exception):
            create_repo(**repo_dict)
    else:
        repo = create_repo(**repo_dict)
        assert isinstance(repo, repo_class)
