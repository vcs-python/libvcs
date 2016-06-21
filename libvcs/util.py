# -*- coding: utf-8 -*-
"""Utility functions for libvcs.

libvcs.util
~~~~~~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

import contextlib
import errno
import logging
import os
import re
import subprocess
import sys
import time
import itertools
import threading
from functools import wraps

from . import exc
from ._compat import PY2, console_to_str, string_types, WINDOWS

logger = logging.getLogger(__name__)

HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'

_log_state = threading.local()
_log_state.indentation = 0


@contextlib.contextmanager
def indent_log(num=2):
    """
    A context manager which will cause the log output to be indented for any
    log messages emitted inside it.
    """
    _log_state.indentation += num
    try:
        yield
    finally:
        _log_state.indentation -= num


def get_indentation():
    return getattr(_log_state, 'indentation', 0)


def remove_tracebacks(output):
    pattern = (r'(?:\W+File "(?:.*)", line (?:.*)\W+(?:.*)\W+\^\W+)?'
               r'Syntax(?:Error|Warning): (?:.*)')
    output = re.sub(pattern, '', output)
    if PY2:
        return output
    # compileall.compile_dir() prints different messages to stdout
    # in Python 3
    return re.sub(r"\*\*\* Error compiling (?:.*)", '', output)


def run(
    cmd,
    cwd=None,
    stdin=None,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=False,
    env=None,
    timeout=None,
    check_returncode = True,
    spinner=None
):
    """Run command and return output.

    :returns: combined stdout/stderr in a big string, newline symbols retained
    :rtype: str
    """
    if isinstance(cmd, string_types):
        cmd = cmd.split(' ')
    if isinstance(cmd, list):
        cmd[0] = which(cmd[0])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=stdout,
            stderr=stderr,
            env=env, cwd=cwd
        )
    except (OSError, IOError) as e:
        raise exc.LibVCSException('Unable to run command: %s' % e)

    all_output = []
    while True:
        line = console_to_str(proc.stdout.readline())
        if not line:
            break
        line = line.rstrip()
        all_output.append(line + '\n')
        if logger.getEffectiveLevel() <= logging.DEBUG:
            # Show the line immediately
            logger.debug(line)
        else:
            # Update the spinner
            if spinner is not None:
                spinner.spin()

    if spinner is not None:
        if proc.returncode:
            spinner.finish("error")
        else:
            spinner.finish("done")
    proc.wait()

    all_output = ''.join(all_output)

    if check_returncode and proc.returncode:
        logging.error(all_output)
        raise exc.SubprocessError(
            returncode=proc.returncode,
            cmd=cmd,
            output=all_output,
        )

    return remove_tracebacks(all_output).rstrip()


def real_memoize(func):
    '''
    Memoize aka cache the return output of a function
    given a specific set of arguments
    '''
    cache = {}

    @wraps(func)
    def _memoize(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return _memoize


def which(exe=None):
    """Return path of bin. Python clone of /usr/bin/which.

    from salt.util - https://www.github.com/saltstack/salt - license apache

    :param exe: Application to search PATHs for.
    :type exe: string
    :rtype: string
    """
    def _is_executable_file_or_link(exe):
        # check for os.X_OK doesn't suffice because directory may executable
        return (os.access(exe, os.X_OK) and
                (os.path.isfile(exe) or os.path.islink(exe)))

    if _is_executable_file_or_link(exe):
        # executable in cwd or fullpath
        return exe

    ext_list = os.environ.get('PATHEXT', '.EXE').split(';')

    @real_memoize
    def _exe_has_ext():
        '''
        Do a case insensitive test if exe has a file extension match in
        PATHEXT
        '''
        for ext in ext_list:
            try:
                pattern = r'.*\.' + ext.lstrip('.') + r'$'
                re.match(pattern, exe, re.I).groups()
                return True
            except AttributeError:
                continue
        return False

    # Enhance POSIX path for the reliability at some environments, when
    # $PATH is changing. This also keeps order, where 'first came, first
    # win' for cases to find optional alternatives
    search_path = os.environ.get('PATH') and \
        os.environ['PATH'].split(os.pathsep) or list()
    for default_path in [
        '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin'
    ]:
        if default_path not in search_path:
            search_path.append(default_path)
    os.environ['PATH'] = os.pathsep.join(search_path)
    for path in search_path:
        full_path = os.path.join(path, exe)
        if _is_executable_file_or_link(full_path):
            return full_path
    logger.trace(
        '\'{0}\' could not be found in the following search path: '
        '\'{1}\''.format(exe, search_path))

    return None


def mkdir_p(path):
    """Make directories recursively.

    :param path: path to create
    :type path: string
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise Exception('Could not create directory %s' % path)


