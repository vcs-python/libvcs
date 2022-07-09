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
    (?P<separator>[:,/])?
    (?P<path>
      (\w[^:.]*)
    )?
"""

RE_SCHEME = r"""
    (?P<scheme>
      (
        http|https|
        svn\+ssh
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
    scheme: str = dataclasses.field(init=False)
    hostname: str = dataclasses.field(init=False)
    path: str = dataclasses.field(init=False)
    user: Optional[str] = None

    #
    # commit-ish: ref
    #
    ref: Optional[str] = None

    matcher: Optional[str] = None
    matchers = MatcherRegistry = MatcherRegistry(
        _matchers={m.label: m for m in DEFAULT_MATCHERS}
    )

    def __post_init__(self):
        url = self.url
        for matcher in self.matchers.values():
            match = re.match(matcher.pattern, url)
            if match is None:
                continue
            groups = match.groupdict()
            setattr(self, "matcher", matcher.label)
            for k, v in groups.items():
                if v is None and k in matcher.pattern_defaults:
                    setattr(self, k, matcher.pattern_defaults[v])
                else:
                    setattr(self, k, v)

    @classmethod
    def is_valid(cls, url: str) -> bool:
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

        >>> svn_location = SvnURL(
        ...     url='svn+ssh://my-username@my-server/vcs-python/libvcs'
        ... )

        >>> svn_location
        SvnURL(url=svn+ssh://my-username@my-server/vcs-python/libvcs,
                scheme=svn+ssh,
                hostname=my-server,
                path=vcs-python/libvcs,
                user=my-username,
                matcher=core-svn)

        Switch repo libvcs -> vcspull:

        >>> svn_location.path = 'vcs-python/vcspull'

        >>> svn_location.to_url()
        'svn+ssh://my-username@my-server/vcs-python/vcspull'

        Switch user to "tom":

        >>> svn_location.user = 'tom'

        >>> svn_location.to_url()
        'svn+ssh://tom@my-server/vcs-python/vcspull'
        """
        if self.scheme is not None:
            parts = [self.scheme, "://"]
            if self.user:
                parts.extend([self.user, "@"])
            parts += [self.hostname, "/", self.path]
        else:
            parts = [self.user or "svn", "@", self.hostname, ":", self.path]

        return "".join(part for part in parts if isinstance(part, str))
