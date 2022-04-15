"""Base class for Projectsitory objects."""
import logging
import pathlib
from typing import NamedTuple
from urllib import parse as urlparse

from libvcs.cmd.core import CmdLoggingAdapter, mkdir_p, run
from libvcs.types import StrOrPath

logger = logging.getLogger(__name__)


class VCSLocation(NamedTuple):
    url: str
    rev: str


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Parse pip URL via `libvcs.projects.base.BaseProject.url`."""
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


class BaseProject:
    """Base class for repositories."""

    #: log command output to buffer
    log_in_real_time = None

    #: vcs app name, e.g. 'git'
    bin_name = ""

    def __init__(self, url, dir: StrOrPath, progress_callback=None, *args, **kwargs):
        r"""
        Parameters
        ----------
        progress_callback : func
            Retrieve live progress from ``sys.stderr`` (useful for certain vcs commands
            like ``git pull``. Use ``progress_callback``:

            >>> import os
            >>> import sys
            >>> def progress_cb(output, timestamp):
            ...     sys.stdout.write(output)
            ...     sys.stdout.flush()
            >>> class Project(BaseProject):
            ...     bin_name = 'git'
            ...     def obtain(self, *args, **kwargs):
            ...         self.ensure_dir()
            ...         self.run(
            ...             ['clone', '--progress', self.url, self.dir],
            ...             log_in_real_time=True
            ...         )
            >>> r = Project(
            ...     url=f'file://{create_git_remote_repo()}',
            ...     dir=str(tmp_path),
            ...     progress_callback=progress_cb
            ... )
            >>> r.obtain()  # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS +REPORT_CDIFF
            Cloning into '...'...
            remote: Enumerating objects: ..., done...
            remote: Counting objects: 100% (...), done...
            remote: Total ... (delta 0), reused 0 (delta 0), pack-reused 0...
            Receiving objects: 100% (...), done...
            >>> assert r.dir.exists()
            >>> assert pathlib.Path(r.dir / '.git').exists()
        """
        self.url = url

        #: Callback for run updates
        self.progress_callback = progress_callback

        #: Directory to check out
        self.dir: pathlib.Path
        if isinstance(dir, pathlib.Path):
            self.dir = dir
        else:
            self.dir = pathlib.Path(dir)

        #: Parent directory
        self.parent_dir = self.dir.parent

        #: Base name of checkout
        self.repo_name = self.dir.stem

        if "rev" in kwargs:
            self.rev = kwargs["rev"]

        # Register more schemes with urlparse for various version control
        # systems
        if hasattr(self, "schemes"):
            urlparse.uses_netloc.extend(self.schemes)
            # Python >= 2.7.4, 3.3 doesn't have uses_fragment
            if getattr(urlparse, "uses_fragment", None):
                urlparse.uses_fragment.extend(self.schemes)

        #: Logging attribute
        self.log: CmdLoggingAdapter = CmdLoggingAdapter(
            bin_name=self.bin_name, keyword=self.repo_name, logger=logger, extra={}
        )

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
        using the cwd `libvcs.projects.base.BaseProject.dir` of the repo.

        Parameters
        ----------
        cwd : str
            dir command is run from, defaults to `libvcs.projects.base.BaseProject.dir`.

        check_returncode : bool
            Indicate whether a :exc:`~exc.CommandError` should be raised if return code
            is different from 0.

        Returns
        -------
        str
            combined stdout/stderr in a big string, newlines retained
        """

        if cwd is None:
            cwd = getattr(self, "dir", None)

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
        if self.dir.exists():
            return True

        if not self.parent_dir.exists():
            mkdir_p(self.parent_dir)

        if not self.dir.exists():
            self.log.debug(
                "Project directory for %s does not exist @ %s"
                % (self.repo_name, self.dir)
            )
            mkdir_p(self.dir)

        return True

    def update_repo(self, *args, **kwargs):
        raise NotImplementedError

    def obtain(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.repo_name}>"
