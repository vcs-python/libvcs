"""Base class for Repository objects."""
import logging
import os
from typing import NamedTuple
from urllib import parse as urlparse

from .util import RepoLoggingAdapter, mkdir_p, run

logger = logging.getLogger(__name__)


class VCSLocation(NamedTuple):
    url: str
    rev: str


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Return repo URL and revision by parsing `libvcs.base.BaseRepo.url`."""
    error_message = (
        "Sorry, '%s' is a malformed VCS url. "
        "The format is <vcs>+<protocol>://<url>, "
        "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp"
    )
    assert "+" in pip_url, error_message % pip_url
    url = pip_url.split("+", 1)[1]
    scheme, netloc, path, query, frag = urlparse.urlsplit(url)
    rev = None
    if "@" in path:
        path, rev = path.rsplit("@", 1)
    url = urlparse.urlunsplit((scheme, netloc, path, query, ""))
    return VCSLocation(url=url, rev=rev)


class BaseRepo(RepoLoggingAdapter):

    """Base class for repositories.

    Extends :py:class:`logging.LoggerAdapter`.
    """

    #: log command output to buffer
    log_in_real_time = None

    #: vcs app name, e.g. 'git'
    bin_name = ""

    def __init__(self, url, repo_dir, progress_callback=None, *args, **kwargs):
        """
        Parameters
        ----------
        progress_callback : func
            Retrieve live progress from ``sys.stderr`` (useful for certain vcs commands
            like ``git pull``. Use ``progress_callback``:

            >>> def progress_cb(output, timestamp):
            >>>     sys.stdout.write(output)
            >>>     sys.stdout.flush()
            >>> create_repo(..., progress_callback=progress_cb)
        """
        self.progress_callback = progress_callback
        self.url = url
        self.parent_dir = os.path.dirname(repo_dir)
        self.repo_name = os.path.basename(os.path.normpath(repo_dir))
        self.path = repo_dir
        if "rev" in kwargs:
            self.rev = kwargs["rev"]

        # Register more schemes with urlparse for various version control
        # systems
        if hasattr(self, "schemes"):
            urlparse.uses_netloc.extend(self.schemes)
            # Python >= 2.7.4, 3.3 doesn't have uses_fragment
            if getattr(urlparse, "uses_fragment", None):
                urlparse.uses_fragment.extend(self.schemes)

        RepoLoggingAdapter.__init__(self, logger, {})

    @classmethod
    def from_pip_url(cls, pip_url, *args, **kwargs):
        url, rev = convert_pip_url(pip_url)
        self = cls(url=url, rev=rev, *args, **kwargs)

        return self

    def run(
        self,
        cmd,
        cwd=None,
        check_returncode=True,
        log_in_real_time=None,
        *args,
        **kwargs,
    ):
        """Return combined stderr/stdout from a command.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd `libvcs.base.BaseRepo.path` of the repo.

        Parameters
        ----------
        cwd : str
            dir command is run from, defaults to `libvcs.base.BaseRepo.path`.

        check_returncode : bool
            Indicate whether a :exc:`~exc.CommandError` should be raised if return code
            is different from 0.

        Returns
        -------
        str
            combined stdout/stderr in a big string, newlines retained
        """

        if cwd is None:
            cwd = getattr(self, "path", None)

        cmd = [self.bin_name] + cmd

        return run(
            cmd,
            callback=(
                self.progress_callback if callable(self.progress_callback) else None
            ),
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time or self.log_in_real_time,
            cwd=cwd,
        )

    def ensure_dir(self, *args, **kwargs):
        """Assure destination path exists. If not, create directories."""
        if os.path.exists(self.path):
            return True

        if not os.path.exists(self.parent_dir):
            mkdir_p(self.parent_dir)

        if not os.path.exists(self.path):
            self.debug(
                "Repo directory for %s does not exist @ %s"
                % (self.repo_name, self.path)
            )
            mkdir_p(self.path)

        return True

    def update_repo(self, *args, **kwargs):
        raise NotImplementedError

    def obtain(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.repo_name}>"
