"""Detect, parse, and validate SVN (Subversion) URLs.

- Detect: :meth:`SvnURL.is_valid()`
- Parse: :class:`SvnURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``svn(1)`` URL: :meth:`SvnURL.to_url()`
- Extendable via :class:`~libvcs.url.base.RuleMap`,
  :class:`~libvcs.url.base.Rule`

.. Note::

   Subversion isn't seen as often these days, can you "rage against the dying of the
   light" and assure its light is not extinguished? Help assure SVN URL parsing is
   correct and robust. Visit the `project tracker <https://github.com/vcs-python/libvcs>`_
   and give us a wave. This API won't be stabilized until we're confident Subversion is
   covered accurately and can handle all-terrain scenarios.
"""

from __future__ import annotations

import dataclasses
import re

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

from .base import Rule, RuleMap, URLProtocol
from .constants import RE_PIP_REV, RE_SCP, RE_USER

RE_PATH = r"""
    (?P<hostname>([^/:@]+))
    (:(?P<port>\d{1,5}))?
    (?P<separator>[:,/])?
    (?P<path>
      (\w[^:.@]*)
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

DEFAULT_RULES: list[Rule] = [
    Rule(
        label="core-svn",
        description="Vanilla svn pattern",
        pattern=re.compile(
            rf"""
        ^{RE_SCHEME}
        ://
        {RE_USER}
        {RE_PATH}
        {RE_PIP_REV}?
        """,
            re.VERBOSE,
        ),
    ),
    Rule(
        label="core-svn-scp",
        description="Vanilla scp(1) / ssh(1) type URL",
        pattern=re.compile(
            rf"""
        ^(?P<scheme>ssh)?
        {RE_USER}
        {RE_SCP}
        {RE_PIP_REV}?
        """,
            re.VERBOSE,
        ),
        defaults={"username": "svn"},
    ),
    # SCP-style URLs, e.g. hg@
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
        svn\+http
      )
    )
"""

