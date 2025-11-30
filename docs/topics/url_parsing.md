(url-parsing)=

# URL Parsing

libvcs provides typed URL parsing for git, Mercurial, and Subversion repositories.
Think of it as `urllib.parse` for VCS URLs—detecting URL types, extracting components,
and converting between formats.

## Detecting URL Types

Use `is_valid()` to check if a string is a valid VCS URL:

```python
>>> from libvcs.url.git import GitURL
>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
>>> GitURL.is_valid(url='git@github.com:vcs-python/libvcs.git')
True
>>> GitURL.is_valid(url='not-a-url')
False
```

## Parsing URLs

Create a URL object to extract components:

```python
>>> from libvcs.url.git import GitURL
>>> url = GitURL(url='git@github.com:vcs-python/libvcs.git')
>>> url.hostname
'github.com'
>>> url.path
'vcs-python/libvcs'
>>> url.suffix
'.git'
```

### HTTPS URLs

```python
>>> from libvcs.url.git import GitURL
>>> url = GitURL(url='https://github.com/vcs-python/libvcs.git')
>>> url.scheme
'https'
>>> url.hostname
'github.com'
>>> url.path
'vcs-python/libvcs'
```

### SCP-style URLs

Git's SCP-style syntax (`user@host:path`) is also supported:

```python
>>> from libvcs.url.git import GitURL
>>> url = GitURL(url='git@github.com:vcs-python/libvcs.git')
>>> url.user
'git'
>>> url.hostname
'github.com'
```

## Converting URL Formats

Use `to_url()` to export a URL in a specific format:

```python
>>> from libvcs.url.git import GitURL
>>> url = GitURL(url='git@github.com:vcs-python/libvcs.git')
>>> url.to_url()
'git@github.com:vcs-python/libvcs.git'
```

## Pip-style URLs

libvcs handles pip-style VCS URLs with branch/tag specifiers:

```python
>>> from libvcs.url.git import GitURL
>>> url = GitURL(url='git+https://github.com/django/django.git@main')
>>> url.scheme
'git+https'
>>> url.rev
'main'
```

## Other VCS Types

### Mercurial

```python
>>> from libvcs.url.hg import HgURL
>>> HgURL.is_valid(url='https://hg.mozilla.org/mozilla-central')
True
>>> url = HgURL(url='https://hg.mozilla.org/mozilla-central')
>>> url.hostname
'hg.mozilla.org'
```

### Subversion

```python
>>> from libvcs.url.svn import SvnURL
>>> SvnURL.is_valid(url='svn+ssh://svn.example.org/repo/trunk')
True
>>> url = SvnURL(url='svn+ssh://svn.example.org/repo/trunk')
>>> url.scheme
'svn+ssh'
```

## URL Registry

The registry can auto-detect VCS type from a URL:

```python
>>> from libvcs.url.registry import registry
>>> matches = registry.match('git@github.com:vcs-python/libvcs.git')
>>> len(matches) >= 1
True
```

## API Reference

See {doc}`/url/index` for the complete API reference.
