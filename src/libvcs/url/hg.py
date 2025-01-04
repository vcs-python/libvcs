"""Detect, parse, and validate hg (Mercurial) URLs.

- Detect: :meth:`HgURL.is_valid()`
- Parse: :class:`HgURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``hg(1)`` URL: :meth:`HgURL.to_url()`
- Extendable via :class:`~libvcs.url.base.RuleMap`,
  :class:`~libvcs.url.base.Rule`

.. Note::

   Use Mercurial at your job or project? This module welcomes a champion / maintainer to
   assure support is top-tier. Stop by the `project tracker
   <https://github.com/vcs-python/libvcs>`_ and make yourself known. We won't stabilize
   any APIs until we're satisfied support is up to snuff and is bullet proofed.
"""

from __future__ import annotations

import dataclasses
import re

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin
from libvcs.url.git import RE_SUFFIX

from .base import Rule, RuleMap, URLProtocol
from .constants import RE_PIP_REV, RE_SCP, RE_USER

RE_PATH = r"""
    (?P<hostname>([^/:]+))
    (:(?P<port>\d{1,5}))?
    (?P<separator>[:,/])?
    (?P<path>
      /?(\w[^:.@]*)
    )?
"""


RE_SCHEME = r"""
    (?P<scheme>
      (
        http|https|ssh
      )
    )
"""

