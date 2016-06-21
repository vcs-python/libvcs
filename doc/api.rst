.. _api:

=============
API Reference
=============

Creating a repo object
----------------------

Helper methods are available in ``libvcs.shortcuts`` which
can return a repo object from a single entry-point.

.. autofunction:: libvcs.shortcuts.create_repo

.. autofunction:: libvcs.shortcuts.create_repo_from_pip_url

Instantiating a repo by hand
----------------------------

Tools like :func:`libvcs.shortcuts.create_repo` and
`:func:`libvcs.shortcuts.create_repo_from_pip_url` are just wrappers
around instantiated these classes.

.. autoclass:: libvcs.git.GitRepo
   :members:
   :show-inheritance:

.. autoclass:: libvcs.hg.MercurialRepo
   :members:
   :show-inheritance:

.. autoclass:: libvcs.svn.SubversionRepo
   :members:
   :show-inheritance:

Adding your own VCS
-------------------

Extending libvcs can be done through subclassing ``BaseRepo``.

.. autoclass:: libvcs.base.BaseRepo
    :members:
    :show-inheritance:

Logging
-------

.. autoclass:: libvcs.base.RepoLoggingAdapter
   :members:
   :show-inheritance:

Utility stuff
-------------

.. automodule:: libvcs.util
   :members:
   :inherited-members:
   :show-inheritance:
