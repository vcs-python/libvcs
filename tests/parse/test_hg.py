import typing

import pytest

from libvcs.parse.base import MatcherRegistry
from libvcs.parse.hg import DEFAULT_MATCHERS, PIP_DEFAULT_MATCHERS, HgURL
from libvcs.projects.hg import MercurialProject


class HgURLFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    hg_location: HgURL


TEST_FIXTURES: list[HgURLFixture] = [
    HgURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        hg_location=HgURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    HgURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        hg_location=HgURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,hg_location",
    TEST_FIXTURES,
)
def test_hg_location(
    url: str,
    is_valid: bool,
    hg_location: HgURL,
    hg_repo: MercurialProject,
):
    url = url.format(local_repo=hg_repo.dir)
    hg_location.url = hg_location.url.format(local_repo=hg_repo.dir)

    assert HgURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert HgURL(url) == hg_location


class HgURLKwargs(typing.TypedDict):
    url: str


class HgURLKwargsFixture(typing.NamedTuple):
    url: str
    is_valid: bool
    hg_location_kwargs: HgURLKwargs


#
#
# Extensibility: pip(1)
# w/ VCS prefixes, e.g. hg+https, hg+ssh, hg+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[HgURLKwargsFixture] = [
    HgURLKwargsFixture(
        url="hg+https://bitbucket.com/liuxinyu95/AlgoXY",
        is_valid=True,
        hg_location_kwargs=HgURLKwargs(
            url="hg+https://bitbucket.com/liuxinyu95/AlgoXY"
        ),
    ),
    HgURLKwargsFixture(
        url="hg+ssh://hg@bitbucket.com:tony/AlgoXY",
        is_valid=True,
        hg_location_kwargs=HgURLKwargs(url="hg+ssh://hg@bitbucket.com:tony/AlgoXY"),
    ),
    HgURLKwargsFixture(
        url="hg+file://{local_repo}",
        is_valid=True,
        hg_location_kwargs=HgURLKwargs(url="hg+file://{local_repo}"),
    ),
    # Incompatible
    HgURLKwargsFixture(
        url="hg+ssh://hg@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        hg_location_kwargs=HgURLKwargs(url="hg+ssh://hg@bitbucket.com/tony/AlgoXY"),
    ),
]


@pytest.mark.parametrize(
    "url,is_valid,hg_location_kwargs",
    PIP_TEST_FIXTURES,
)
def test_hg_location_extension_pip(
    url: str,
    is_valid: bool,
    hg_location_kwargs: HgURLKwargs,
    hg_repo: MercurialProject,
):
    class HgURLWithPip(HgURL):
        matchers = MatcherRegistry = MatcherRegistry(
            _matchers={m.label: m for m in [*DEFAULT_MATCHERS, *PIP_DEFAULT_MATCHERS]}
        )

    hg_location_kwargs["url"] = hg_location_kwargs["url"].format(local_repo=hg_repo.dir)
    url = url.format(local_repo=hg_repo.dir)
    hg_location = HgURLWithPip(**hg_location_kwargs)
    hg_location.url = hg_location.url.format(local_repo=hg_repo.dir)

    assert (
        HgURL.is_valid(url) != is_valid
    ), f"{url} compatibility should work with core, expects {not is_valid}"
    assert (
        HgURLWithPip.is_valid(url) == is_valid
    ), f"{url} compatibility should be {is_valid}"
    assert HgURLWithPip(url) == hg_location


class ToURLFixture(typing.NamedTuple):
    hg_location: HgURL
    expected: str


@pytest.mark.parametrize(
    "hg_location,expected",
    [
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            hg_location=HgURL(
                url="https://bitbucket.com/vcs-python/libvcs",
                scheme="https",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            hg_location=HgURL(
                url="https://bitbucket.com/vcs-python/libvcs",
                scheme="https",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
        #
        # SCP-style URLs:
        # e.g. 'ssh://hg@example.com/foo/bar'
        #
        ToURLFixture(
            expected="ssh://hg@bitbucket.com/liuxinyu95/AlgoXY",
            hg_location=HgURL(
                url="ssh://hg@bitbucket.com/liuxinyu95/AlgoXY",
                user="hg",
                scheme="ssh",
                hostname="bitbucket.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="ssh://username@bitbucket.com/vcs-python/libvcs",
            hg_location=HgURL(
                url="username@bitbucket.com/vcs-python/libvcs",
                user="username",
                scheme="ssh",
                hostname="bitbucket.com",
                path="vcs-python/libvcs",
            ),
        ),
    ],
)
def test_hg_to_url(
    expected: str,
    hg_location: HgURL,
    hg_repo: MercurialProject,
):
    """Test HgURL.to_url()"""
    hg_location.url = hg_location.url.format(local_repo=hg_repo.dir)

    assert hg_location.to_url() == expected
