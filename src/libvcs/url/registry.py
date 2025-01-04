"""Registry of VCS URL Parsers for libvcs."""

from __future__ import annotations

import typing as t

from libvcs._internal.module_loading import import_string

if t.TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from .base import URLProtocol

    ParserLazyMap: TypeAlias = dict[str, t.Union[type[URLProtocol], str]]
    ParserMap: TypeAlias = dict[str, type[URLProtocol]]

DEFAULT_PARSERS: ParserLazyMap = {
    "git": "libvcs.url.git.GitURL",
    "hg": "libvcs.url.hg.HgURL",
    "svn": "libvcs.url.svn.SvnURL",
}


class ParserMatch(t.NamedTuple):
    """Match or hit that suggests or identifies a VCS by URL Pattern."""

    vcs: str
    """VCS system matched"""
    match: URLProtocol
    """Matcher vcs detected with"""


class VCSRegistry:
    """Index of parsers."""

    parser_map: t.ClassVar[ParserMap] = {}

    def __init__(self, parsers: ParserLazyMap) -> None:
        for k, v in parsers.items():
            if isinstance(v, str):
                v = import_string(v)
            assert callable(v)
            self.parser_map[k] = v

    def match(
        self,
        url: str,
        is_explicit: bool | None = None,
    ) -> list[ParserMatch]:
        """Return a list of potential VCS' identified for a given URL."""
        matches: list[ParserMatch] = []
        for vcs, parser in self.parser_map.items():
            if parser.is_valid(url=url, is_explicit=is_explicit):
                matches.append(ParserMatch(vcs=vcs, match=parser(url)))
        return matches


registry = VCSRegistry(parsers=DEFAULT_PARSERS)
