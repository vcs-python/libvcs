"""This module is an all-in-one parser and validator for Git URLs.

- Detection: :meth:`GitURL.is_valid()`
- Parse: :class:`GitURL`

  compare to :class:`urllib.parse.ParseResult`

  - Output ``git(1)`` URL: :meth:`GitURL.to_url()`
- Extendable via :class:`~libvcs.parse.base.MatcherRegistry`,
  :class:`~libvcs.parse.base.Matcher`
"""

import dataclasses
import re
from typing import Optional

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

from .base import Matcher, MatcherRegistry, URLProtocol

# Credit, pip (license: MIT):
# https://github.com/pypa/pip/blob/22.1.2/src/pip/_internal/vcs/git.py#L39-L52
# We modified it to have groupings
SCP_REGEX = r"""
    # Optional user, e.g. 'git@'
    (?P<user>(\w+))?@
    # Server, e.g. 'github.com'.
    (?P<hostname>([^/:]+)):
    # The server-side path. e.g. 'user/project.git'. Must start with an
    # alphanumeric character so as not to be confusable with a Windows paths
    # like 'C:/foo/bar' or 'C:\foo\bar'.
    (?P<path>(\w[^:]+))
    """

RE_PATH = r"""
    (?P<hostname>([^/:]+))
    (?P<separator>[:,/])?
    (?P<path>
      (\w[^:.]*)  # cut the path at . to negate .git
    )?
"""

RE_SCHEME = r"""
    (?P<scheme>
      (
        http|https
      )
    )
"""

RE_SUFFIX = r"(?P<suffix>\.git)"
# Some https repos have .git at the end, e.g. https://github.com/org/repo.git


DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="core-git-https",
        description="Vanilla git pattern, URL ending with optional .git suffix",
        pattern=re.compile(
            rf"""
        ^{RE_SCHEME}
        ://
        {RE_PATH}
        {RE_SUFFIX}?
        """,
            re.VERBOSE,
        ),
    ),
    # ends with .git. Including ones starting with https://
    # e.g. https://github.com/vcs-python/libvcs.git
    Matcher(
        label="core-git-scp",
        description="Vanilla scp(1) / ssh(1) type URL",
        pattern=re.compile(
            rf"""
        ^(?P<scheme>ssh)?
        {SCP_REGEX}
        {RE_SUFFIX}
        """,
            re.VERBOSE,
        ),
        pattern_defaults={"username": "git"},
    ),
    # SCP-style URLs, e.g. git@
]
"""Core regular expressions. These are patterns understood by ``git(1)``"""


#
# Third-party URLs, e.g. npm, pip, etc.
#
RE_PIP_SCHEME = r"""
    (?P<scheme>
      (
        git\+ssh|
        git\+https|
        git\+http|
        git\+file
      )
    )
"""

RE_PIP_SCHEME_WITH_HTTP = r"""
    (?P<scheme>
      (
        git\+ssh|
        git\+https|
        git\+http|
        git\+file
      )
    )
"""

PIP_DEFAULT_MATCHERS: list[Matcher] = [
    Matcher(
        label="pip-url",
        description="pip-style git URL",
        pattern=re.compile(
            rf"""
        {RE_PIP_SCHEME_WITH_HTTP}
        ://
        {RE_PATH}
        {RE_SUFFIX}?
        """,
            re.VERBOSE,
        ),
    ),
    Matcher(
        label="pip-scp-url",
        description="pip-style git ssh/scp URL",
        pattern=re.compile(
            rf"""
        {RE_PIP_SCHEME}
        {SCP_REGEX}?
        {RE_SUFFIX}
        """,
            re.VERBOSE,
        ),
    ),
    # file://, RTC 8089, File:// https://datatracker.ietf.org/doc/html/rfc8089
    Matcher(
        label="pip-file-url",
        description="pip-style git+file:// URL",
        pattern=re.compile(
            r"""
        (?P<scheme>git\+file)://
        (?P<path>.*)
        """,
            re.VERBOSE,
        ),
    ),
]
"""pip-style git URLs.

Examples of PIP-style git URLs (via pip.pypa.io)::

    MyProject @ git+ssh://git.example.com/MyProject
    MyProject @ git+file:///home/user/projects/MyProject
    MyProject @ git+https://git.example.com/MyProject

Refs (via pip.pypa.io)::

    MyProject @ git+https://git.example.com/MyProject.git@master
    MyProject @ git+https://git.example.com/MyProject.git@v1.0
    MyProject @ git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709
    MyProject @ git+https://git.example.com/MyProject.git@refs/pull/123/head

Notes
-----

- https://pip.pypa.io/en/stable/topics/vcs-support/
"""  # NOQA: E501

