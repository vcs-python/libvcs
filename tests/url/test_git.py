"""Tests for GitURL."""
import typing

import pytest

from libvcs.sync.git import GitSync
from libvcs.url.base import RuleMap
from libvcs.url.git import DEFAULT_RULES, PIP_DEFAULT_RULES, GitBaseURL, GitURL


class GitURLFixture(typing.NamedTuple):
    """Test fixture for GitURL."""

    url: str
    is_valid: bool
    git_url: GitURL


TEST_FIXTURES: list[GitURLFixture] = [
    GitURLFixture(
        url="https://github.com/vcs-python/libvcs.git",
        is_valid=True,
        git_url=GitURL(
            url="https://github.com/vcs-python/libvcs.git",
            scheme="https",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
    GitURLFixture(
        url="https://github.com/vcs-python/libvcs",
        is_valid=True,
        git_url=GitURL(
            url="https://github.com/vcs-python/libvcs",
            scheme="https",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
    GitURLFixture(
        url="https://github.com:7999/vcs-python/libvcs",
        is_valid=True,
        git_url=GitURL(
            url="https://github.com:7999/vcs-python/libvcs",
            scheme="https",
            hostname="github.com",
            port=7999,
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
        git_url=GitURL(
            url="git@github.com:liuxinyu95/AlgoXY.git",
            scheme=None,
            hostname="github.com",
            path="liuxinyu95/AlgoXY",
        ),
    ),
    GitURLFixture(
        url="git@github.com:vcs-python/libvcs.git",
        is_valid=True,
        git_url=GitURL(
            url="git@github.com:vcs-python/libvcs.git",
            hostname="github.com",
            path="vcs-python/libvcs",
        ),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,git_url",
    TEST_FIXTURES,
)
def test_git_url(
    url: str,
    is_valid: bool,
    git_url: GitURL,
    git_repo: GitSync,
) -> None:
    """Tests for GitURL."""
    url = url.format(local_repo=git_repo.path)
    git_url.url = git_url.url.format(local_repo=git_repo.path)

    assert GitURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert GitURL(url) == git_url


class GitURLKwargs(typing.TypedDict):
    """GitURL with keyword arguments."""

    url: str


class GitURLKwargsFixture(typing.NamedTuple):
    """Test fixture for GitURL with keyword arguments."""

    url: str
    is_valid: bool
    git_url_kwargs: GitURLKwargs


#
# Extensibility patterns, via pip:
# w/ VCS prefixes, e.g. git+https, git+ssh, git+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[GitURLKwargsFixture] = [
    GitURLKwargsFixture(
        url="git+https://github.com/liuxinyu95/AlgoXY.git",
        is_valid=True,
        git_url_kwargs=GitURLKwargs(url="git+https://github.com/liuxinyu95/AlgoXY.git"),
    ),
    GitURLKwargsFixture(
        url="git+ssh://git@github.com:tony/AlgoXY.git",
        is_valid=True,
        git_url_kwargs=GitURLKwargs(url="git+ssh://git@github.com:tony/AlgoXY.git"),
    ),
    GitURLKwargsFixture(
        url="git+file://{local_repo}",
        is_valid=True,
        git_url_kwargs=GitURLKwargs(url="git+file://{local_repo}"),
    ),
    # Incompatible
    GitURLKwargsFixture(
        url="git+ssh://git@github.com/tony/AlgoXY.git",
        is_valid=True,
        git_url_kwargs=GitURLKwargs(url="git+ssh://git@github.com/tony/AlgoXY.git"),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,git_url_kwargs",
    PIP_TEST_FIXTURES,
)
def test_git_url_extension_pip(
    url: str,
    is_valid: bool,
    git_url_kwargs: GitURLKwargs,
    git_repo: GitSync,
) -> None:
    """Test GitURL external extension from pip."""

    class GitURLWithPip(GitBaseURL):
        rule_map = RuleMap(
            _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
        )

    git_url_kwargs["url"] = git_url_kwargs["url"].format(local_repo=git_repo.path)
    url = url.format(local_repo=git_repo.path)
    git_url = GitURLWithPip(**git_url_kwargs)
    git_url.url = git_url.url.format(local_repo=git_repo.path)

    assert (
        GitBaseURL.is_valid(url) != is_valid
    ), f"{url} compatibility should work with core, expects {not is_valid}"
    assert (
        GitURLWithPip.is_valid(url) == is_valid
    ), f"{url} compatibility should be {is_valid}"
    assert GitURLWithPip(url) == git_url


class ToURLFixture(typing.NamedTuple):
    """Test fixture for GitURL.to_url()."""

    git_url: GitURL
    expected: str


@pytest.mark.parametrize(
    "git_url,expected",
    [
        ToURLFixture(
            expected="https://github.com/vcs-python/libvcs.git",
            git_url=GitURL(
                url="https://github.com/vcs-python/libvcs.git",
                scheme="https",
                hostname="github.com",
                path="vcs-python/libvcs",
            ),
        ),
        ToURLFixture(
            expected="https://github.com/vcs-python/libvcs",
            git_url=GitURL(
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
            git_url=GitURL(
                url="git@github.com:liuxinyu95/AlgoXY.git",
                scheme=None,
                hostname="github.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="https://github.com/vcs-python/libvcs.git",
            git_url=GitURL(
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
    git_url: GitURL,
    git_repo: GitSync,
) -> None:
    """Test GitURL.to_url()."""
    git_url.url = git_url.url.format(local_repo=git_repo.path)

    assert git_url.to_url() == expected


class RevFixture(typing.NamedTuple):
    """Test fixture for GitURL with revisions."""

    git_url_kwargs: GitURLKwargs
    expected: typing.Optional[str]
    # Expected revision / branch / tag


@pytest.mark.parametrize(
    "git_url_kwargs,expected",
    [
        RevFixture(
            expected=None,
            git_url_kwargs=GitURLKwargs(
                url="git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git",
            ),
        ),
        RevFixture(
            expected="eucalyptus",
            git_url_kwargs=GitURLKwargs(
                url="git+ssh://git@bitbucket.example.com:7999/PROJ/repo.git@eucalyptus",
            ),
        ),
        RevFixture(
            expected="build.2600-whistler",
            git_url_kwargs=GitURLKwargs(
                url="git+https://github.com/PROJ/repo.git@build.2600-whistler",
            ),
        ),
    ],
)
def test_git_revs(
    expected: str,
    git_url_kwargs: GitURLKwargs,
) -> None:
    """Tests for GitURL with revisions."""

    class GitURLWithPip(GitURL):
        rule_map = RuleMap(
            _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
        )

    git_url = GitURLWithPip(**git_url_kwargs)
    assert git_url.rev == expected
