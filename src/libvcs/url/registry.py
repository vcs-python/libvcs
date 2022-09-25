import typing as t

from libvcs._internal.module_loading import import_string

from .base import URLProtocol

if t.TYPE_CHECKING:
    from typing_extensions import TypeAlias

    ParserLazyMap: TypeAlias = t.Dict[str, t.Union[t.Type[URLProtocol], str]]
    ParserMap: TypeAlias = t.Dict[str, t.Type[URLProtocol]]

DEFAULT_PARSERS: "ParserLazyMap" = {
    "git": "libvcs.url.git.GitURL",
    "hg": "libvcs.url.hg.HgURL",
    "svn": "libvcs.url.svn.SvnURL",
}


class ParserMatch(t.NamedTuple):
    vcs: str
    """VCS system matched"""
    match: URLProtocol
    """Matcher vcs detected with"""


class VCSRegistry:
    """Index of parsers"""

    parser_map: t.ClassVar["ParserMap"] = {}

    def __init__(self, parsers: "ParserLazyMap"):
        for k, v in parsers.items():
            if isinstance(v, str):
                v = import_string(v)
            assert callable(v)
            self.parser_map[k] = v

    def match(
        self, url: str, is_explicit: t.Optional[bool] = None
    ) -> t.List["ParserMatch"]:
        matches: t.List[ParserMatch] = []
        for vcs, parser in self.parser_map.items():
            if parser.is_valid(url=url, is_explicit=is_explicit):
                matches.append(ParserMatch(vcs=vcs, match=parser(url)))
        return matches


registry = VCSRegistry(parsers=DEFAULT_PARSERS)
