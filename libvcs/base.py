# -*- coding: utf-8 -*-
"""Base class for Repository objects.

libvcs.base
~~~~~~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

import logging
import os
import subprocess

from ._compat import urlparse, implements_to_string
from .util import RepoLoggingAdapter, mkdir_p, run

logger = logging.getLogger(__name__)


@implements_to_string
class BaseRepo(RepoLoggingAdapter, object):

    """Base class for repositories.

    Extends :py:class:`logging.LoggerAdapter`.

    """

    #: log command output to buffer
    log_in_real_time = None

    #: vcs app name, e.g. 'git'
    bin_name = ''

    def __init__(self, url, repo_dir, progress_callback=None, *args, **kwargs):
        """
        :param callback: Retrieve live progress from ``sys.stderr`` (useful for
            certain vcs commands like ``git pull``. Use ``progress_callback``::

                def progress_cb(output, timestamp):
                    sys.stdout.write(output)
                    sys.stdout.flush()
                create_repo(..., progress_callback=progress_cb)
        :type callback: func
        """
        self.__dict__.update(kwargs)
        self.progress_callback = progress_callback
        self.url = url
        self.parent_dir = os.path.dirname(repo_dir)
        self.name = os.path.basename(os.path.normpath(repo_dir))
        self.path = repo_dir

        # Register more schemes with urlparse for various version control
        # systems
        if hasattr(self, 'schemes'):
            urlparse.uses_netloc.extend(self.schemes)
            # Python >= 2.7.4, 3.3 doesn't have uses_fragment
            if getattr(urlparse, 'uses_fragment', None):
                urlparse.uses_fragment.extend(self.schemes)

        RepoLoggingAdapter.__init__(self, logger, {})

    @classmethod
    def from_pip_url(cls, pip_url, *args, **kwargs):
        url, rev = cls.get_url_and_revision_from_pip_url(pip_url)
        self = cls(url=url, rev=rev, *args, **kwargs)

        return self

    def run(
        self, cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=None, check_returncode=True, log_in_real_time=None,
        *args, **kwargs
    ):
        """Return combined stderr/stdout from a command.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd :attr:`~.path` of the repo.

        :param cwd: dir command is run from, defaults :attr:`~.path`.
        :type cwd: string

        :param check_returncode: Indicate whether a :exc:`~exc.CommandError`
            should be raised if return code is different from 0.
        :type check_returncode: :class:`bool`

        :returns: combined stdout/stderr in a big string, newlines retained
        :rtype: str
        """

        if cwd is None:
            cwd = getattr(self, 'path', None)

        cmd = [self.bin_name] + cmd

        return run(
            cmd,
            callback=(
                self.progress_callback
                if callable(self.progress_callback)
                else None
            ),
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time or self.log_in_real_time,
            cwd=cwd
        )

    def check_destination(self, *args, **kwargs):
        """Assure destination path exists. If not, create directories."""
        if not os.path.exists(self.parent_dir):
            mkdir_p(self.parent_dir)
        else:
            if not os.path.exists(self.path):
                self.debug('Repo directory for %s does not exist @ %s' % (
                    self.name, self.path))
                mkdir_p(self.path)

        return True

    @classmethod
    def get_url_and_revision_from_pip_url(cls, pip_url):
        """Return repo URL and revision by parsing :attr:`~.url`."""
        error_message = (
            "Sorry, '%s' is a malformed VCS url. "
            "The format is <vcs>+<protocol>://<url>, "
            "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp")
        assert '+' in pip_url, error_message % pip_url
        url = pip_url.split('+', 1)[1]
        scheme, netloc, path, query, frag = urlparse.urlsplit(url)
        rev = None
        if '@' in path:
            path, rev = path.rsplit('@', 1)
        url = urlparse.urlunsplit((scheme, netloc, path, query, ''))
        return url, rev

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.name)
