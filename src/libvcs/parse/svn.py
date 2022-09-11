"""This module is an all-in-one parser and validator for Subversion URLs.

- Detection: :meth:`SvnURL.is_valid()`
- Parse: :class:`SvnURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``svn(1)`` URL: :meth:`SvnURL.to_url()`
- Extendable via :class:`~libvcs.parse.base.MatcherRegistry`,
  :class:`~libvcs.parse.base.Matcher`

.. Note::

   Subversion isn't seen as often these days, can you "rage against the dying of the
   light" and assure its light is not extinguished? Help assure SVN URL parsing is
   correct and robust. Visit the `project tracker <https://github.com/vcs-python/libvcs>`_
   and give us a wave. This API won't be stabilized until we're confident Subversion is
   covered accurately and can handle all-terrain scenarios.
"""  # NOQA: E5

import dataclasses
import re
from typing import Optional

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

from .base import Matcher, MatcherRegistry, URLProtocol

RE_PATH = r"""
    ((?P<user>.*)@)?
    (?P<hostname>([^/:]+))
    (:(?P<port>\d{1,5}))?
    (?P<separator>/)?
    (?P<path>
      (\w[^:.]*)
    )?
"""

# Valid schemes for svn(1).
# See Table 1.1 Repository access URLs in SVN Book
# https://svnbook.red-bean.com/nightly/en/svn.basic.in-action.html#svn.basic.in-action.wc.tbl-1
RE_SCHEME = r"""
    (?P<scheme>
      (
        file|http|https|svn|svn\+ssh
      )
    )
"""

DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="core-svn",
        description="Vanilla svn pattern",
        pattern=re.compile(
            rf"""
        ^{RE_SCHEME}
        ://
        {RE_PATH}
        """,
            re.VERBOSE,
        ),
    ),
]
"""Core regular expressions. These are patterns understood by ``svn(1)``"""


#
# Third-party URLs, e.g. npm, pip, etc.
#
RE_PIP_SCHEME = r"""
    (?P<scheme>
      (
        svn\+ssh|
        svn\+https|
        svn\+http|
        svn\+file
      )
    )
"""

PIP_DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="pip-url",
        description="pip-style svn URL",
        pattern=re.compile(
            rf"""
        {RE_PIP_SCHEME}
        ://
        {RE_PATH}
        """,
            re.VERBOSE,
        ),
    ),
    # file://, RTC 8089, File:// https://datatracker.ietf.org/doc/html/rfc8089
    Matcher(
        label="pip-file-url",
        description="pip-style svn+file:// URL",
        pattern=re.compile(
            r"""
        (?P<scheme>svn\+file)://
        (?P<path>.*)
        """,
            re.VERBOSE,
        ),
    ),
]
"""pip-style svn URLs.

Examples of PIP-style svn URLs (via pip.pypa.io)::

    MyProject @ svn+https://svn.example.com/MyProject
    MyProject @ svn+ssh://svn.example.com/MyProject
    MyProject @ svn+ssh://user@svn.example.com/MyProject

Refs (via pip.pypa.io)::

    MyProject @ -e svn+http://svn.example.com/svn/MyProject/trunk@2019
    MyProject @ -e svn+http://svn.example.com/svn/MyProject/trunk@{20080101}

Notes
-----

- https://pip.pypa.io/en/stable/topics/vcs-support/
"""  # NOQA: E501


@dataclasses.dataclass(repr=False)
class SvnURL(URLProtocol, SkipDefaultFieldsReprMixin):
    """SVN repository location. Parses URLs on initialization.

    Examples
    --------
    >>> SvnURL(url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository')
    SvnURL(url=svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository,
           scheme=svn+ssh,
           hostname=svn.debian.org,
           path=svn/aliothproj/path/in/project/repository,
           matcher=core-svn)

    >>> myrepo = SvnURL(
    ...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository'
    ... )

    >>> myrepo.hostname
    'svn.debian.org'

    >>> myrepo.path
    'svn/aliothproj/path/in/project/repository'

    - Compatibility checking: :meth:`SvnURL.is_valid()`
    - URLs compatible with ``svn(1)``: :meth:`SvnURL.to_url()`

    Attributes
    ----------
    matcher : str
        name of the :class:`~libvcs.parse.base.Matcher`
    """

    url: str
    scheme: Optional[str] = None
    user: Optional[str] = None
    hostname: str = dataclasses.field(default="")
    port: Optional[int] = None
    separator: str = dataclasses.field(default="/")
    path: str = dataclasses.field(default="")

    #
    # commit-ish: ref
    #
    ref: Optional[str] = None

    matcher: Optional[str] = None
    matchers = MatcherRegistry = MatcherRegistry(
        _matchers={m.label: m for m in DEFAULT_MATCHERS}
    )

    def __post_init__(self) -> None:
        url = self.url
        for matcher in self.matchers.values():
            match = re.match(matcher.pattern, url)
            if match is None:
                continue
            groups = match.groupdict()
            setattr(self, "matcher", matcher.label)
            for k, v in groups.items():
                setattr(self, k, v)

            for k, v in matcher.pattern_defaults.items():
                if getattr(self, k, None) is None:
                    setattr(self, k, matcher.pattern_defaults[k])

    @classmethod
    def is_valid(cls, url: str, is_explicit: Optional[bool] = False) -> bool:
        """Whether URL is compatible with VCS or not.

        Examples
        --------

        >>> SvnURL.is_valid(
        ...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository'
        ... )
        True

        >>> SvnURL.is_valid(url='notaurl')
        False
        """
        return any(re.search(matcher.pattern, url) for matcher in cls.matchers.values())

    def to_url(self) -> str:
        """Return a ``svn(1)``-compatible URL. Can be used with ``svn checkout``.

        Examples
        --------

        >>> svn_url = SvnURL(
        ...     url='svn+ssh://my-username@my-server/vcs-python/libvcs'
        ... )

        >>> svn_url
        SvnURL(url=svn+ssh://my-username@my-server/vcs-python/libvcs,
                scheme=svn+ssh,
                user=my-username,
                hostname=my-server,
                path=vcs-python/libvcs,
                matcher=core-svn)

        Switch repo libvcs -> vcspull:

        >>> svn_url.path = 'vcs-python/vcspull'

        >>> svn_url.to_url()
        'svn+ssh://my-username@my-server/vcs-python/vcspull'

        Switch user to "tom":

        >>> svn_url.user = 'tom'

        >>> svn_url.to_url()
        'svn+ssh://tom@my-server/vcs-python/vcspull'
        """
        parts = [self.scheme or "ssh", "://"]
        if self.user:
            parts.extend([self.user, "@"])

        parts.append(self.hostname)

        if self.port is not None:
            parts.extend([":", f"{self.port}"])

        parts.extend([self.separator, self.path])

        return "".join(part for part in parts if isinstance(part, str))
