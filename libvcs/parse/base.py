import dataclasses
from typing import Iterator, Pattern, Protocol

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin


class URLProtocol(Protocol):
    """Common interface for VCS URL Parsers."""

    def __init__(self, url: str):
        ...

    def to_url(self) -> str:
        ...

    def is_valid(self, url: str) -> bool:
        ...


@dataclasses.dataclass(repr=False)
class Matcher(SkipDefaultFieldsReprMixin):
    """Structure for a matcher"""

    label: str
    """Computer readable name / ID"""
    description: str
    """Human readable description"""
    pattern: Pattern
    """Regex pattern"""
    pattern_defaults: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(repr=False)
class MatcherRegistry(SkipDefaultFieldsReprMixin):
    """Pattern matching and parsing capabilities for URL parsers, e.g. GitURL"""

    _matchers: dict[str, Matcher] = dataclasses.field(default_factory=dict)

    def register(self, cls: Matcher) -> None:
        """

        .. currentmodule:: libvcs.parse.git

        >>> from libvcs.parse.git import GitURL, GitBaseURL

        :class:`GitBaseURL` - the ``git(1)`` compliant parser - won't accept a pip-style URL:

        >>> GitBaseURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        False

        :class:`GitURL` - the "batteries-included" parser - can do it:

        >>> GitURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        True

        But what if you wanted to do ``github:org/repo``?

        >>> GitURL.is_valid(url="github:org/repo")
        False

        **Extending matching capability:**

        >>> class GitHubPrefix(Matcher):
        ...     label = 'gh-prefix'
        ...     description ='Matches prefixes like github:org/repo'
        ...     pattern = r'^github:(?P<path>)'
        ...     pattern_defaults = {
        ...         'hostname': 'github.com',
        ...         'scheme': 'https'
        ...     }

        >>> class GitHubLocation(GitURL):
        ...    matchers = MatcherRegistry = MatcherRegistry(
        ...        _matchers={'github_prefix': GitHubPrefix}
        ...    )

        >>> GitHubLocation.is_valid(url='github:vcs-python/libvcs')
        True

        >>> GitHubLocation.is_valid(url='gitlab:vcs-python/libvcs')
        False

        >>> class GitLabPrefix(Matcher):
        ...     label = 'gl-prefix'
        ...     description ='Matches prefixes like gitlab:org/repo'
        ...     pattern = r'^gitlab:(?P<path>)'
        ...     pattern_defaults = {
        ...         'hostname': 'gitlab.com',
        ...         'scheme': 'https',
        ...         'suffix': '.git'
        ...     }

        Option 1: Create a brand new matcher

        >>> class GitLabLocation(GitURL):
        ...    matchers = MatcherRegistry = MatcherRegistry(
        ...        _matchers={'gitlab_prefix': GitLabPrefix}
        ...    )

        >>> GitLabLocation.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Option 2 (global, everywhere): Add to the global :class:`GitURL`:

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        False

        >>> GitURL.matchers.register(GitLabPrefix)

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        git URLs + pip-style git URLs:

        This is already in :class:`GitURL` via :data:`PIP_DEFAULT_MATCHERS`. For the
        sake of showing how extensibility works, here is a recreation based on
        :class:`GitBaseURL`:

        >>> from libvcs.parse.git import GitBaseURL

        >>> from libvcs.parse.git import DEFAULT_MATCHERS, PIP_DEFAULT_MATCHERS

        >>> class GitURLWithPip(GitBaseURL):
        ...    matchers = MatcherRegistry = MatcherRegistry(
        ...        _matchers={m.label: m for m in [*DEFAULT_MATCHERS, *PIP_DEFAULT_MATCHERS]}
        ...    )

        >>> GitURLWithPip.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        True

        >>> GitURLWithPip(url="git+ssh://git@github.com/tony/AlgoXY.git")
        GitURLWithPip(url=git+ssh://git@github.com/tony/AlgoXY.git,
            scheme=git+ssh,
            user=git,
            hostname=github.com,
            path=tony/AlgoXY,
            suffix=.git,
            matcher=pip-url)
        """  # NOQA: E501
        if cls.label not in self._matchers:
            self._matchers[cls.label] = cls

    def unregister(self, label: str) -> None:
        if label in self._matchers:
            del self._matchers[label]

    def __iter__(self) -> Iterator[str]:
        return self._matchers.__iter__()

    def values(self):  # https://github.com/python/typing/discussions/1033
        return self._matchers.values()
