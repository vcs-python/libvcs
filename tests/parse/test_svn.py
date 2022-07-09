import typing

import pytest

from libvcs.parse.base import MatcherRegistry
from libvcs.parse.svn import DEFAULT_MATCHERS, PIP_DEFAULT_MATCHERS, SvnURL
from libvcs.projects.svn import SubversionProject


class SvnURLFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    svn_location: SvnURL


# Valid schemes for svn(1).
# See Table 1.1 Repository access URLs in SVN Book
# https://svnbook.red-bean.com/nightly/en/svn.basic.in-action.html#svn.basic.in-action.wc.tbl-1
TEST_FIXTURES: list[SvnURLFixture] = [
    SvnURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        svn_location=SvnURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    SvnURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        svn_location=SvnURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    SvnURLFixture(
        url="svn://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_location=SvnURL(
            url="svn://svn@bitbucket.com/tony/AlgoXY",
            scheme="https",
            hostname="bitbucket.com",
            path="tony/AlgoXY",
        ),
    ),
    SvnURLFixture(
        url="svn+ssh://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_location=SvnURL(
            url="svn+ssh://svn@bitbucket.com/tony/AlgoXY",
            scheme="https",
            hostname="bitbucket.com",
            path="tony/AlgoXY",
        ),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,svn_location",
    TEST_FIXTURES,
)
def test_svn_location(
    url: str,
    is_valid: bool,
    svn_location: SvnURL,
    svn_repo: SubversionProject,
):
    url = url.format(local_repo=svn_repo.dir)
    svn_location.url = svn_location.url.format(local_repo=svn_repo.dir)

    assert SvnURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert SvnURL(url) == svn_location


class SvnURLKwargs(typing.TypedDict):
    url: str


class SvnURLKwargsFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    svn_location_kwargs: SvnURLKwargs


#
#
# Extensibility: pip(1)
# w/ VCS prefixes, e.g. svn+https, svn+ssh, svn+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[SvnURLKwargsFixture] = [
    SvnURLKwargsFixture(
        url="svn+http://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_location_kwargs=SvnURLKwargs(
            url="svn+http://svn@bitbucket.com/tony/AlgoXY"
        ),
    ),
    SvnURLKwargsFixture(
        url="svn+https://svn@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        svn_location_kwargs=SvnURLKwargs(
            url="svn+https://svn@bitbucket.com/tony/AlgoXY"
        ),
    ),
    SvnURLKwargsFixture(
        url="svn+file://{local_repo}",
        is_valid=True,
        svn_location_kwargs=SvnURLKwargs(url="svn+file://{local_repo}"),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,svn_location_kwargs",
    PIP_TEST_FIXTURES,
)
def test_svn_location_extension_pip(
    url: str,
    is_valid: bool,
    svn_location_kwargs: SvnURLKwargs,
    svn_repo: SubversionProject,
):
    class SvnURLWithPip(SvnURL):
        matchers = MatcherRegistry = MatcherRegistry(
            _matchers={m.label: m for m in [*DEFAULT_MATCHERS, *PIP_DEFAULT_MATCHERS]}
        )

    svn_location_kwargs["url"] = svn_location_kwargs["url"].format(
        local_repo=svn_repo.dir
    )
    url = url.format(local_repo=svn_repo.dir)
    svn_location = SvnURLWithPip(**svn_location_kwargs)
    svn_location.url = svn_location.url.format(local_repo=svn_repo.dir)

    assert (
        SvnURL.is_valid(url) != is_valid
    ), f"{url} compatibility should work with core, expects {not is_valid}"
    assert (
        SvnURLWithPip.is_valid(url) == is_valid
    ), f"{url} compatibility should be {is_valid}"
    assert SvnURLWithPip(url) == svn_location


class ToURLFixture(typing.NamedTuple):
    svn_location: SvnURL
    expected: str


@pytest.mark.parametrize(
    "svn_location,expected",
    [
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            svn_location=SvnURL(
                url="https://bitbucket.com/vcs-python/libvcs",
                scheme="https",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            svn_location=SvnURL(
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
            svn_location=SvnURL(
                url="ssh://svn@bitbucket.com/liuxinyu95/AlgoXY",
                user="svn",
                scheme="ssh",
                hostname="bitbucket.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="ssh://username@bitbucket.com/vcs-python/libvcs",
            svn_location=SvnURL(
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
    svn_location: SvnURL,
    svn_repo: SubversionProject,
):
    """Test SvnURL.to_url()"""
    svn_location.url = svn_location.url.format(local_repo=svn_repo.dir)

    assert svn_location.to_url() == expected
