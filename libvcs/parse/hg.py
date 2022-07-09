"""This module is an all-in-one parser and validator for Mercurial URLs.

- Detection: :meth:`HgURL.is_valid()`
- Parse: :class:`HgURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``hg(1)`` URL: :meth:`HgURL.to_url()`
- Extendable via :class:`~libvcs.parse.base.MatcherRegistry`,
  :class:`~libvcs.parse.base.Matcher`

.. Note::

   Do you use Mercurial at your job or project? This module welcomes a champion /
   maintainer assure support is top-tier. Stop by the `project tracker
   <https://github.com/vcs-python/libvcs>`_ to make yourself known. We won't stabilize
   any APIs until we're satisfied support is "by the book" and is bullet proofed.
"""

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
      (\w[^:.]*)  # cut the path at . to negate .hg
    )?
"""

RE_SCHEME = r"""
    (?P<scheme>
      (
        http|https|ssh
      )
    )
"""

DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="core-hg",
        description="Vanilla hg pattern",
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
"""Core regular expressions. These are patterns understood by ``hg(1)``"""


#
# Third-party URLs, e.g. pip, etc.
#
RE_PIP_SCHEME = r"""
    (?P<scheme>
      (
        hg\+ssh|
        hg\+https|
        hg\+http|
        hg\+file
      )
    )
"""

PIP_DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="pip-url",
        description="pip-style hg URL",
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
        description="pip-style hg+file:// URL",
        pattern=re.compile(
            r"""
        (?P<scheme>hg\+file)://
        (?P<path>.*)
        """,
            re.VERBOSE,
        ),
    ),
]
"""pip-style hg URLs.

Examples of PIP-style hg URLs (via pip.pypa.io)::

    MyProject @ hg+http://hg.myproject.org/MyProject
    MyProject @ hg+https://hg.myproject.org/MyProject
    MyProject @ hg+ssh://hg.myproject.org/MyProject
    MyProject @ hg+file:///home/user/projects/MyProject

Refs (via pip.pypa.io)::

    MyProject @ hg+http://hg.example.com/MyProject@da39a3ee5e6b
    MyProject @ hg+http://hg.example.com/MyProject@2019
    MyProject @ hg+http://hg.example.com/MyProject@v1.0
    MyProject @ hg+http://hg.example.com/MyProject@special_feature

Notes
-----

- https://pip.pypa.io/en/stable/topics/vcs-support/
"""  # NOQA: E501


@dataclasses.dataclass(repr=False)
class HgURL(URLProtocol, SkipDefaultFieldsReprMixin):
    """Mercurial repository location. Parses URLs on initialization.

    Attributes
    ----------
    matcher : str
        name of the :class:`~libvcs.parse.base.Matcher`

    Examples
    --------
    >>> HgURL(url='https://hg.mozilla.org/mozilla-central/')
    HgURL(url=https://hg.mozilla.org/mozilla-central/,
            scheme=https,
            hostname=hg.mozilla.org,
            path=mozilla-central/,
            matcher=core-hg)

    >>> myrepo = HgURL(url='https://hg.mozilla.org/mozilla-central/')

    >>> myrepo.hostname
    'hg.mozilla.org'

    >>> myrepo.path
    'mozilla-central/'

    >>> HgURL(url='ssh://username@machinename/path/to/repo')
    HgURL(url=ssh://username@machinename/path/to/repo,
            scheme=ssh,
            hostname=machinename,
            path=path/to/repo,
            user=username,
            matcher=core-hg)

    - Compatibility checking: :meth:`HgURL.is_valid()`
    - URLs compatible with ``hg(1)``: :meth:`HgURL.to_url()`
    """

    url: str
    scheme: Optional[str] = None
    hostname: Optional[str] = None
    path: Optional[str] = None
    user: Optional[str] = None

    #
    # commit-ish: tag, branch, ref, revision
    #
    ref: Optional[str] = None

    matcher: Optional[str] = None
    # name of the :class:`Matcher`
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

        >>> HgURL.is_valid(
        ...     url='https://hg.mozilla.org/mozilla-central'
        ... )
        True

        >>> HgURL.is_valid(url='ssh://hg@hg.python.org/cpython')
        True

        >>> HgURL.is_valid(url='notaurl')
        False
        """
        return any(re.search(matcher.pattern, url) for matcher in cls.matchers.values())

    def to_url(self) -> str:
        """Return a ``hg(1)``-compatible URL. Can be used with ``hg clone``.

        Examples
        --------

        >>> hg_location = HgURL(url='https://hg.mozilla.org/mozilla-central')

        >>> hg_location
        HgURL(url=https://hg.mozilla.org/mozilla-central,
                scheme=https,
                hostname=hg.mozilla.org,
                path=mozilla-central,
                matcher=core-hg)

        Switch repo libvcs -> vcspull:

        >>> hg_location.path = 'mobile-browser'

        >>> hg_location.to_url()
        'https://hg.mozilla.org/mobile-browser'

        Switch them to hglab:

        >>> hg_location.hostname = 'localhost'
        >>> hg_location.scheme = 'http'

        >>> hg_location.to_url()
        'http://localhost/mobile-browser'

        todo
        ----

        - Formats: Show an example converting a hghub url from ssh -> https format,
          and the other way around.
        """
        if self.scheme is not None:
            parts = [self.scheme, "://", self.hostname, "/", self.path]
        else:
            parts = [self.user or "hg", "@", self.hostname, ":", self.path]

        return "".join(part for part in parts if isinstance(part, str))
