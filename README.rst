``libvcs`` - abstraction layer for vcs, powers `vcspull`_.

|pypi| |docs| |build-status| |coverage| |license|

Setup
-----

.. code-block:: sh

   $ pip install libvcs

Open up python:

.. code-block:: sh

   $ python

   # or for nice autocomplete and syntax highlighting
   $ pip install ptpython
   $ ptpython

Usage
-----
Create a `Repo`_ object of the project to inspect / checkout / update:

.. code-block:: python

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

See donation options at https://www.git-pull.com/support.html.

More information 
----------------
- Python support: Python 2.7, >= 3.4, pypy
- VCS supported: git(1), svn(1), hg(1)
- Source: https://github.com/vcs-python/libvcs
- Docs: https://libvcs.git-pull.com
- Changelog: https://libvcs.git-pull.com/history.html
- API: https://libvcs.git-pull.com/api.html
- Issues: https://github.com/vcs-python/libvcs/issues
- Test Coverage: https://codecov.io/gh/vcs-python/libvcs
- pypi: https://pypi.python.org/pypi/libvcs
- Open Hub: https://www.openhub.net/p/libvcs
- License: `MIT`_.

.. _MIT: https://opensource.org/licenses/MIT
.. _Documentation: https://libvcs.git-pull.com/
.. _API: https://libvcs.git-pull.com/api.html
.. _pip: http://www.pip-installer.org/en/latest/
.. _vcspull: https://www.github.com/vcs-python/vcspull/
.. _Repo: https://libvcs.git-pull.com/api.html#creating-a-repo-object

.. |pypi| image:: https://img.shields.io/pypi/v/libvcs.svg
    :alt: Python Package
    :target: http://badge.fury.io/py/libvcs

.. |docs| image:: https://github.com/vcs-python/libvcs/workflows/Publish%20Docs/badge.svg
   :alt: Docs
   :target: https://github.com/vcs-python/libvcs/actions?query=workflow%3A"Publish+Docs"

.. |build-status| image:: https://github.com/vcs-python/libvcs/workflows/tests/badge.svg
   :alt: Build Status
   :target: https://github.com/vcs-python/libvcs/actions?query=workflow%3A"tests"

.. |coverage| image:: https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg
    :alt: Code Coverage
    :target: https://codecov.io/gh/vcs-python/libvcs
    
.. |license| image:: https://img.shields.io/github/license/vcs-python/libvcs.svg
    :alt: License 
