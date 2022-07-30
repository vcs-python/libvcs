"""This module is an all-in-one parser and validator for Mercurial URLs.

- Detection: :meth:`HgURL.is_valid()`
- Parse: :class:`HgURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``hg(1)`` URL: :meth:`HgURL.to_url()`
- Extendable via :class:`~libvcs.parse.base.MatcherRegistry`,
  :class:`~libvcs.parse.base.Matcher`

.. Note::

   Do you use Mercurial at your job or project? This module welcomes a champion /
   maintainer to assure support is top-tier. Stop by the `project tracker
   <https://github.com/vcs-python/libvcs>`_ to make yourself known. We won't stabilize
   any APIs until we're satisfied support is "by the book" and is bullet proofed.
"""

import dataclasses
import re
from typing import Optional

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

from .base import Matcher, MatcherRegistry, URLProtocol

RE_PATH = r"""
    ((?P<user>\w+)@)?
    (?P<hostname>([^/:@]+))
    (:(?P<port>\d{1,5}))?
    (?P<separator>/)?
    (?P<path>
      /?(\w[^:.]*)
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
            user=username,
            hostname=machinename,
            path=path/to/repo,
            matcher=core-hg)

    - Compatibility checking: :meth:`HgURL.is_valid()`
    - URLs compatible with ``hg(1)``: :meth:`HgURL.to_url()`
    """

    url: str
    scheme: Optional[str] = None
    user: Optional[str] = None
    hostname: str = dataclasses.field(default="")
    port: Optional[int] = None
    separator: str = dataclasses.field(default="/")
    path: str = dataclasses.field(default="")

    #
    # commit-ish: tag, branch, ref, revision
    #
    ref: Optional[str] = None

    matcher: Optional[str] = None
    # name of the :class:`Matcher`
    matchers: MatcherRegistry = MatcherRegistry(
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

        >>> hg_url = HgURL(url='https://hg.mozilla.org/mozilla-central')

        >>> hg_url
        HgURL(url=https://hg.mozilla.org/mozilla-central,
                scheme=https,
                hostname=hg.mozilla.org,
                path=mozilla-central,
                matcher=core-hg)

        Switch repo libvcs -> vcspull:

        >>> hg_url.path = 'mobile-browser'

        >>> hg_url.to_url()
        'https://hg.mozilla.org/mobile-browser'

        Switch them to localhost:

        >>> hg_url.hostname = 'localhost'
        >>> hg_url.scheme = 'http'

        >>> hg_url.to_url()
        'http://localhost/mobile-browser'

        Another example, `hugin <http://hugin.hg.sourceforge.net>`_:

        >>> hugin = HgURL(url="http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin")

        >>> hugin
        HgURL(url=http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin,
                scheme=http,
                hostname=hugin.hg.sourceforge.net,
                port=8000,
                path=hgroot/hugin/hugin,
                matcher=core-hg)

        >>> hugin.to_url()
        'http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin'

        SSH URL with a username, `graphicsmagic <http://graphicsmagick.org/Hg.html>`_:

        >>> graphicsmagick = HgURL(
        ...     url="ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick"
        ... )

        >>> graphicsmagick
        HgURL(url=ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick,
                scheme=ssh,
                user=yourid,
                hostname=hg.GraphicsMagick.org,
                path=/hg/GraphicsMagick,
                matcher=core-hg)

        >>> graphicsmagick.to_url()
        'ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick'

        Switch the username:

        >>> graphicsmagick.user = 'lucas'

        >>> graphicsmagick.to_url()
        'ssh://lucas@hg.GraphicsMagick.org//hg/GraphicsMagick'

        """
        parts = [self.scheme or "ssh", "://"]
        if self.user:
            parts.extend([self.user, "@"])

        parts.append(self.hostname)

        if self.port is not None:
            parts.extend([":", f"{self.port}"])

        parts.extend([self.separator, self.path])

        return "".join(part for part in parts if isinstance(part, str))
