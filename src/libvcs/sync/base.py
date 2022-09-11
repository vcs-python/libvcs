"""Base class for VCS Project plugins."""
import logging
import pathlib
from collections.abc import Sequence
from typing import Any, NamedTuple, Optional
from urllib import parse as urlparse

from libvcs._internal.run import _CMD, CmdLoggingAdapter, ProgressCallbackProtocol, run
from libvcs._internal.types import StrPath

logger = logging.getLogger(__name__)


class VCSLocation(NamedTuple):
    url: str
    rev: Optional[str]


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Parse pip URL via `libvcs.sync.base.BaseSync.url`."""
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


class BaseSync:
    """Base class for repositories."""

    log_in_real_time = None
    """Log command output to buffer"""

    bin_name: str = ""
    """VCS app name, e.g. 'git'"""

    schemes: tuple[str, ...] = ()
    """List of supported schemes to register in ``urlparse.uses_netloc``"""

    def __init__(
        self,
        *,
        url: str,
        dir: StrPath,
        progress_callback: Optional[ProgressCallbackProtocol] = None,
        **kwargs: Any,
    ) -> None:
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
            >>> class Project(BaseSync):
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
            >>> r.obtain()
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

    @property
    def repo_name(self) -> str:
        return self.dir.stem

    @classmethod
    def from_pip_url(cls, pip_url: str, **kwargs: Any) -> "BaseSync":
        url, rev = convert_pip_url(pip_url)
        self = cls(url=url, rev=rev, **kwargs)

        return self

    def run(
        self,
        cmd: _CMD,
        cwd: None = None,
        check_returncode: bool = True,
        log_in_real_time: Optional[bool] = None,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Return combined stderr/stdout from a command.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd `libvcs.sync.base.BaseSync.dir` of the repo.

        Parameters
        ----------
        cwd : str
            dir command is run from, defaults to `libvcs.sync.base.BaseSync.dir`.

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

        if isinstance(cmd, Sequence):
            cmd = [self.bin_name, *cmd]
        else:
            cmd = [self.bin_name, cmd]

        return run(
            cmd,
            callback=(
                self.progress_callback if callable(self.progress_callback) else None
            ),
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time or self.log_in_real_time or False,
            cwd=cwd,
        )

    def ensure_dir(self, *args: Any, **kwargs: Any) -> bool:
        """Assure destination path exists. If not, create directories."""
        if self.dir.exists():
            return True

        if not self.dir.parent.exists():
            self.dir.parent.mkdir(parents=True)

        if not self.dir.exists():
            self.log.debug(
                "Project directory for %s does not exist @ %s"
                % (self.repo_name, self.dir)
            )
            self.dir.mkdir(parents=True)

        return True

    def update_repo(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def obtain(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.repo_name}>"