################################################################
# Generic "something is happening" spinners
#
# We don't even try using progress.spinner.Spinner here because it's actually
# simpler to reimplement from scratch than to coerce their code into doing
# what we need.
################################################################

@contextlib.contextmanager
def hidden_cursor(file):
    # The Windows terminal does not support the hide/show cursor ANSI codes,
    # even via colorama. So don't even try.
    if WINDOWS:
        yield
    # We don't want to clutter the output with control characters if we're
    # writing to a file, or if the user is running with --quiet.
    # See https://github.com/pypa/pip/issues/3418
    elif not file.isatty() or logger.getEffectiveLevel() > logging.INFO:
        yield
    else:
        file.write(HIDE_CURSOR)
        try:
            yield
        finally:
            file.write(SHOW_CURSOR)

class RateLimiter(object):
    def __init__(self, min_update_interval_seconds):
        self._min_update_interval_seconds = min_update_interval_seconds
        self._last_update = 0

    def ready(self):
        now = time.time()
        delta = now - self._last_update
        return delta >= self._min_update_interval_seconds

    def reset(self):
        self._last_update = time.time()


class InteractiveSpinner(object):
    def __init__(self, message, file=None, spin_chars="-\\|/",
                 # Empirically, 8 updates/second looks nice
                 min_update_interval_seconds=0.125):
        self._message = message
        if file is None:
            file = sys.stdout
        self._file = file
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._finished = False

        self._spin_cycle = itertools.cycle(spin_chars)

        self._file.write(" " * get_indentation() + self._message + " ... ")
        self._width = 0

    def _write(self, status):
        assert not self._finished
        # Erase what we wrote before by backspacing to the beginning, writing
        # spaces to overwrite the old text, and then backspacing again
        backup = "\b" * self._width
        self._file.write(backup + " " * self._width + backup)
        # Now we have a blank slate to add our status
        self._file.write(status)
        self._width = len(status)
        self._file.flush()
        self._rate_limiter.reset()

    def spin(self):
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._write(next(self._spin_cycle))

    def finish(self, final_status):
        if self._finished:
            return
        self._write(final_status)
        self._file.write("\n")
        self._file.flush()
        self._finished = True


# Used for dumb terminals, non-interactive installs (no tty), etc.
# We still print updates occasionally (once every 60 seconds by default) to
# act as a keep-alive for systems like Travis-CI that take lack-of-output as
# an indication that a task has frozen.
class NonInteractiveSpinner(object):
    def __init__(self, message, min_update_interval_seconds=60):
        self._message = message
        self._finished = False
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._update("started")

    def _update(self, status):
        assert not self._finished
        self._rate_limiter.reset()
        logger.info("%s: %s", self._message, status)

    def spin(self):
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._update("still running...")

    def finish(self, final_status):
        if self._finished:
            return
        self._update("finished with status '%s'" % (final_status,))
        self._finished = True


@contextlib.contextmanager
def open_spinner(message):
    # Interactive spinner goes directly to sys.stdout rather than being routed
    # through the logging system, but it acts like it has level INFO,
    # i.e. it's only displayed if we're at level INFO or better.
    # Non-interactive spinner goes through the logging system, so it is always
    # in sync with logging configuration.
    if sys.stdout.isatty() and logger.getEffectiveLevel() <= logging.INFO:
        spinner = InteractiveSpinner(message)
    else:
        spinner = NonInteractiveSpinner(message)
    try:
        with hidden_cursor(sys.stdout):
            yield spinner
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    else:
        spinner.finish("done")
