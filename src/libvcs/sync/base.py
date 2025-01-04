"""Foundational tools to set up a VCS manager in libvcs.sync."""

from __future__ import annotations

import logging
import pathlib
import typing as t
from collections.abc import Sequence
from urllib import parse as urlparse

from libvcs._internal.run import _CMD, CmdLoggingAdapter, ProgressCallbackProtocol, run

if t.TYPE_CHECKING:
    from libvcs._internal.types import StrPath

logger = logging.getLogger(__name__)


class VCSLocation(t.NamedTuple):
    """Generic VCS Location (URL and optional revision)."""

    url: str
    rev: str | None


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Parse pip URL via `libvcs.sync.base.BaseSync.url`."""
    error_message = (
        "Sorry, '%s' is a malformed VCS url. "
        "The format is <vcs>+<protocol>://<url>, "
        "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp"
    )
    assert "+" in pip_url, error_message % pip_url
    url = pip_url.split("+", 1)[1]
    scheme, netloc, path, query, _frag = urlparse.urlsplit(url)
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
        path: StrPath,
        progress_callback: ProgressCallbackProtocol | None = None,
        **kwargs: t.Any,
    ) -> None:
        r"""Initialize a tool to manage a local VCS Checkout, Clone, Copy, or Work tree.

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
            ...             ['clone', '--progress', self.url, self.path],
            ...             log_in_real_time=True
            ...         )
            >>> r = Project(
            ...     url=f'file://{create_git_remote_repo()}',
            ...     path=str(tmp_path),
            ...     progress_callback=progress_cb
            ... )
            >>> r.obtain()
            Cloning into '...'...
            remote: Enumerating objects: ...
            remote: Counting objects: ...% (...)...
            ...
            remote: Total ... (delta 0), reused 0 (delta 0), pack-reused 0
            ...
            Receiving objects: ...% (...)...
            ...
            >>> assert r.path.exists()
            >>> assert pathlib.Path(r.path / '.git').exists()
        """
        self.url = url

        #: Callback for run updates
        self.progress_callback = progress_callback

        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

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
            bin_name=self.bin_name,
            keyword=self.repo_name,
            logger=logger,
            extra={},
        )

    @property
    def repo_name(self) -> str:
        """Return the short name of a repo checkout."""
        return self.path.stem

    @classmethod
    def from_pip_url(cls, pip_url: str, **kwargs: t.Any) -> BaseSync:
        """Create synchronization object from pip-style URL."""
        url, rev = convert_pip_url(pip_url)
        return cls(url=url, rev=rev, **kwargs)

    def run(
        self,
        cmd: _CMD,
        cwd: None = None,
        check_returncode: bool = True,
        log_in_real_time: bool | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        """Return combined stderr/stdout from a command.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd `libvcs.sync.base.BaseSync.path` of the repo.

        Parameters
        ----------
        cwd : str
            dir command is run from, defaults to `libvcs.sync.base.BaseSync.path`.

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

    def ensure_dir(self, *args: t.Any, **kwargs: t.Any) -> bool:
        """Assure destination path exists. If not, create directories."""
        if self.path.exists():
            return True

        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)

        if not self.path.exists():
            self.log.debug(
                f"Project directory for {self.repo_name} does not exist @ {self.path}",
            )
            self.path.mkdir(parents=True)

        return True

    def update_repo(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Pull latest changes to here from remote repository."""
        raise NotImplementedError

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Checkout initial VCS repository or working copy from remote repository."""
        raise NotImplementedError

    def __repr__(self) -> str:
        """Representation of a VCS management object."""
        return f"<{self.__class__.__name__} {self.repo_name}>"