DEFAULT_RULES: list[Rule] = [
    Rule(
        label="core-hg",
        description="Vanilla hg pattern",
        pattern=re.compile(
            rf"""
        ^{RE_SCHEME}
        ://
        {RE_USER}
        {RE_PATH}
        {RE_SUFFIX}?
        {RE_PIP_REV}?
        """,
            re.VERBOSE,
        ),
    ),
    Rule(
        label="core-hg-scp",
        description="Vanilla scp(1) / ssh(1) type URL",
        pattern=re.compile(
            rf"""
        ^(?P<scheme>ssh)?
        {RE_USER}
        {RE_SCP}
        {RE_SUFFIX}?
        """,
            re.VERBOSE,
        ),
        defaults={"username": "hg"},
    ),
    # SCP-style URLs, e.g. hg@
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

PIP_DEFAULT_RULES: list[Rule] = [
    Rule(
        label="pip-url",
        description="pip-style hg URL",
        pattern=re.compile(
            rf"""
        ^{RE_PIP_SCHEME}
        ://
        {RE_USER}
        {RE_PATH}
        {RE_SUFFIX}?
        {RE_PIP_REV}?
        """,
            re.VERBOSE,
        ),
        is_explicit=True,
    ),
    # file://, RTC 8089, File:// https://datatracker.ietf.org/doc/html/rfc8089
    Rule(
        label="pip-file-url",
        description="pip-style hg+file:// URL",
        pattern=re.compile(
            r"""
        (?P<scheme>hg\+file)://
        (?P<path>.*)
        """,
            re.VERBOSE,
        ),
        is_explicit=True,
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
"""


@dataclasses.dataclass(repr=False)
class HgBaseURL(
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """Mercurial repository location. Parses URLs on initialization.

    Attributes
    ----------
    rule : str
        name of the :class:`~libvcs.url.base.Rule`

    Examples
    --------
    >>> HgBaseURL(url='https://hg.mozilla.org/mozilla-central/')
    HgBaseURL(url=https://hg.mozilla.org/mozilla-central/,
            scheme=https,
            hostname=hg.mozilla.org,
            path=mozilla-central/,
            rule=core-hg)

    >>> myrepo = HgURL(url='https://hg.mozilla.org/mozilla-central/')

    >>> myrepo.hostname
    'hg.mozilla.org'

    >>> myrepo.path
    'mozilla-central/'

    >>> HgBaseURL.is_valid(url='ssh://username@machinename/path/to/repo')
    True

    >>> HgBaseURL(url='ssh://username@machinename/path/to/repo')
    HgBaseURL(url=ssh://username@machinename/path/to/repo,
            scheme=ssh,
            user=username,
            hostname=machinename,
            path=path/to/repo,
            rule=core-hg)

    - Compatibility checking: :meth:`HgURL.is_valid()`
    - URLs compatible with ``hg(1)``: :meth:`HgURL.to_url()`
    """

    url: str
    scheme: str | None = None
    user: str | None = None
    hostname: str = dataclasses.field(default="")
    port: int | None = None
    separator: str = dataclasses.field(default="/")
    path: str = dataclasses.field(default="")

    # Decoration
    suffix: str | None = None

    #
    # commit-ish: tag, branch, ref, revision
    #
    ref: str | None = None

    rule: str | None = None
    # name of the :class:`Rule`

    rule_map = RuleMap(_rule_map={m.label: m for m in DEFAULT_RULES})

    def __post_init__(self) -> None:
        """Initialize GitURL params into attributes."""
        url = self.url
        for rule in self.rule_map.values():
            match = re.match(rule.pattern, url)
            if match is None:
                continue
            groups = match.groupdict()
            self.rule = rule.label
            for k, v in groups.items():
                setattr(self, k, v)

            for k in rule.defaults:
                if getattr(self, k, None) is None:
                    setattr(self, k, rule.defaults[k])

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        """Whether URL is compatible with VCS or not.

        Examples
        --------
        >>> HgBaseURL.is_valid(
        ...     url='https://hg.mozilla.org/mozilla-central'
        ... )
        True

        >>> HgBaseURL.is_valid(url='ssh://hg@hg.python.org/cpython')
        True

        >>> HgBaseURL.is_valid(url='notaurl')
        False
        """
        if is_explicit is not None:
            return any(
                re.search(rule.pattern, url)
                for rule in cls.rule_map.values()
                if rule.is_explicit == is_explicit
            )
        return any(re.search(rule.pattern, url) for rule in cls.rule_map.values())

    def to_url(self) -> str:
        """Return a ``hg(1)``-compatible URL. Can be used with ``hg clone``.

        Examples
        --------
        >>> hg_url = HgBaseURL(url='https://hg.mozilla.org/mozilla-central')

        >>> hg_url
        HgBaseURL(url=https://hg.mozilla.org/mozilla-central,
                scheme=https,
                hostname=hg.mozilla.org,
                path=mozilla-central,
                rule=core-hg)

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

        >>> hugin = HgBaseURL(
        ...     url="http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin")

        >>> hugin
        HgBaseURL(url=http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin,
                scheme=http,
                hostname=hugin.hg.sourceforge.net,
                port=8000,
                path=hgroot/hugin/hugin,
                rule=core-hg)

        >>> hugin.to_url()
        'http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin'

        SSH URL with a username, `graphicsmagic <http://graphicsmagick.org/Hg.html>`_:

        >>> graphicsmagick = HgBaseURL(
        ...     url="ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick"
        ... )

        >>> graphicsmagick
        HgBaseURL(url=ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick,
                scheme=ssh,
                user=yourid,
                hostname=hg.GraphicsMagick.org,
                path=/hg/GraphicsMagick,
                rule=core-hg)

        >>> graphicsmagick.to_url()
        'ssh://yourid@hg.GraphicsMagick.org//hg/GraphicsMagick'

        Switch the username:

        >>> graphicsmagick.user = 'lucas'

        >>> graphicsmagick.to_url()
        'ssh://lucas@hg.GraphicsMagick.org//hg/GraphicsMagick'

        """
        if self.scheme is not None:
            parts = [self.scheme, "://"]

            if self.user is not None:
                parts.append(f"{self.user}@")
            parts.append(self.hostname)
        else:
            parts = [self.user or "hg", "@", self.hostname]

        if self.port is not None:
            parts.extend([":", f"{self.port}"])

        parts.extend([self.separator, self.path])

        return "".join(part for part in parts if isinstance(part, str))


@dataclasses.dataclass(repr=False)
class HgPipURL(
    HgBaseURL,
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """Supports pip hg URLs."""

    # commit-ish (rev): tag, branch, ref
    rev: str | None = None

    rule_map = RuleMap(_rule_map={m.label: m for m in PIP_DEFAULT_RULES})

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        """Whether URL is compatible with VCS or not.

        Examples
        --------
        >>> HgPipURL.is_valid(
        ...     url='hg+https://hg.mozilla.org/mozilla-central'
        ... )
        True

        >>> HgPipURL.is_valid(url='hg+ssh://hg@hg.python.org:cpython')
        True

        >>> HgPipURL.is_valid(url='notaurl')
        False
        """
        return super().is_valid(url=url, is_explicit=is_explicit)

    def to_url(self) -> str:
        """Return a ``hg(1)``-compatible URL. Can be used with ``hg clone``.

        Examples
        --------
        >>> hg_url = HgPipURL(url='hg+https://hg.mozilla.org/mozilla-central')

        >>> hg_url
        HgPipURL(url=hg+https://hg.mozilla.org/mozilla-central,
                scheme=hg+https,
                hostname=hg.mozilla.org,
                path=mozilla-central,
                rule=pip-url)

        Switch repo mozilla-central -> mobile-browser:

        >>> hg_url.path = 'mobile-browser'

        >>> hg_url.to_url()
        'hg+https://hg.mozilla.org/mobile-browser'

        Switch them to localhost:

        >>> hg_url.hostname = 'localhost'
        >>> hg_url.scheme = 'http'

        >>> hg_url.to_url()
        'http://localhost/mobile-browser'

        """
        parts = [self.scheme or "ssh", "://"]
        if self.user:
            parts.extend([self.user, "@"])

        parts.append(self.hostname)

        if self.port is not None:
            parts.extend([":", f"{self.port}"])

        parts.extend([self.separator, self.path])

        return "".join(part for part in parts if isinstance(part, str))


@dataclasses.dataclass(repr=False)
class HgURL(
    HgPipURL,
    HgBaseURL,
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """Batteries included URL Parser. Supports hg(1) and pip URLs.

    **Ancestors (MRO)**
    This URL parser inherits methods and attributes from the following parsers:

    - :class:`HgPipURL`

      - :meth:`HgPipURL.to_url`
    - :class:`HgBaseURL`

      - :meth:`HgBaseURL.to_url`
    """

    rule_map = RuleMap(
        _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
    )

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        r"""Whether URL is compatible included Hg URL rule_map or not.

        Examples
        --------
        **Will** match normal ``hg(1)`` URLs, use :meth:`HgURL.is_valid` for that.

        >>> HgURL.is_valid(url='https://hg.mozilla.org/mozilla-central/mozilla-central')
        True

        >>> HgURL.is_valid(url='hg@hg.mozilla.org:MyProject/project')
        True

        Pip-style URLs:

        >>> HgURL.is_valid(url='hg+https://hg.mozilla.org/mozilla-central/project')
        True

        >>> HgURL.is_valid(url='hg+ssh://hg@hg.mozilla.org:MyProject/project')
        True

        >>> HgURL.is_valid(url='notaurl')
        False

        **Explicit VCS detection**

        Pip-style URLs are prefixed with the VCS name in front, so its rule_map can
        unambiguously narrow the type of VCS:

        >>> HgURL.is_valid(
        ...     url='hg+ssh://hg@hg.mozilla.org:mozilla-central/image', is_explicit=True
        ... )
        True

        Below, while it's hg.mozilla.org, that doesn't necessarily mean that the URL
        itself is conclusively a `hg` URL (e.g. the pattern is too broad):

        >>> HgURL.is_valid(
        ...     url='hg@hg.mozilla.org:mozilla-central/image', is_explicit=True
        ... )
        False

        You could create a Mozilla rule that consider hg.mozilla.org hostnames to be
        exclusively hg:

        >>> MozillaRule = Rule(
        ...     # Since hg.mozilla.org exclusively serves hg repos, make explicit
        ...     label='mozilla-rule',
        ...     description='Matches hg.mozilla.org https URLs, exact VCS match',
        ...     pattern=re.compile(
        ...         rf'''
        ...         ^(?P<scheme>ssh)?
        ...         ((?P<user>\w+)@)?
        ...         (?P<hostname>(hg.mozilla.org)+):
        ...         (?P<path>(\w[^:]+))
        ...         {RE_SUFFIX}?
        ...         ''',
        ...         re.VERBOSE,
        ...     ),
        ...     is_explicit=True,
        ...     defaults={
        ...         'hostname': 'hg.mozilla.org'
        ...     }
        ... )

        >>> HgURL.rule_map.register(MozillaRule)

        >>> HgURL.is_valid(
        ...     url='hg@hg.mozilla.org:mozilla-central/image', is_explicit=True
        ... )
        True

        >>> HgURL(url='hg@hg.mozilla.org:mozilla-central/image').rule
        'mozilla-rule'

        This is just us cleaning up:

        >>> HgURL.rule_map.unregister('mozilla-rule')

        >>> HgURL(url='hg@hg.mozilla.org:mozilla-central/mozilla-rule').rule
        'core-hg-scp'
        """
        return super().is_valid(url=url, is_explicit=is_explicit)

    def to_url(self) -> str:
        """Return a ``hg(1)``-compatible URL. Can be used with ``hg clone``.

        Examples
        --------
        SSH style URL:

        >>> hg_url = HgURL(url='hg@hg.mozilla.org:mozilla-central/browser')

        >>> hg_url.path = 'mozilla-central/gfx'

        >>> hg_url.to_url()
        'ssh://hg@hg.mozilla.org:mozilla-central/gfx'

        HTTPs URL:

        >>> hg_url = HgURL(url='https://hg.mozilla.org/mozilla-central/memory')

        >>> hg_url.path = 'mozilla-central/image'

        >>> hg_url.to_url()
        'https://hg.mozilla.org/mozilla-central/image'

        Switch them to hglab:

        >>> hg_url.hostname = 'localhost'
        >>> hg_url.scheme = 'http'

        >>> hg_url.to_url()
        'http://localhost/mozilla-central/image'

        Pip style URL, thanks to this class implementing :class:`HgPipURL`:

        >>> hg_url = HgURL(url='hg+ssh://hg@hg.mozilla.org/mozilla-central/image')

        >>> hg_url.hostname = 'localhost'

        >>> hg_url.to_url()
        'hg+ssh://hg@localhost/mozilla-central/image'

        >>> hg_url.user = None

        >>> hg_url.to_url()
        'hg+ssh://localhost/mozilla-central/image'

        See Also
        --------
        :meth:`HgBaseURL.to_url`, :meth:`HgPipURL.to_url`
        """
        return super().to_url()
