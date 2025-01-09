"""Tests for mercurial URL module."""

from __future__ import annotations

import typing

import pytest

from libvcs.url.base import RuleMap
from libvcs.url.hg import DEFAULT_RULES, PIP_DEFAULT_RULES, HgBaseURL, HgURL

if typing.TYPE_CHECKING:
    import pathlib

    from libvcs.sync.hg import HgSync


@pytest.fixture(autouse=True)
def set_hgconfig(
    set_hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Set mercurial configuration."""
    return set_hgconfig


class HgURLFixture(typing.NamedTuple):
    """Test fixture for HgURL."""

    url: str
    is_valid: bool
    hg_url: HgURL


TEST_FIXTURES: list[HgURLFixture] = [
    HgURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        hg_url=HgURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
    HgURLFixture(
        url="https://bitbucket.com/vcs-python/libvcs",
        is_valid=True,
        hg_url=HgURL(
            url="https://bitbucket.com/vcs-python/libvcs",
            scheme="https",
            hostname="bitbucket.com",
            path="vcs-python/libvcs",
        ),
    ),
]


@pytest.mark.parametrize(
    ("url", "is_valid", "hg_url"),
    TEST_FIXTURES,
)
def test_hg_url(
    url: str,
    is_valid: bool,
    hg_url: HgURL,
    hg_repo: HgSync,
) -> None:
    """Test HgURL."""
    url = url.format(local_repo=hg_repo.path)
    hg_url.url = hg_url.url.format(local_repo=hg_repo.path)

    assert HgURL.is_valid(url) == is_valid, f"{url} compatibility should be {is_valid}"
    assert HgURL(url) == hg_url


class HgURLKwargs(typing.TypedDict):
    """HgURL with keyword arguments."""

    url: str


class HgURLKwargsFixture(typing.NamedTuple):
    """Test fixture for HgURL w/ extra keyword arguments."""

    url: str
    is_valid: bool
    hg_url_kwargs: HgURLKwargs


#
# Extensibility patterns, via pip:
# w/ VCS prefixes, e.g. hg+https, hg+ssh, hg+file
# https://pip.pypa.io/en/stable/topics/vcs-support/
#
#
PIP_TEST_FIXTURES: list[HgURLKwargsFixture] = [
    HgURLKwargsFixture(
        url="hg+https://bitbucket.com/liuxinyu95/AlgoXY",
        is_valid=True,
        hg_url_kwargs=HgURLKwargs(url="hg+https://bitbucket.com/liuxinyu95/AlgoXY"),
    ),
    HgURLKwargsFixture(
        url="hg+ssh://hg@bitbucket.com:tony/AlgoXY",
        is_valid=True,
        hg_url_kwargs=HgURLKwargs(url="hg+ssh://hg@bitbucket.com:tony/AlgoXY"),
    ),
    HgURLKwargsFixture(
        url="hg+file://{local_repo}",
        is_valid=True,
        hg_url_kwargs=HgURLKwargs(url="hg+file://{local_repo}"),
    ),
    # Incompatible
    HgURLKwargsFixture(
        url="hg+ssh://hg@bitbucket.com/tony/AlgoXY",
        is_valid=True,
        hg_url_kwargs=HgURLKwargs(url="hg+ssh://hg@bitbucket.com/tony/AlgoXY"),
    ),
]


@pytest.mark.parametrize(
    ("url", "is_valid", "hg_url_kwargs"),
    PIP_TEST_FIXTURES,
)
def test_hg_url_extension_pip(
    url: str,
    is_valid: bool,
    hg_url_kwargs: HgURLKwargs,
    hg_repo: HgSync,
) -> None:
    """Tests for HgURL with pip rules."""

    class HgURLWithPip(HgURL):
        rule_map = RuleMap(
            _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
        )

    hg_url_kwargs["url"] = hg_url_kwargs["url"].format(local_repo=hg_repo.path)
    url = url.format(local_repo=hg_repo.path)
    hg_url = HgURLWithPip(**hg_url_kwargs)
    hg_url.url = hg_url.url.format(local_repo=hg_repo.path)

    assert HgBaseURL.is_valid(url) != is_valid, (
        f"{url} compatibility should work with core, expects {not is_valid}"
    )
    assert HgURLWithPip.is_valid(url) == is_valid, (
        f"{url} compatibility should be {is_valid}"
    )
    assert HgURLWithPip(url) == hg_url


class ToURLFixture(typing.NamedTuple):
    """Test fixture for HgURL.to_url()."""

    hg_url: HgURL
    expected: str


@pytest.mark.parametrize(
    ("hg_url", "expected"),
    [
        ToURLFixture(
            expected="https://bitbucket.com/vcs-python/libvcs",
            hg_url=HgURL(
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
            hg_url=HgURL(
                url="ssh://hg@bitbucket.com/liuxinyu95/AlgoXY",
                user="hg",
                scheme="ssh",
                hostname="bitbucket.com",
                path="liuxinyu95/AlgoXY",
            ),
        ),
        ToURLFixture(
            expected="ssh://username@bitbucket.com/vcs-python/libvcs",
            hg_url=HgURL(
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
    hg_url: HgURL,
    hg_repo: HgSync,
) -> None:
    """Test HgURL.to_url()."""
    hg_url.url = hg_url.url.format(local_repo=hg_repo.path)

    assert hg_url.to_url() == expected
