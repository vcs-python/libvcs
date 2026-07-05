(parse)=

# URL Parser - `libvcs.url`

Parse VCS URLs into typed, editable structures — {mod}`urllib.parse` for git,
Mercurial, and Subversion. You validate a URL string, read its parts back as
{mod}`dataclasses` fields (`hostname`, `path`, `rev`), change any of them,
and export a form the VCS binary accepts.

The common URL shapes work out of the box; when your host or shorthand
isn't covered, you can {ref}`add your own rules <url-parser-extendability>`.
For a guided tour, start with {ref}`url-parsing`.

## Modules

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} Git URLs
:link: git
:link-type: doc
Parse and validate Git repository URLs (HTTPS, SSH, SCP).
:::

:::{grid-item-card} SVN URLs
:link: svn
:link-type: doc
Parse Subversion repository URLs.
:::

:::{grid-item-card} Hg URLs
:link: hg
:link-type: doc
Parse Mercurial repository URLs.
:::

:::{grid-item-card} Base
:link: base
:link-type: doc
Abstract base classes for URL parsing.
:::

:::{grid-item-card} Registry
:link: registry
:link-type: doc
URL matcher registration and lookup.
:::

:::{grid-item-card} Constants
:link: constants
:link-type: doc
Shared regex patterns and URL constants.
:::

::::

## Validate and detect VCS URLs

Check whether a string is a URL the VCS recognizes:

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

Turn a URL string into a typed structure with named fields — compare to
{class}`urllib.parse.ParseResult`:

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

`pip` knows what a certain URL string means, but `git clone` won't. This
works great with `pip`:

```console
$ pip install git+https://github.com/django/django.git@3.2
...
Successfully installed Django-3.2
```

but `git clone` can't use that URL:

```console
$ git clone git+https://github.com/django/django.git@3.2
Cloning into 'django.git@3.2'...
fatal: Unable to find remote helper for 'git+https'
```

It needs something like this:

```console
$ git clone https://github.com/django/django.git --branch 3.2
```

That translation is why parsing returns a structure —
{class}`~libvcs.url.git.GitURL` — rather than a string. As with
{class}`urllib.parse.ParseResult`, you inspect or replace individual fields
(swap just the hostname, drop the scheme), then call
{meth}`~libvcs.url.git.GitURL.to_url` when you finally need a string the VCS accepts. The same
structure covers the popular hosts out of the box and takes custom rules
for everything else.

## Scope

### Out of the box

libvcs parses package-like URLs, e.g.

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

(url-parser-extendability)=

## Extendability

Patterns can be registered. [Similar behavior](https://stackoverflow.com/a/6264214/1396928) exists
in {mod}`urllib.parse` (undocumented).

- Any formats not covered by the stock rules
- Custom URLs

  - For orgs on GitHub or GitLab, e.g.:

    - `python:mypy` -> `git@github.com:python/mypy.git`
    - `inkscape:inkscape` -> `git@gitlab.com:inkscape/inkscape.git`

  - For out of domain trackers, e.g.

    Direct to site:

    - `cb:vcs-python/libvcs` -> `https://codeberg.org/vcs-python/libvcs`
    - `kde:plasma/plasma-sdk` -> `git@invent.kde.org:plasma/plasma-sdk.git`

      Aside: Note [KDE's git docs] use of [`url.<base>.insteadOf`] and [`url.<base>.pushInsteadOf`]

    Direct to site + org / group:

    - `gnome:gedit` -> `git@gitlab.gnome.org:GNOME/gedit.git`
    - `openstack:openstack` -> `https://opendev.org/openstack/openstack.git`
    - `mozilla:central` -> `https://hg.mozilla.org/mozilla-central/`

[kde's git docs]: https://community.kde.org/Infrastructure/Git#Pushing
[`url.<base>.insteadof`]: https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtinsteadOf
[`url.<base>.pushinsteadof`]: https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtpushInsteadOf

From there, {class}`~libvcs.url.git.GitURL` can be used downstream directly by other projects:
libvcs's own {ref}`cmd` and {ref}`sync <projects>` layers, as well as
[vcspull configurations](https://vcspull.git-pull.com/), detect and accept
these URL patterns.

### How matching resolves

When a rule matches, its `defaults` fill in the groups the pattern didn't
capture — a `github:` prefix implies `hostname=github.com`. When several
rules could match, higher `weight`s are checked first; the first rule whose
pattern produces a valid match wins.

```{toctree}
:hidden:

git
svn
hg
base
registry
constants
```
