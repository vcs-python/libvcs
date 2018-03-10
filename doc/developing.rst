.. _developing:

===========
Development
===========

Testing
-------

Our tests are inside ``tests/``. Tests are implemented using
`pytest`_.

.. _pytest: http://pytest.org/

.. _install_dev_env:

Install the latest code from git
--------------------------------

To begin developing, check out the code from github:

.. code-block:: sh

    $ git clone git@github.com:vcs-python/libvcs.git
    $ cd libvcs

Now create a virtualenv, if you don't know how to, you can create a
virtualenv with:

.. code-block:: sh

    $ virtualenv .venv

Then activate it to current tty / terminal session with:

.. code-block:: sh

    $ source .venv/bin/activate

Good! Now let's run this:

.. code-block:: sh

    $ pip install -r requirements/test.txt -e .

This has ``pip``, a python package manager install the python package
in the current directory. ``-e`` means ``--editable``, which means you can
adjust the code and the installed software will reflect the changes.

Test Runner
-----------

As you seen above, the ``libvcs`` command will now be available to you,
since you are in the virtual environment, your `PATH` environment was
updated to include a special version of ``python`` inside your ``.venv``
folder with its own packages.

.. code-block:: bash

    $ make test

You probably didn't see anything but tests scroll by.

If you found a problem or are trying to write a test, you can file an
`issue on github`_.

.. _test_specific_tests:

Test runner options
~~~~~~~~~~~~~~~~~~~

Test only a file:

.. code-block:: bash

    $ py.test tests/test_util.py

will test the ``tests/test_util.py`` tests.

.. code-block:: bash

    $ py.test tests/test_util.py::test_mkdir_p

tests ``test_mkdir_p`` inside of ``tests/test_util.py``.

Multiple can be separated by spaces:

.. code-block:: bash

    $ py.test tests/test_{git,svn}.py tests/test_util.py::test_mkdir_p

.. _issue on github: https://github.com/vcs-python/libvcs/issues
