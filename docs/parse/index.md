(parse)=

# Parser - `libvcs.parse`

VCS URL parser for python.

## Parsing capabilities

:::{warning}

The APIs and structures themselves are still unstable APIs. If you are missing a field or use case,
please file an issue.

:::

1. Detect VCS URLs

   - git: {meth}`libvcs.parse.git.GitURL.is_valid()`
   - hg: {meth}`libvcs.parse.hg.HgURL.is_valid()`
   - svn: {meth}`libvcs.parse.svn.SvnURL.is_valid()`

- Parse results of URL to a structure

  _Compare to {class}`urllib.parse.ParseResult`_

  - {class}`libvcs.parse.git.GitURL`
  - {class}`libvcs.parse.hg.HgURL`
  - {class}`libvcs.parse.svn.SvnURL`

3. Convert input VCS to _usable_ URLs

   - git: {meth}`libvcs.parse.git.GitURL.to_url()`
   - hg: {meth}`libvcs.parse.hg.HgURL.to_url()`
   - svn: {meth}`libvcs.parse.svn.SvnURL.to_url()`

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

   But before we get there, we don't know if we want a URL yet. We return a structure, e.g.
   `GitURL`.

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

### Extendability

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
[`url.<base>.insteadof`]:
  https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtinsteadOf
[`url.<base>.pushinsteadof`]:
  https://git-scm.com/docs/git-config#Documentation/git-config.txt-urlltbasegtpushInsteadOf

From there, `GitURL` can be used downstream directly by other projects.

In our case, `libvcs`s' own {ref}`cmd` and {ref}`projects`, as well as a {ref}`vcspull:index`
configuration, will be able to detect and accept various URL patterns.

## Location objects

Compare to {class}`urllib.parse.ParseResult`. These are structures that break the VCS location into
parse so they can be filled, replaced [^api-unstable], and exported into a URL specifier compatible
with the VCS.

[^api-unstable]: Provisional API only

    It's not determined if Location will be mutable or if modifications will return a new object.

## Explore

```{toctree}
:caption: API

git
svn
hg
base
```
