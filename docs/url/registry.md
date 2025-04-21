# VCS Detection - `libvcs.url.registry`

Detect VCS from `git`, `hg`, and `svn` URLs.

**Basic example:**

```python
>>> from libvcs.url.registry import registry, ParserMatch
>>> from libvcs.url.git import GitURL

>>> registry.match('git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=GitURL(...))]

>>> registry.match('git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=True)
[ParserMatch(vcs='git', match=GitURL(...))]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=GitURL(...))]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=False)
[]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=True)
[ParserMatch(vcs='git', match=GitURL(...))]
```

**From the ground up:**

```python
>>> import dataclasses
>>> from libvcs.url.base import Rule, RuleMap
>>> from libvcs.url.registry import ParserMatch, VCSRegistry
>>> from libvcs.url.git import GitURL

This will match `github:org/repo`:

>>> class GitHubPrefix(Rule):
...     label = 'gh-prefix'
...     description ='Matches prefixes like github:org/repo'
...     pattern = r'^github:(?P<path>.*)$'
...     defaults = {
...         'hostname': 'github.com',
...         'scheme': 'https'
...     }
...     is_explicit = True  # We know it's git, not any other VCS
...     weight = 100

Prefix for KDE infrastructure, `kde:group/repository`:

>>> class KDEPrefix(Rule):  # https://community.kde.org/Infrastructure/Git
...     label = 'kde-prefix'
...     description ='Matches prefixes like kde:org/repo'
...     pattern = r'^kde:(?P<path>\w[^:]+)$'
...     defaults = {
...         'hostname': 'invent.kde.org',
...         'scheme': 'https'
...     }
...     is_explicit = True
...     weight = 100

>>> @dataclasses.dataclass(repr=False)
... class MyGitURLParser(GitURL):
...    rule_map = RuleMap(
...        _rule_map={
...            **GitURL.rule_map._rule_map,
...            'github_prefix': GitHubPrefix,
...            'kde_prefix': KDEPrefix,
...        }
...    )

>>> my_parsers: "ParserLazyMap" = {
...    "git": MyGitURLParser,
...    "hg": "libvcs.url.hg.HgURL",
...    "svn": "libvcs.url.svn.SvnURL",
... }

>>> vcs_matcher = VCSRegistry(parsers=my_parsers)

>>> vcs_matcher.match('git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=MyGitURLParser(...)),
    ParserMatch(vcs='hg', match=HgURL(...)),
    ParserMatch(vcs='svn', match=SvnURL(...))]

Still works with everything GitURL does:

>>> vcs_matcher.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=True)
[ParserMatch(vcs='git', match=MyGitURLParser(...))]

>>> vcs_matcher.match('github:webpack/webpack', is_explicit=True)
[ParserMatch(vcs='git',
    match=MyGitURLParser(url=github:webpack/webpack,
    scheme=https,
    hostname=github.com,
    path=webpack/webpack,
    rule=gh-prefix))]

>>> git_match = vcs_matcher.match('github:webpack/webpack', is_explicit=True)[0].match

>>> git_match.to_url()
'https://github.com/webpack/webpack'

If an ssh URL is preferred:

>>> git_match.scheme = None

>>> git_match.to_url()
'git@github.com:webpack/webpack'

>>> vcs_matcher.match('kde:frameworks/kirigami', is_explicit=True)
[ParserMatch(vcs='git',
    match=MyGitURLParser(url=kde:frameworks/kirigami,
    scheme=https,
    hostname=invent.kde.org,
    path=frameworks/kirigami,
    rule=kde-prefix))]

>>> kde_match = vcs_matcher.match('kde:frameworks/kirigami', is_explicit=True)[0].match

>>> kde_match
MyGitURLParser(url=kde:frameworks/kirigami,
    scheme=https,
    hostname=invent.kde.org,
    path=frameworks/kirigami,
    rule=kde-prefix)

>>> kde_match.to_url()
'https://invent.kde.org/frameworks/kirigami'

>>> kde_match.scheme = None

>>> kde_match.to_url()
'git@invent.kde.org:frameworks/kirigami'
```

```{eval-rst}
.. automodule:: libvcs.url.registry
   :members:
   :undoc-members:
```
