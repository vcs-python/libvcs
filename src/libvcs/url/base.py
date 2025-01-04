"""Foundational tools to detect, parse, and validate VCS URLs."""

from __future__ import annotations

import dataclasses
import typing as t

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

if t.TYPE_CHECKING:
    from _collections_abc import dict_values
    from collections.abc import Iterator
    from re import Pattern


class URLProtocol(t.Protocol):
    """Common interface for VCS URL Parsers."""

    def __init__(self, url: str) -> None: ...

    def to_url(self) -> str:
        """Output to a command friendly URL for VCS."""
        ...

    @classmethod
    def is_valid(cls, url: str, is_explicit: bool | None = None) -> bool:
        """Return True if URL is valid for this parser."""
        ...


@dataclasses.dataclass(repr=False)
class Rule(SkipDefaultFieldsReprMixin):
    """A Rule represents an eligible pattern mapping to URL."""

    label: str
    """Computer readable name / ID"""
    description: str
    """Human readable description"""
    pattern: Pattern[str]
    """Regex pattern"""
    defaults: dict[str, str] = dataclasses.field(default_factory=dict)
    """Is the match unambiguous with other VCS systems? e.g. git+ prefix"""
    is_explicit: bool = False
    """Weight: Higher is more likely to win"""
    weight: int = 0


@dataclasses.dataclass(repr=False)
class RuleMap(SkipDefaultFieldsReprMixin):
    """Pattern matching and parsing capabilities for URL parsers, e.g. GitURL."""

    _rule_map: dict[str, Rule] = dataclasses.field(default_factory=dict)

    def register(self, cls: Rule) -> None:
        r"""Add a new URL rule.

        .. currentmodule:: libvcs.url.git

        >>> from dataclasses import dataclass
        >>> from libvcs.url.git import GitURL, GitBaseURL

        :class:`GitBaseURL` - the ``git(1)`` compliant parser - won't accept a pip-style URL:

        >>> GitBaseURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        False

        :class:`GitURL` - the "batteries-included" parser - can do it:

        >>> GitURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        True

        But what if you wanted to do ``github:org/repo``?

        >>> GitURL.is_valid(url="github:org/repo")
        True

        That actually works, but look, it's caught in git's standard SCP regex:

        >>> GitURL(url="github:org/repo")
        GitURL(url=github:org/repo,
           hostname=github,
           path=org/repo,
           rule=core-git-scp)

        >>> GitURL(url="github:org/repo").to_url()
        'git@github:org/repo'

        Eek. That won't work, :abbr:`can't do much with that one ("git clone git@github:org/repo"
        wouldn't work unless your user's had "insteadOf" set.)`.

        We need something more specific so usable URLs can be generated. What do we do?

        **Extending matching capability:**

        >>> class GitHubPrefix(Rule):
        ...     label = 'gh-prefix'
        ...     description ='Matches prefixes like github:org/repo'
        ...     pattern = r'^github:(?P<path>.*)$'
        ...     defaults = {
        ...         'hostname': 'github.com',
        ...         'scheme': 'https'
        ...     }
        ...     # We know it's git, not any other VCS
        ...     is_explicit = True
        ...     weight = 50

        >>> @dataclasses.dataclass(repr=False)
        ... class GitHubURL(GitURL):
        ...    rule_map = RuleMap(
        ...        _rule_map={'github_prefix': GitHubPrefix}
        ...    )

        >>> GitHubURL.is_valid(url='github:vcs-python/libvcs')
        True

        >>> GitHubURL.is_valid(url='github:vcs-python/libvcs', is_explicit=True)
        True

        Notice how ``defaults`` neatly fills the values for us.

        >>> GitHubURL(url='github:vcs-python/libvcs')
        GitHubURL(url=github:vcs-python/libvcs,
            scheme=https,
            hostname=github.com,
            path=vcs-python/libvcs,
            rule=gh-prefix)

        >>> GitHubURL(url='github:vcs-python/libvcs').to_url()
        'https://github.com/vcs-python/libvcs'

        >>> GitHubURL.is_valid(url='gitlab:vcs-python/libvcs')
        False

        ``GitHubURL`` sees this as invalid since it only has one rule,
        ``GitHubPrefix``.

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Same story, getting caught in ``git(1)``'s own liberal scp-style URL:

        >>> GitURL(url='gitlab:vcs-python/libvcs').rule
        'core-git-scp'

        >>> class GitLabPrefix(Rule):
        ...     label = 'gl-prefix'
        ...     description ='Matches prefixes like gitlab:org/repo'
        ...     pattern = r'^gitlab:(?P<path>)'
        ...     defaults = {
        ...         'hostname': 'gitlab.com',
        ...         'scheme': 'https',
        ...         'suffix': '.git'
        ...     }

        Option 1: Create a brand new rule

        >>> @dataclasses.dataclass(repr=False)
        ... class GitLabURL(GitURL):
        ...     rule_map = RuleMap(
        ...         _rule_map={'gitlab_prefix': GitLabPrefix}
        ...     )

        >>> GitLabURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Option 2 (global, everywhere): Add to the global :class:`GitURL`:

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Are we home free, though? Remember our issue with vague matches.

        >>> GitURL(url='gitlab:vcs-python/libvcs').rule
        'core-git-scp'

        Register:

        >>> GitURL.rule_map.register(GitLabPrefix)

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        **Example: git URLs + pip-style git URLs:**

        This is already in :class:`GitURL` via :data:`PIP_DEFAULT_RULES`. For the
        sake of showing how extensibility works, here is a recreation based on
        :class:`GitBaseURL`:

        >>> from libvcs.url.git import GitBaseURL

        >>> from libvcs.url.git import DEFAULT_RULES, PIP_DEFAULT_RULES

        >>> @dataclasses.dataclass(repr=False)
        ... class GitURLWithPip(GitBaseURL):
        ...    rule_map = RuleMap(
        ...        _rule_map={m.label: m for m in [*DEFAULT_RULES, *PIP_DEFAULT_RULES]}
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
            rule=pip-url)
        """  # NOQA: E501
        if cls.label not in self._rule_map:
            self._rule_map[cls.label] = cls

    def unregister(self, label: str) -> None:
        """Remove a URL rule."""
        if label in self._rule_map:
            del self._rule_map[label]

    def __iter__(self) -> Iterator[str]:
        """Iterate over map of URL rules."""
        return self._rule_map.__iter__()

    def values(
        self,  # https://github.com/python/typing/discussions/1033
    ) -> dict_values[str, Rule]:
        """Return list of URL rules."""
        return self._rule_map.values()
