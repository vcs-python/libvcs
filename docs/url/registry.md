# VCS Detection - `libvcs.url.registry`

Detect which VCS a URL belongs to — git, Mercurial, or Subversion — before
you shell out to any binary. The module-level registry checks a URL against
every parser — {class}`~libvcs.url.git.GitURL`,
{class}`~libvcs.url.hg.HgURL`, {class}`~libvcs.url.svn.SvnURL` — and returns
each hit as a {class}`~libvcs.url.registry.ParserMatch`. Most readers only
need {meth}`~libvcs.url.registry.VCSRegistry.match`; registering rules of
your own is the rarer case covered further down.

## Matching URLs

Pass `is_explicit` to narrow matching to rules where the URL names its VCS
outright (`True`) — like the `git+ssh://` pip-style scheme — or to
pattern-inference rules only (`False`):

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

## Adding your own rules

For the rarer cases — organization shorthands, self-hosted forges — teach a
parser new URL shapes: subclass {class}`~libvcs.url.base.Rule` for the
pattern, attach it to your own {class}`~libvcs.url.git.GitURL` subclass
through {class}`~libvcs.url.base.RuleMap`, and hand that parser to a fresh
{class}`~libvcs.url.registry.VCSRegistry`. Subclassing keeps the rules
local — registering on `GitURL.rule_map` directly would mutate the shared
class-level map and change `GitURL` for every caller in the process.

This registry understands `github:org/repo` and converts matches to
cloneable URLs, leaving the module-level `registry` untouched. An ambiguous
SSH URL still matches every VCS — narrow it with `is_explicit=True`:

```python
>>> import dataclasses
>>> from libvcs.url.base import Rule, RuleMap
>>> from libvcs.url.registry import ParserMatch, VCSRegistry, registry
>>> from libvcs.url.git import GitURL

>>> class GitHubPrefix(Rule):
...     label = 'gh-prefix'
...     description = 'Matches prefixes like github:org/repo'
...     pattern = r'^github:(?P<path>.*)$'
...     defaults = {
...         'hostname': 'github.com',
...         'scheme': 'https'
...     }
...     is_explicit = True  # We know it's git, not any other VCS
...     weight = 100

>>> @dataclasses.dataclass(repr=False)
... class MyGitURLParser(GitURL):
...    rule_map = RuleMap(
...        _rule_map={
...            **GitURL.rule_map._rule_map,
...            'github_prefix': GitHubPrefix,
...        }
...    )

>>> my_parsers: "ParserLazyMap" = {
...    "git": MyGitURLParser,
...    "hg": "libvcs.url.hg.HgURL",
...    "svn": "libvcs.url.svn.SvnURL",
... }

>>> vcs_matcher = VCSRegistry(parsers=my_parsers)

>>> registry.match('git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=GitURL(...))]

>>> vcs_matcher.match('git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=MyGitURLParser(...)),
    ParserMatch(vcs='hg', match=HgURL(...)),
    ParserMatch(vcs='svn', match=SvnURL(...))]

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

>>> git_match.scheme = None

>>> git_match.to_url()
'git@github.com:webpack/webpack'
```

The same pattern handles infrastructure shorthands like KDE's
`kde:group/repository` convention:

```python
>>> import dataclasses
>>> from libvcs.url.base import Rule, RuleMap
>>> from libvcs.url.registry import ParserMatch, VCSRegistry
>>> from libvcs.url.git import GitURL

>>> class KDEPrefix(Rule):  # https://community.kde.org/Infrastructure/Git
...     label = 'kde-prefix'
...     description = 'Matches prefixes like kde:org/repo'
...     pattern = r'^kde:(?P<path>\w[^:]+)$'
...     defaults = {
...         'hostname': 'invent.kde.org',
...         'scheme': 'https'
...     }
...     is_explicit = True
...     weight = 100

>>> @dataclasses.dataclass(repr=False)
... class MyKDEURLParser(GitURL):
...    rule_map = RuleMap(
...        _rule_map={
...            **GitURL.rule_map._rule_map,
...            'kde_prefix': KDEPrefix,
...        }
...    )

>>> vcs_matcher = VCSRegistry(parsers={
...    "git": MyKDEURLParser,
...    "hg": "libvcs.url.hg.HgURL",
...    "svn": "libvcs.url.svn.SvnURL",
... })

>>> vcs_matcher.match('kde:frameworks/kirigami', is_explicit=True)
[ParserMatch(vcs='git',
    match=MyKDEURLParser(url=kde:frameworks/kirigami,
    scheme=https,
    hostname=invent.kde.org,
    path=frameworks/kirigami,
    rule=kde-prefix))]

>>> kde_match = vcs_matcher.match('kde:frameworks/kirigami', is_explicit=True)[0].match

>>> kde_match.to_url()
'https://invent.kde.org/frameworks/kirigami'

>>> kde_match.scheme = None

>>> kde_match.to_url()
'git@invent.kde.org:frameworks/kirigami'
```

## API Reference

```{eval-rst}
.. automodule:: libvcs.url.registry
   :members:
   :undoc-members:
```
