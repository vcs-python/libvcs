# -*- coding: utf-8 -*-
"""Base class for Repository objects.

libvcs.base
~~~~~~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

import logging
import os
import subprocess

from ._compat import urlparse
from .util import mkdir_p, run

logger = logging.getLogger(__name__)


class RepoLoggingAdapter(logging.LoggerAdapter):

    """Adapter for adding Repo related content to logger.

    Extends :class:`logging.LoggerAdapter`'s functionality.

    The standard library :py:mod:`logging` facility is pretty complex, so this
    warrants and explanation of what's happening.

    Any class that subclasses this will have its class attributes for:

        - :attr:`~.bin_name` -> ``repo_vcs``
        - :attr:`~.name` -> ``repo_name``

    Added to a dictionary of context information in :py:meth:`
    logging.LoggerAdapter.process()` to be made use of when the user of this
    library wishes to use a custom :class:`logging.Formatter` to output
    results.

    """

    def __init__(self, *args, **kwargs):
        logging.LoggerAdapter.__init__(self, *args, **kwargs)

    def process(self, msg, kwargs):
        """Add additional context information for loggers."""
        prefixed_dict = {}
        prefixed_dict['repo_vcs'] = self.bin_name
        prefixed_dict['repo_name'] = self.name

        kwargs["extra"] = prefixed_dict

        return msg, kwargs


class BaseRepo(RepoLoggingAdapter, object):

    """Base class for repositories.

    Extends :py:class:`logging.LoggerAdapter`.
    """

    def __init__(self, url, repo_dir, *args, **kwargs):
        self.__dict__.update(kwargs)

        self.url = url
        self.parent_dir = os.path.dirname(repo_dir)
        self.name = os.path.basename(os.path.normpath(repo_dir))
        self.path = repo_dir

        # Register more schemes with urlparse for various version control
        # systems
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
        extra_env=None, cwd=None, check_returncode=True, *args, **kwargs
    ):
        """Return combined stderr/stdout from a command.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd :attr:`~.path` of the repo.

        :param cwd: dir command is run from, defaults :attr:`~.path`.
        :type cwd: string

        :param check_returncode: Indicate whether a :exc:`~exc.SubprocessError`
            should be raised if return code is different from 0.
        :type check_returncode: :class:`bool`

        :returns: combined stdout/stderr in a big string, newlines retained
        :rtype: str
        """

        if cwd is None:
            cwd = getattr(self, 'path', None)

        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        cmd = [self.bin_name] + cmd

        return run(
            cmd,
            stdout=stdout,
            stderr=stderr,
            env=env, cwd=cwd,
            check_returncode=check_returncode,
            *args, **kwargs
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

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

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
