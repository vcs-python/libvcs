# -*- coding: utf-8 -*-
"""Exceptions for libvcs.

libvcs.exc
~~~~~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

from subprocess import CalledProcessError


class LibVCSException(Exception):

    """Standard exception raised by libvcs."""

    pass


class SubprocessError(LibVCSException, CalledProcessError):
    """This exception is raised on non-zero Base.run, util.run return codes."""

    def __init__(self, returncode, cmd, output):
        CalledProcessError.__init__(self,
                                    returncode=returncode,
                                    cmd=cmd,
                                    output=output)

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d: \n%s" % (
            self.cmd, self.returncode, self.output)


class InvalidPipURL(LibVCSException):
    """Invalid pip-style URL."""
    def __init__(self, url):
        self.url = url
        super(InvalidPipURL, self).__init__()

    def __str__(self):
        return self.message % (
            self.url,
            'git+https://github.com/freebsd/freebsd.git',
            'hg+https://bitbucket.org/birkenfeld/sphinx',
            'svn+http://svn.code.sf.net/p/docutils/code/trunk'
        )

    message = (
        'repo URL %s requires a vcs scheme. Prepend hg+,'
        ' git+, svn+ to the repo URL. Examples:\n'
        '\t %s\n'
        '\t %s\n'
        '\t %s\n'
    )


class InvalidVCS(LibVCSException):
    """Invalid VCS."""
    pass
