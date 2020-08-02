`libvcs` - abstraction layer for vcs, powers
[vcspull](https://www.github.com/vcs-python/vcspull/).

[![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](http://badge.fury.io/py/libvcs)
[![Documentation Status](https://readthedocs.org/projects/libvcs/badge/?version=latest)](https://readthedocs.org/projects/libvcs/)
[![Build Status](https://img.shields.io/travis/vcs-python/libvcs.svg)](https://travis-ci.org/vcs-python/libvcs)
[![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)
![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)

Install:

    $ pip install libvcs

Open up python:

    $ python

    # or for nice autocomplete and syntax highlighting
    $ pip install ptpython
    $ ptpython

Create a
[Repo](https://libvcs.git-pull.com/en/latest/api.html#creating-a-repo-object)
object of the project to inspect / checkout / update:

    >>> from libvcs.shortcuts import create_repo_from_pip_url, create_repo

    # repo is an object representation of a vcs repository.
    >>> r = create_repo(url='https://www.github.com/vcs-python/libtmux',
    ...                 vcs='git',
    ...                 repo_dir='/tmp/libtmux')

    # or via pip-style URL
    >>> r = create_repo_from_pip_url(
    ...         pip_url='git+https://www.github.com/vcs-python/libtmux',
    ...         repo_dir='/tmp/libtmux')

Update / clone repo:

    # it may or may not be checked out/cloned on the system yet
    >>> r.update_repo()

Get revision:

    >>> r.get_revision()
    u'5c227e6ab4aab44bf097da2e088b0ff947370ab8'

# Donations

Your donations fund development of new features, testing and support.
Your money will go directly to maintenance and development of the
project. If you are an individual, feel free to give whatever feels
right for the value you get out of the project.

See donation options at <https://www.git-pull.com/support.html>.

# More information

<table>
<tbody>
<tr class="odd">
<td>Python support</td>
<td>Python 2.7, &gt;= 3.4, pypy</td>
</tr>
<tr class="even">
<td>VCS supported</td>
<td>git(1), svn(1), hg(1)</td>
</tr>
<tr class="odd">
<td>Source</td>
<td><a href="https://github.com/vcs-python/libvcs">https://github.com/vcs-python/libvcs</a></td>
</tr>
<tr class="even">
<td>Docs</td>
<td><a href="https://libvcs.git-pull.com">https://libvcs.git-pull.com</a></td>
</tr>
<tr class="odd">
<td>Changelog</td>
<td><a href="https://libvcs.git-pull.com/en/latest/history.html">https://libvcs.git-pull.com/en/latest/history.html</a></td>
</tr>
<tr class="even">
<td>API</td>
<td><a href="https://libvcs.git-pull.com/en/latest/api.html">https://libvcs.git-pull.com/en/latest/api.html</a></td>
</tr>
<tr class="odd">
<td>Issues</td>
<td><a href="https://github.com/vcs-python/libvcs/issues">https://github.com/vcs-python/libvcs/issues</a></td>
</tr>
<tr class="even">
<td>Travis</td>
<td><a href="https://travis-ci.org/vcs-python/libvcs">https://travis-ci.org/vcs-python/libvcs</a></td>
</tr>
<tr class="odd">
<td>Test Coverage</td>
<td><a href="https://codecov.io/gh/vcs-python/libvcs">https://codecov.io/gh/vcs-python/libvcs</a></td>
</tr>
<tr class="even">
<td>pypi</td>
<td><a href="https://pypi.python.org/pypi/libvcs">https://pypi.python.org/pypi/libvcs</a></td>
</tr>
<tr class="odd">
<td>Open Hub</td>
<td><a href="https://www.openhub.net/p/libvcs">https://www.openhub.net/p/libvcs</a></td>
</tr>
<tr class="even">
<td>License</td>
<td><a href="https://opensource.org/licenses/MIT">MIT</a>.</td>
</tr>
<tr class="odd">
<td><p>git repo</p></td>
<td><div class="sourceCode" id="cb1"><pre class="sourceCode bash"><code class="sourceCode bash"><span id="cb1-1"><a href="#cb1-1" aria-hidden="true"></a>$ <span class="fu">git</span> clone https://github.com/vcs-python/libvcs.git</span></code></pre></div></td>
</tr>
<tr class="even">
<td><p>install dev</p></td>
<td><div class="sourceCode" id="cb2"><pre class="sourceCode bash"><code class="sourceCode bash"><span id="cb2-1"><a href="#cb2-1" aria-hidden="true"></a>$ <span class="fu">git</span> clone https://github.com/vcs-python/libvcs.git libvcs</span>
<span id="cb2-2"><a href="#cb2-2" aria-hidden="true"></a>$ <span class="bu">cd</span> ./libvcs</span>
<span id="cb2-3"><a href="#cb2-3" aria-hidden="true"></a>$ <span class="ex">virtualenv</span> .venv</span>
<span id="cb2-4"><a href="#cb2-4" aria-hidden="true"></a>$ <span class="bu">source</span> .venv/bin/activate</span>
<span id="cb2-5"><a href="#cb2-5" aria-hidden="true"></a>$ <span class="ex">pip</span> install -e .</span></code></pre></div></td>
</tr>
<tr class="odd">
<td><p>tests</p></td>
<td><div class="sourceCode" id="cb3"><pre class="sourceCode bash"><code class="sourceCode bash"><span id="cb3-1"><a href="#cb3-1" aria-hidden="true"></a>$ <span class="ex">py.test</span></span></code></pre></div></td>
</tr>
</tbody>
</table>
