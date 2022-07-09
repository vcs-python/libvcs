import typing

import pytest

from libvcs.parse.base import MatcherRegistry
from libvcs.parse.git import DEFAULT_MATCHERS, PIP_DEFAULT_MATCHERS, GitURL
from libvcs.projects.git import GitProject


class GitURLFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    git_location: GitURL


TEST_FIXTURES: list[GitURLFixture] = [
    GitURLFixture(
        url="https://github.com/vcs-python/libvcs.git",
        is_valid=True,
        git_location=GitURL(
            url="https://github.com/vcs-python/libvcs.git",
            scheme="https",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
    GitURLFixture(
        url="https://github.com/vcs-python/libvcs",
        is_valid=True,
        git_location=GitURL(
            url="https://github.com/vcs-python/libvcs",
            scheme="https",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
    #
    # SCP-style URLs:
    # e.g. 'git@example.com:foo/bar.git'
    #
    GitURLFixture(
        url="git@github.com:liuxinyu95/AlgoXY.git",
        is_valid=True,
        git_location=GitURL(
            url="git@github.com:liuxinyu95/AlgoXY.git",
            scheme=None,
            hostname="github.com",
            path="liuxinyu95/AlgoXY",
        ),
    ),
    GitURLFixture(
        url="git@github.com:vcs-python/libvcs.git",
        is_valid=True,
        git_location=GitURL(
            url="git@github.com:vcs-python/libvcs.git",
            scheme="https",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,git_location",
    TEST_FIXTURES,
)
def test_git_location(
    url: str,
    is_valid: bool,
    git_location: GitURL,
    git_repo: GitProject,
):
    url = url.format(local_repo=git_repo.dir)
    git_location.url = git_location.url.format(local_repo=git_repo.dir)

    assert GitURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert GitURL(url) == git_location


class GitURLKwargs(typing.TypedDict):
    url: str


class GitURLKwargsFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    git_location_kwargs: GitURLKwargs


#
#
# Extensibility: pip(1)
# w/ VCS prefixes, e.g. git+https, git+ssh, git+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[GitURLKwargsFixture] = [
    GitURLKwargsFixture(
        url="git+https://github.com/liuxinyu95/AlgoXY.git",
        is_valid=True,
        git_location_kwargs=GitURLKwargs(
            url="git+https://github.com/liuxinyu95/AlgoXY.git"
        ),
    ),
    GitURLKwargsFixture(
        url="git+ssh://git@github.com:tony/AlgoXY.git",
        is_valid=True,
        git_location_kwargs=GitURLKwargs(
            url="git+ssh://git@github.com:tony/AlgoXY.git"
        ),
    ),
    GitURLKwargsFixture(
        url="git+file://{local_repo}",
        is_valid=True,
        git_location_kwargs=GitURLKwargs(url="git+file://{local_repo}"),
    ),
    # Incompatible
    GitURLKwargsFixture(
        url="git+ssh://git@github.com/tony/AlgoXY.git",
        is_valid=True,
        git_location_kwargs=GitURLKwargs(
            url="git+ssh://git@github.com/tony/AlgoXY.git"
        ),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,git_location_kwargs",
    PIP_TEST_FIXTURES,
)
def test_git_location_extension_pip(
    url: str,
    is_valid: bool,
    git_location_kwargs: GitURLKwargs,
    git_repo: GitProject,
):
    class GitURLWithPip(GitURL):
        matchers = MatcherRegistry = MatcherRegistry(
            _matchers={m.label: m for m in [*DEFAULT_MATCHERS, *PIP_DEFAULT_MATCHERS]}
        )

    git_location_kwargs["url"] = git_location_kwargs["url"].format(
        local_repo=git_repo.dir
    )
    url = url.format(local_repo=git_repo.dir)
    git_location = GitURLWithPip(**git_location_kwargs)
    git_location.url = git_location.url.format(local_repo=git_repo.dir)

    assert (
        GitURL.is_valid(url) != is_valid
    ), f"{url} compatibility should work with core, expects {not is_valid}"
    assert (
        GitURLWithPip.is_valid(url) == is_valid
    ), f"{url} compatibility should be {is_valid}"
    assert GitURLWithPip(url) == git_location


class ToURLFixture(typing.NamedTuple):
    git_location: GitURL
    expected: str


@pytest.mark.parametrize(
    "git_location,expected",
    [
        ToURLFixture(
            expected="https://github.com/vcs-python/libvcs.git",
            git_location=GitURL(
                url="https://github.com/vcs-python/libvcs.git",
                scheme="https",
                hostname="github.com",
                path="vcs-python/libvcs",
            ),
        ),
        ToURLFixture(
            expected="https://github.com/vcs-python/libvcs",
            git_location=GitURL(
                url="https://github.com/vcs-python/libvcs",
                scheme="https",
                hostname="github.com",
                path="vcs-python/libvcs",
            ),
        ),
        #
        # SCP-style URLs:
        # e.g. 'git@example.com:foo/bar.git'
        #
        ToURLFixture(
            expected="git@github.com:liuxinyu95/AlgoXY.git",
            git_location=GitURL(
                url="git@github.com:liuxinyu95/AlgoXY.git",
                scheme=None,
                hostname="github.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="git@github.com:vcs-python/libvcs.git",
            git_location=GitURL(
                url="git@github.com:vcs-python/libvcs.git",
                scheme="https",
                hostname="github.com",
                path="vcs-python/libvcs",
            ),
        ),
    ],
)
def test_git_to_url(
    expected: str,
    git_location: GitURL,
    git_repo: GitProject,
):
    """Test GitURL.to_url()"""
    git_location.url = git_location.url.format(local_repo=git_repo.dir)

    assert git_location.to_url() == expected