PIP_DEFAULT_RULES: list[Rule] = [
    Rule(
        label="pip-url",
        description="pip-style svn URL",
        pattern=re.compile(
            rf"""
        ^{RE_PIP_SCHEME}
        ://
        {RE_USER}
        {RE_PATH}
        {RE_PIP_REV}?
        """,
            re.VERBOSE,
        ),
        is_explicit=True,
    ),
    # file://, RTC 8089, File:// https://datatracker.ietf.org/doc/html/rfc8089
    Rule(
        label="pip-file-url",
        description="pip-style svn+file:// URL",
        pattern=re.compile(
            r"""
        (?P<scheme>svn\+file)://
        (?P<path>.*)
        """,
            re.VERBOSE,
        ),
        is_explicit=True,
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
"""


@dataclasses.dataclass(repr=False)
class SvnBaseURL(
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """SVN repository location. Parses URLs on initialization.

    Examples
    --------
    >>> SvnBaseURL(
    ...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository')
    SvnBaseURL(url=svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository,
           scheme=svn+ssh,
           hostname=svn.debian.org,
           path=svn/aliothproj/path/in/project/repository,
           rule=core-svn)

    >>> myrepo = SvnBaseURL(
    ...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository'
    ... )

    >>> myrepo.hostname
    'svn.debian.org'

    >>> myrepo.path
    'svn/aliothproj/path/in/project/repository'

    - Compatibility checking: :meth:`SvnBaseURL.is_valid()`
    - URLs compatible with ``svn(1)``: :meth:`SvnBaseURL.to_url()`

    Attributes
    ----------
    rule : str
        name of the :class:`~libvcs.url.base.Rule`
    """

    url: str
    scheme: str | None = None
    user: str | None = None
    hostname: str = dataclasses.field(default="")
    port: int | None = None
    separator: str = dataclasses.field(default="/")
    path: str = dataclasses.field(default="")

    ref: str | None = None

    rule: str | None = None
    rule_map = RuleMap(_rule_map={m.label: m for m in DEFAULT_RULES})

    def __post_init__(self) -> None:
        """Initialize SvnURL params into attributes."""
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
        >>> SvnBaseURL.is_valid(
        ...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository'
        ... )
        True

        >>> SvnBaseURL.is_valid(url='notaurl')
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
        """Return a ``svn(1)``-compatible URL. Can be used with ``svn checkout``.

        Examples
        --------
        >>> svn_url = SvnBaseURL(
        ...     url='svn+ssh://my-username@my-server/vcs-python/libvcs'
        ... )

        >>> svn_url
        SvnBaseURL(url=svn+ssh://my-username@my-server/vcs-python/libvcs,
                scheme=svn+ssh,
                user=my-username,
                hostname=my-server,
                path=vcs-python/libvcs,
                rule=core-svn)

        Switch repo libvcs -> vcspull:

        >>> svn_url.path = 'vcs-python/vcspull'

        >>> svn_url.to_url()
        'svn+ssh://my-username@my-server/vcs-python/vcspull'

        Switch user to "tom":

        >>> svn_url.user = 'tom'

        >>> svn_url.to_url()
        'svn+ssh://tom@my-server/vcs-python/vcspull'
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
class SvnPipURL(
    SvnBaseURL,
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """Supports pip svn URLs."""

    # commit-ish (rev): tag, branch, ref
    rev: str | None = None

    rule_map = RuleMap(_rule_map={m.label: m for m in PIP_DEFAULT_RULES})

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        """Whether URL is compatible with VCS or not.

        Examples
        --------
        >>> SvnPipURL.is_valid(
        ...     url='svn+https://svn.project.org/project-central'
        ... )
        True

        >>> SvnPipURL.is_valid(url='svn+ssh://svn@svn.python.org:cpython')
        True

        >>> SvnPipURL.is_valid(url='notaurl')
        False
        """
        return super().is_valid(url=url, is_explicit=is_explicit)

    def to_url(self) -> str:
        """Return a ``svn(1)``-compatible URL. Can be used with ``svn clone``.

        Examples
        --------
        >>> svn_url = SvnPipURL(url='svn+https://svn.project.org/project-central')

        >>> svn_url
        SvnPipURL(url=svn+https://svn.project.org/project-central,
                scheme=svn+https,
                hostname=svn.project.org,
                path=project-central,
                rule=pip-url)

        Switch repo project-central -> mobile-browser:

        >>> svn_url.path = 'mobile-browser'

        >>> svn_url.to_url()
        'svn+https://svn.project.org/mobile-browser'

        Switch them to localhost:

        >>> svn_url.hostname = 'localhost'
        >>> svn_url.scheme = 'http'

        >>> svn_url.to_url()
        'http://localhost/mobile-browser'

        """
        return super().to_url()


@dataclasses.dataclass(repr=False)
class SvnURL(
    SvnPipURL,
    SvnBaseURL,
    URLProtocol,
    SkipDefaultFieldsReprMixin,
):
    """Batteries included URL Parser. Supports svn(1) and pip URLs.

    **Ancestors (MRO)**
    This URL parser inherits methods and attributes from the following parsers:

    - :class:`SvnPipURL`

      - :meth:`SvnPipURL.to_url`
    - :class:`SvnBaseURL`

      - :meth:`SvnBaseURL.to_url`
    """

    rule_map = RuleMap(
        _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]},
    )

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        r"""Whether URL is compatible included Svn URL rule_map or not.

        Examples
        --------
        **Will** match normal ``svn(1)`` URLs, use :meth:`SvnURL.is_valid` for that.

        >>> SvnURL.is_valid(
        ... url='https://svn.project.org/project-central/project-central')
        True

        >>> SvnURL.is_valid(url='svn@svn.project.org:MyProject/project')
        True

        Pip-style URLs:

        >>> SvnURL.is_valid(url='svn+https://svn.project.org/project-central/project')
        True

        >>> SvnURL.is_valid(url='svn+ssh://svn@svn.project.org:MyProject/project')
        True

        >>> SvnURL.is_valid(url='notaurl')
        False

        **Explicit VCS detection**

        Pip-style URLs are prefixed with the VCS name in front, so its rule_map can
        unambiguously narrow the type of VCS:

        >>> SvnURL.is_valid(
        ...     url='svn+ssh://svn@svn.project.org:project-central/image',
        ...     is_explicit=True
        ... )
        True

        Below, while it's svn.project.org, that doesn't necessarily mean that the URL
        itself is conclusively a `svn` URL (e.g. the pattern is too broad):

        >>> SvnURL.is_valid(
        ...     url='svn@svn.project.org:project-central/image', is_explicit=True
        ... )
        False

        You could create a project rule that consider svn.project.org hostnames to be
        exclusively svn:

        >>> projectRule = Rule(
        ...     # Since svn.project.org exclusively serves svn repos, make explicit
        ...     label='project-rule',
        ...     description='Matches svn.project.org https URLs, exact VCS match',
        ...     pattern=re.compile(
        ...         rf'''
        ...         ^(?P<scheme>ssh)?
        ...         ((?P<user>\w+)@)?
        ...         (?P<hostname>(svn.project.org)+):
        ...         (?P<path>(\w[^:]+))
        ...         ''',
        ...         re.VERBOSE,
        ...     ),
        ...     is_explicit=True,
        ...     defaults={
        ...         'hostname': 'svn.project.org'
        ...     }
        ... )

        >>> SvnURL.rule_map.register(projectRule)

        >>> SvnURL.is_valid(
        ...     url='svn@svn.project.org:project-central/image', is_explicit=True
        ... )
        True

        >>> SvnURL(url='svn@svn.project.org:project-central/image').rule
        'project-rule'

        This is just us cleaning up:

        >>> SvnURL.rule_map.unregister('project-rule')

        >>> SvnURL(url='svn@svn.project.org:project-central/project-rule').rule
        'core-svn-scp'
        """
        return super().is_valid(url=url, is_explicit=is_explicit)

    def to_url(self) -> str:
        """Return a ``svn(1)``-compatible URL. Can be used with ``svn clone``.

        Examples
        --------
        SSH style URL:

        >>> svn_url = SvnURL(url='svn@svn.project.org:project-central/browser')

        >>> svn_url.path = 'project-central/gfx'

        >>> svn_url.to_url()
        'svn@svn.project.org:project-central/gfx'

        HTTPs URL:

        >>> svn_url = SvnURL(url='https://svn.project.org/project-central/memory')

        >>> svn_url.path = 'project-central/image'

        >>> svn_url.to_url()
        'https://svn.project.org/project-central/image'

        Switch them to svnlab:

        >>> svn_url.hostname = 'localhost'
        >>> svn_url.scheme = 'http'

        >>> svn_url.to_url()
        'http://localhost/project-central/image'

        Pip style URL, thanks to this class implementing :class:`SvnPipURL`:

        >>> svn_url = SvnURL(url='svn+ssh://svn@svn.project.org/project-central/image')

        >>> svn_url.hostname = 'localhost'

        >>> svn_url.to_url()
        'svn+ssh://svn@localhost/project-central/image'

        >>> svn_url.user = None

        >>> svn_url.to_url()
        'svn+ssh://localhost/project-central/image'

        See Also
        --------
        :meth:`SvnBaseURL.to_url`, :meth:`SvnPipURL.to_url`
        """
        return super().to_url()
