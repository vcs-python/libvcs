``libvcs`` - abstraction layer for vcs, powers `vcspull`_.

|pypi| |docs| |build-status| |coverage| |license|

Install:

.. code-block:: sh

   $ pip install libvcs

Open up python:

.. code-block:: sh

   $ python

   # or for nice autocomplete and syntax highlighting
   $ pip install ptpython
   $ ptpython

Create a `Repo`_ object of the project to inspect / checkout / update:

.. code-block:: python

   >>> from libvcs.shortcuts import create_repo_from_pip_url, create_repo

   # repo is an object representation of a vcs repository.
   >>> r = create_repo(url='https://www.github.com/tony/libtmux',
   ...                 vcs='git',
   ...                 repo_dir='/tmp/libtmux')

   # or via pip-style URL
   >>> r = create_repo_from_pip_url(
   ...         pip_url='git+https://www.github.com/tony/libtmux',
   ...         repo_dir='/tmp/libtmux')

Update / clone repo:

.. code-block:: python

   # it may or may not be checked out/cloned on the system yet
   >>> r.update_repo()

Get revision:

.. code-block:: python

   >>> r.get_revision()
   u'5c227e6ab4aab44bf097da2e088b0ff947370ab8'

Donations
---------

Your donations fund development of new features, testing and support.
Your money will go directly to maintenance and development of the project.
If you are an individual, feel free to give whatever feels right for the
value you get out of the project.

See donation options at https://git-pull.com/support.html.

More information 
----------------

==============  ==========================================================
Python support  Python 2.7, >= 3.3, pypy
VCS supported   git(1), svn(1), hg(1)
Source          https://github.com/tony/libvcs
Docs            http://libvcs.git-pull.com
Changelog       http://libvcs.git-pull.com/en/latest/history.html
API             http://libvcs.git-pull.com/en/latest/api.html
Issues          https://github.com/tony/libvcs/issues
Travis          http://travis-ci.org/tony/libvcs
Test Coverage   https://codecov.io/gh/tony/libvcs
pypi            https://pypi.python.org/pypi/libvcs
Open Hub        https://www.openhub.net/p/libvcs
License         `BSD`_.
git repo        .. code-block:: bash

                    $ git clone https://github.com/tony/libvcs.git
install dev     .. code-block:: bash

                    $ git clone https://github.com/tony/libvcs.git libvcs
                    $ cd ./libvcs
                    $ virtualenv .venv
                    $ source .venv/bin/activate
                    $ pip install -e .
tests           .. code-block:: bash

                    $ py.test
==============  ==========================================================

.. _BSD: http://opensource.org/licenses/BSD-3-Clause
.. _Documentation: http://libvcs.git-pull.com/en/latest/
.. _API: http://libvcs.git-pull.com/en/latest/api.html
.. _pip: http://www.pip-installer.org/en/latest/
.. _vcspull: http://www.github.com/tony/vcspull/
.. _Repo: https://libvcs.git-pull.com/en/latest/api.html#creating-a-repo-object

.. |pypi| image:: https://img.shields.io/pypi/v/libvcs.svg
    :alt: Python Package
    :target: http://badge.fury.io/py/libvcs

.. |build-status| image:: https://img.shields.io/travis/tony/libvcs.svg
   :alt: Build Status
   :target: https://travis-ci.org/tony/libvcs

.. |coverage| image:: https://codecov.io/gh/tony/libvcs/branch/master/graph/badge.svg
    :alt: Code Coverage
    :target: https://codecov.io/gh/tony/libvcs
    
.. |license| image:: https://img.shields.io/github/license/tony/libvcs.svg
    :alt: License 

.. |docs| image:: https://readthedocs.org/projects/libvcs/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://readthedocs.org/projects/libvcs/
