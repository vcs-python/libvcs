"""Tests for URL Registry."""

from __future__ import annotations

import typing as t

import pytest

from libvcs.url import registry
from libvcs.url.git import GitURL
from libvcs.url.hg import HgURL
from libvcs.url.svn import SvnURL

if t.TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import TypeAlias

    ParserMatchLazy: TypeAlias = Callable[[str], registry.ParserMatch]
    DetectVCSFixtureExpectedMatch: TypeAlias = t.Union[
        registry.ParserMatch,
        ParserMatchLazy,
    ]


class DetectVCSFixture(t.NamedTuple):
    """Test VCS Detection fixture."""

    url: str
    expected_matches_lazy: list[DetectVCSFixtureExpectedMatch]
    is_explicit: bool


TEST_FIXTURES: list[DetectVCSFixture] = [
    *[
        DetectVCSFixture(
            url=url,
            expected_matches_lazy=[
                lambda url: registry.ParserMatch(vcs="git", match=GitURL(url)),
            ],
            is_explicit=True,
        )
        for url in [
            "git+https://github.com/vcs-python/libvcs",
            "git+https://github.com/vcs-python/libvcs.git",
            "git+https://github.com:vcs-python/libvcs.git",
            "git+ssh://git@github.com:vcs-python/libvcs.git",
            "git+ssh://git@github.com:vcs-python/libvcs",
            "git+ssh://git@github.com/tony/ScreenToGif.git",
            "git+https://github.com/nltk/nltk.git",
            "git+https://github.com/nltk/nltk",
            "codecommit://MyDemoRepo",
            "codecommit::ap-northeast-1://MyDemoRepo",
            "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/test",
            "ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/test",
            # plain SCP-style Git URLs should be recognized explicitly
            "git@github.com:tmux-python/tmuxp.git",
        ]
    ],
    *[
        DetectVCSFixture(
            url=url,
            expected_matches_lazy=[
                lambda url: registry.ParserMatch(vcs="hg", match=HgURL(url)),
            ],
            is_explicit=True,
        )
        for url in [
            "hg+http://hg.example.com/MyProject@da39a3ee5e6b",
            "hg+ssh://hg.example.com:MyProject@da39a3ee5e6b",
            "hg+https://hg.mozilla.org/mozilla-central/",
        ]
    ],
    *[
        DetectVCSFixture(
            url=url,
            expected_matches_lazy=[
                lambda url: registry.ParserMatch(vcs="svn", match=SvnURL(url)),
            ],
            is_explicit=True,
        )
        for url in [
            "svn+http://svn.example.com/MyProject@da39a3ee5e6b",
            "svn+ssh://svn.example.com:MyProject@da39a3ee5e6b",
            "svn+ssh://svn.example.com:MyProject@da39a3ee5e6b",
        ]
    ],
]


@pytest.mark.parametrize(
    list(DetectVCSFixture._fields),
    TEST_FIXTURES,
)
def test_registry(
    url: str,
    expected_matches_lazy: list[DetectVCSFixtureExpectedMatch],
    is_explicit: bool,
) -> None:
    """Test URL detection registry."""
    assert url
    assert registry.registry

    matches = registry.registry.match(url, is_explicit=is_explicit)

    # Just add water
    expected_matches: list[DetectVCSFixtureExpectedMatch] = []
    for expected_match in expected_matches_lazy:
        if callable(expected_match):
            assert callable(expected_match)
            expected_matches.append(expected_match(url))

    assert matches == expected_matches