NPM_DEFAULT_MATCHERS: list[Matcher] = []
"""NPM-style git URLs.

Git URL pattern (from docs.npmjs.com)::

   <protocol>://[<user>[:<password>]@]<hostname>[:<port>][:][/]<path>[#<commit-ish> | #semver:<semver>]

Examples of NPM-style git URLs (from docs.npmjs.com)::

    ssh://git@github.com:npm/cli.git#v1.0.27
    git+ssh://git@github.com:npm/cli#semver:^5.0
    git+https://isaacs@github.com/npm/cli.git
    git://github.com/npm/cli.git#v1.0.27

Notes
-----

- https://docs.npmjs.com/cli/v8/configuring-npm/package-json#git-urls-as-dependencies
"""  # NOQA: E501


@dataclasses.dataclass(repr=False)
class GitURL(URLProtocol, SkipDefaultFieldsReprMixin):
    """Git gepository location. Parses URLs on initialization.

    Examples
    --------
    >>> GitURL(url='https://github.com/vcs-python/libvcs.git')
    GitURL(url=https://github.com/vcs-python/libvcs.git,
            scheme=https,
            hostname=github.com,
            path=vcs-python/libvcs,
            suffix=.git,
            matcher=core-git-https)

    >>> myrepo = GitURL(url='https://github.com/myproject/myrepo.git')

    >>> myrepo.hostname
    'github.com'

    >>> myrepo.path
    'myproject/myrepo'

    >>> GitURL(url='git@github.com:vcs-python/libvcs.git')
    GitURL(url=git@github.com:vcs-python/libvcs.git,
            hostname=github.com,
            path=vcs-python/libvcs,
            user=git,
            suffix=.git,
            matcher=core-git-scp)

    - Compatibility checking: :meth:`GitURL.is_valid()`
    - URLs compatible with ``git(1)``: :meth:`GitURL.to_url()`

    Attributes
    ----------
    matcher : str
        name of the :class:`~libvcs.parse.base.Matcher`

    branch : str, optional
        Default URL parsers don't output these,
        can be added by extending or passing manually
    """

    url: str
    scheme: Optional[str] = None
    hostname: Optional[str] = None
    path: Optional[str] = None
    user: Optional[str] = None

    # Decoration
    suffix: Optional[str] = None

    #
    # commit-ish: tag, branch, ref, revision
    #
    ref: Optional[str] = None
    branch: Optional[str] = None
    tag: Optional[str] = None

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

        >>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
        True

        >>> GitURL.is_valid(url='git@github.com:vcs-python/libvcs.git')
        True

        >>> GitURL.is_valid(url='notaurl')
        False
        """
        return any(re.search(matcher.pattern, url) for matcher in cls.matchers.values())

    def to_url(self) -> str:
        """Return a ``git(1)``-compatible URL. Can be used with ``git clone``.

        Examples
        --------

        >>> git_location = GitURL(url='git@github.com:vcs-python/libvcs.git')

        >>> git_location
        GitURL(url=git@github.com:vcs-python/libvcs.git,
                hostname=github.com,
                path=vcs-python/libvcs,
                user=git,
                suffix=.git,
                matcher=core-git-scp)

        Switch repo libvcs -> vcspull:

        >>> git_location.path = 'vcs-python/vcspull'

        >>> git_location.to_url()
        'git@github.com:vcs-python/vcspull.git'

        Switch them to gitlab:

        >>> git_location.hostname = 'gitlab.com'

        >>> git_location.to_url()
        'git@gitlab.com:vcs-python/vcspull.git'

        todo
        ----

        - Formats: Show an example converting a github url from ssh -> https format,
          and the other way around.
        """
        if self.scheme is not None:
            parts = [self.scheme, "://", self.hostname, "/", self.path]
        else:
            parts = [self.user or "git", "@", self.hostname, ":", self.path]

        if self.suffix:
            parts.append(self.suffix)

        return "".join(part for part in parts if isinstance(part, str))
