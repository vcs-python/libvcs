# Development

## Testing

Our tests are inside `tests/`. Tests are implemented using
[pytest](http://pytest.org/).

## Install the latest code from git

### Using pip

To begin developing, check out the code from github:

    $ git clone git@github.com:vcs-python/libvcs.git
    $ cd libvcs

Now create a virtualenv, if you don't know how to, you can create a
virtualenv with:

    $ virtualenv .venv

Then activate it to current tty / terminal session with:

    $ source .venv/bin/activate

Good! Now let's run this:

    $ pip install -r requirements/test.txt -e .

This has `pip`, a python package manager install the python package in
the current directory. `-e` means `--editable`, which means you can
adjust the code and the installed software will reflect the changes.

### Using poetry

To begin developing, check out the code from github:

    $ git clone git@github.com:vcs-python/libvcs.git
    $ cd libvcs

You can create a virtualenv, and install all of the locked packages as
listed in poetry.lock:

    $ poetry install

If you ever need to update packages during your development session, the
following command can be used to update all packages as per poetry
settings or individual package (second command):

    $ poetry update
    $ poetry update requests

Then activate it to your current tty / terminal session with:

    $ poetry shell

That is it! You are now ready to code!

## Test Runner

As you seen above, the `libvcs` command will now be available to you,
since you are in the virtual environment, your <span
class="title-ref">PATH</span> environment was updated to include a
special version of `python` inside your `.venv` folder with its own
packages.

    $ make test

You probably didn't see anything but tests scroll by.

If you found a problem or are trying to write a test, you can file an
[issue on github](https://github.com/vcs-python/libvcs/issues).

#### Test runner options

Test only a file:

    $ py.test tests/test_util.py

will test the `tests/test_util.py` tests.

    $ py.test tests/test_util.py::test_mkdir_p

tests `test_mkdir_p` inside of `tests/test_util.py`.

Multiple can be separated by spaces:

    $ py.test tests/test_{git,svn}.py tests/test_util.py::test_mkdir_p

## Docs

Build docs to _site/_:

    $ make build_docs

Serve docs from http://localhost:8000:

    $ make serve_docs

Rebuild docs when files are edited (requires [`entr(1)`](http://eradman.com/entrproject/)):

    $ make watch_docs

Serve + watch w/ rebuild (requires `make(1)` w/ `-j` support, usually GNU Make):

    $ make dev_docs
