"""Tests for SVNUrl."""

from __future__ import annotations

import typing

import pytest

from libvcs.url.base import RuleMap
from libvcs.url.svn import DEFAULT_RULES, PIP_DEFAULT_RULES, SvnBaseURL, SvnURL

if typing.TYPE_CHECKING:
    from libvcs.sync.svn import SvnSync


class SvnURLFixture(typing.NamedTuple):
    """Test fixture for SvnURL."""

    url: str
    is_valid: bool
    svn_url: SvnURL


# Valid schemes for svn(1).
# See Table 1.1 Repository access URLs in SVN Book
# https://svnbook.red-bean.com/nightly/en/svn.basic.in-action.html#svn.basic.in-action.wc.tbl-1
TEST_FIXTURES: list[SvnURLFixture] = [
    SvnURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        svn_url=SvnURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    SvnURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        svn_url=SvnURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    SvnURLFixture(
        url="svn://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_url=SvnURL(
            url="svn://svn@bitbucket.com/tony/AlgoXY",
            scheme="https",
            hostname="bitbucket.com",
            path="tony/AlgoXY",
        ),
    ),
    SvnURLFixture(
        url="svn+ssh://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_url=SvnURL(
            url="svn+ssh://svn@bitbucket.com/tony/AlgoXY",
            scheme="https",
            hostname="bitbucket.com",
            path="tony/AlgoXY",
        ),
    ),
]


@pytest.mark.parametrize(
    ("url", "is_valid", "svn_url"),
    TEST_FIXTURES,
)
def test_svn_url(
    url: str,
    is_valid: bool,
    svn_url: SvnURL,
    svn_repo: SvnSync,
) -> None:
    """Test SvnURL."""
    url = url.format(local_repo=svn_repo.path)
    svn_url.url = svn_url.url.format(local_repo=svn_repo.path)

    assert SvnURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert SvnURL(url) == svn_url


class SvnURLKwargs(typing.TypedDict):
    """SvnURL dictionary with keyword arguments."""

    url: str


class SvnURLKwargsFixture(typing.NamedTuple):
    """Test fixture for SvnURL with keyword arguments."""

    url: str
    is_valid: bool
    svn_url_kwargs: SvnURLKwargs


#
# Extensibility patterns, via pip:
# w/ VCS prefixes, e.g. svn+https, svn+ssh, svn+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[SvnURLKwargsFixture] = [
    SvnURLKwargsFixture(
        url="svn+http://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_url_kwargs=SvnURLKwargs(url="svn+http://svn@bitbucket.com/tony/AlgoXY"),
    ),
    SvnURLKwargsFixture(
        url="svn+https://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_url_kwargs=SvnURLKwargs(url="svn+https://svn@bitbucket.com/tony/AlgoXY"),
    ),
    SvnURLKwargsFixture(
        url="svn+file://{local_repo}",
        is_valid=True,
        svn_url_kwargs=SvnURLKwargs(url="svn+file://{local_repo}"),
    ),
]


@pytest.mark.parametrize(
    ("url", "is_valid", "svn_url_kwargs"),
    PIP_TEST_FIXTURES,
)
def test_svn_url_extension_pip(
    url: str,
    is_valid: bool,
    svn_url_kwargs: SvnURLKwargs,
    svn_repo: SvnSync,
) -> None:
    """Test SvnURL external extension from pip."""

    class SvnURLWithPip(SvnURL):
        rule_map = RuleMap(
            _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
        )

    svn_url_kwargs["url"] = svn_url_kwargs["url"].format(local_repo=svn_repo.path)
    url = url.format(local_repo=svn_repo.path)
    svn_url = SvnURLWithPip(**svn_url_kwargs)
    svn_url.url = svn_url.url.format(local_repo=svn_repo.path)

    assert SvnBaseURL.is_valid(url) != is_valid, (
        f"{url} compatibility should work with core, expects {not is_valid}"
    )
    assert SvnURL.is_valid(url) == is_valid, (
        f"{url} compatibility should work with core, expects {not is_valid}"
    )
    assert SvnURLWithPip.is_valid(url) == is_valid, (
        f"{url} compatibility should be {is_valid}"
    )
    assert SvnURLWithPip(url) == svn_url


class ToURLFixture(typing.NamedTuple):
    """Test fixture for SVN URL conversion."""

    svn_url: SvnURL
    expected: str


@pytest.mark.parametrize(
    ("svn_url", "expected"),
    [
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            svn_url=SvnURL(
                url="https://bitbucket.com/vcs-python/libvcs",
                scheme="https",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
        #
        # SCP-style URLs:
        # e.g. 'ssh://svn@example.com/foo/bar'
        #
        ToURLFixture(
            expected="ssh://svn@bitbucket.com/liuxinyu95/AlgoXY",
            svn_url=SvnURL(
                url="ssh://svn@bitbucket.com/liuxinyu95/AlgoXY",
                user="svn",
                scheme="ssh",
                hostname="bitbucket.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="ssh://username@bitbucket.com/vcs-python/libvcs",
            svn_url=SvnURL(
                url="username@bitbucket.com/vcs-python/libvcs",
                user="username",
                scheme="ssh",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
    ],
)
def test_svn_to_url(
    expected: str,
    svn_url: SvnURL,
    svn_repo: SvnSync,
) -> None:
    """Test SvnURL.to_url()."""
    svn_url.url = svn_url.url.format(local_repo=svn_repo.path)

    assert svn_url.to_url() == expected
