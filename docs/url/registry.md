# VCS Detection - `libvcs.url.registry`

Detect VCS from `git`, `hg`, and `svn` URLs.

```python
>>> from libvcs.url.registry import registry, ParserMatch
>>> from libvcs.url.git import GitURL

>>> registry.match('git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=GitURL(...))]

>>> registry.match('git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=True)
[]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git')
[ParserMatch(vcs='git', match=GitURL(...))]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=False)
[]

>>> registry.match('git+ssh://git@invent.kde.org:plasma/plasma-sdk.git', is_explicit=True)
[ParserMatch(vcs='git', match=GitURL(...))]
```

```{eval-rst}
.. automodule:: libvcs.url.registry
   :members:
   :undoc-members:
```
