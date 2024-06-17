(parse)=

# URL Parser - `libvcs.url`

We all love {mod}`urllib.parse`, but what about VCS systems?

Also, things like completions and typings being in demand, what of all these factories? Good python
code, but how to we get editor support and the nice satisfaction of types snapping together?

If there was a type-friendly structure - like writing our own abstract base class - or a
{mod}`dataclasses` - while also being extensible to patterns and groupings, maybe we could strike a
perfect balance.

If we could make it ready-to-go out of the box, but also have framework-like extensibility, it could
satisfy the niche.

## Validate and detect VCS URLs

````{tab} git

{meth}`libvcs.url.git.GitURL.is_valid()`

```python
>>> from libvcs.url.git import GitURL

>>> GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')
True
```

```python
>>> from libvcs.url.git import GitURL

>>> GitURL.is_valid(url='git@github.com:vcs-python/libvcs.git')
True
```

````

````{tab} hg
{meth}`libvcs.url.hg.HgURL.is_valid()`

```python
>>> from libvcs.url.hg import HgURL

>>> HgURL.is_valid(url='https://hg.mozilla.org/mozilla-central/mozilla-central')
True
```

```python
>>> from libvcs.url.hg import HgURL

>>> HgURL.is_valid(url='hg@hg.mozilla.org:MyProject/project')
True
```

````

````{tab} svn

{meth}`libvcs.url.svn.SvnURL.is_valid()`


```python
>>> from libvcs.url.svn import SvnURL

>>> SvnURL.is_valid(
... url='https://svn.project.org/project-central/project-central')
True
```

```python
>>> from libvcs.url.svn import SvnURL

>>> SvnURL.is_valid(url='svn@svn.project.org:MyProject/project')
True
```

````

## Parse VCS URLs

_Compare to {class}`urllib.parse.ParseResult`_

````{tab} git

{class}`libvcs.url.git.GitURL`

```python
>>> from libvcs.url.git import GitURL

>>> GitURL(url='git@github.com:vcs-python/libvcs.git')
GitURL(url=git@github.com:vcs-python/libvcs.git,
        user=git,
        hostname=github.com,
        path=vcs-python/libvcs,
        suffix=.git,
        rule=core-git-scp)
```

````

````{tab} hg

{class}`libvcs.url.hg.HgURL`

```python
>>> from libvcs.url.hg import HgURL

>>> HgURL(
...     url="http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin")
HgURL(url=http://hugin.hg.sourceforge.net:8000/hgroot/hugin/hugin,
        scheme=http,
        hostname=hugin.hg.sourceforge.net,
        port=8000,
        path=hgroot/hugin/hugin,
        rule=core-hg)
```

````

````{tab} svn

{class}`libvcs.url.svn.SvnURL`

```python
>>> from libvcs.url.svn import SvnURL

>>> SvnURL(
...     url='svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository')
SvnURL(url=svn+ssh://svn.debian.org/svn/aliothproj/path/in/project/repository,
       scheme=svn+ssh,
       hostname=svn.debian.org,
       path=svn/aliothproj/path/in/project/repository,
       rule=pip-url)
```

````

## Export usable URLs

- git: {meth}`libvcs.url.git.GitURL.to_url()`
- hg: {meth}`libvcs.url.hg.HgURL.to_url()`
- svn: {meth}`libvcs.url.svn.SvnURL.to_url()`

`pip` knows what a certain URL string means, but `git clone` won't.

e.g. `pip install git+https://github.com/django/django.git@3.2` works great with `pip`.

```console
$ pip install git+https://github.com/django/django.git@3.2
...
Successfully installed Django-3.2

```

but `git clone` can't use that:

```console
$ git clone git+https://github.com/django/django.git@3.2  # Fail
...
Cloning into django.git@3.2''...'
git: 'remote-git+https' is not a git command. See 'git --help'.
```

It needs something like this:

```console
$ git clone https://github.com/django/django.git --branch 3.2
```

But before we get there, we don't know if we want a URL yet. We return a structure, e.g. `GitURL`.

- Common result primitives across VCS, e.g. `GitURL`.

  Compare to a {class}`urllib.parse.ParseResult` in `urlparse`

  This is where fun can happen, or you can just parse a URL.

- Allow mutating / replacing parse of a vcs (e.g. just the hostname)
- Support common cases with popular VCS systems
- Support extending parsing for users needing to do so

## Scope

### Out of the box

The ambition for this is to build extendable parsers for package-like URLs, e.g.

- Vanilla VCS URLs

  - any URL supported by the VCS binary, e.g. `git(1)`, `svn(1)`, `hg(1)`.

- [pip]-style urls [^pip-url]
  - branches
  - tags
- [NPM]-style urls[^npm-url]
  - branches
  - tags

[pip]: https://pip.pypa.io/en/stable/

[^pip-url]: PIP-style URLs

    https://pip.pypa.io/en/stable/topics/vcs-support/

[npm]: https://docs.npmjs.com/

[^npm-url]: NPM style URLs

    https://docs.npmjs.com/about-packages-and-modules#npm-package-git-url-formats

## Extendability

Patterns can be registered. [Similar behavior](https://stackoverflow.com/a/6264214/1396928) exists
in {mod}`urlparse` (undocumented).

- Any formats not covered by the stock
- Custom urls

  - For orgs on , e.g:

    - `python:mypy` -> `git@github.com:python/mypy.git`
    - `inkscape:inkscape` -> `git@gitlab.com:inkscape/inkscape.git`

  - For out of domain trackers, e.g.

    Direct to site:

    - `cb:python-vcs/libtmux` -> `https://codeberg.org/vcs-python/libvcs`
    - `kde:plasma/plasma-sdk` -> `git@invent.kde.org:plasma/plasma-sdk.git`

      Aside: Note [KDE's git docs] use of [`url.<base>.insteadOf`] and [`url.<base>.pushInsteadOf`]

    Direct to site + org / group:

    - `gnome:gedit` -> `git@gitlab.gnome.org:GNOME/gedit.git`
    - `openstack:openstack` -> `https://opendev.org/openstack/openstack.git`
    - `mozilla:central` -> `https://hg.mozilla.org/mozilla-central/`

[kde's git docs]: https://community.kde.org/Infrastructure/Git#Pushing
[`url.<base>.insteadof`]: https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtinsteadOf
[`url.<base>.pushinsteadof`]: https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtpushInsteadOf

From there, `GitURL` can be used downstream directly by other projects.

In our case, `libvcs`s' own {ref}`cmd` and {ref}`projects`, as well as a {ref}`vcspull:index`
configuration, will be able to detect and accept various URL patterns.

### Matchers: Defaults

When a match occurs, its `defaults` will fill in non-matched groups.

### Matchers: First wins

When registering new matchers, higher `weight`s are checked first. If it's a valid regex grouping,
it will be picked.

[^api-unstable]: Provisional API only

    It's not determined if Location will be mutable or if modifications will return a new object.

## Explore

```{toctree}
:caption: API

git
svn
hg
base
registry
constants
```
