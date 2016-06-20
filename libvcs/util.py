# -*- coding: utf-8 -*-
"""Utility functions for libvcs.

libvcs.util
~~~~~~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

import errno
import logging
import os
import re
import subprocess
from functools import wraps

from . import exc
from ._compat import PY2, console_to_str, string_types

logger = logging.getLogger(__name__)


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
    timeout=None
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
        process = subprocess.Popen(
            cmd,
            stdout=stdout,
            stderr=stderr,
            env=env, cwd=cwd
        )
    except (OSError, IOError) as e:
        raise exc.LibVCSException('Unable to run command: %s' % e)

    process.wait()
    all_output = []
    while True:
        line = console_to_str(process.stdout.readline())
        if not line:
            break
        line = line.rstrip()
        all_output.append(line + '\n')
    all_output = ''.join(all_output)

    if process.returncode:
        logging.error(all_output)
        raise exc.SubprocessError(
            returncode=process.returncode,
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
