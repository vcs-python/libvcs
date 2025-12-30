"""Foundational tools for async VCS managers.

Async equivalent of :mod:`libvcs.sync.base`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import logging
import pathlib
import typing as t
from urllib import parse as urlparse

from libvcs._internal.async_run import (
    AsyncProgressCallbackProtocol,
    async_run,
)
from libvcs._internal.run import CmdLoggingAdapter
from libvcs._internal.types import StrPath
from libvcs.sync.base import convert_pip_url

logger = logging.getLogger(__name__)


class AsyncBaseSync:
    """Base class for async repository synchronization.

    Async equivalent of :class:`~libvcs.sync.base.BaseSync`.
    """

    log_in_real_time: bool | None = None
    """Log command output to buffer"""

    bin_name: str = ""
    """VCS app name, e.g. 'git'"""

    schemes: tuple[str, ...] = ()
    """List of supported schemes to register in urlparse.uses_netloc"""

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Initialize async VCS synchronization object.

        Parameters
        ----------
        url : str
            URL of the repository
        path : str | Path
            Local path for the repository
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress updates

        Examples
        --------
        >>> import asyncio
        >>> class MyRepo(AsyncBaseSync):
        ...     bin_name = 'git'
        ...     async def obtain(self):
        ...         await self.run(['clone', self.url, str(self.path)])
        """
        self.url = url

        #: Async callback for run updates
        self.progress_callback = progress_callback

        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        if "rev" in kwargs:
            self.rev = kwargs["rev"]

        # Register schemes with urlparse
        if hasattr(self, "schemes"):
            urlparse.uses_netloc.extend(self.schemes)
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
    def from_pip_url(cls, pip_url: str, **kwargs: t.Any) -> AsyncBaseSync:
        """Create async synchronization object from pip-style URL."""
        url, rev = convert_pip_url(pip_url)
        return cls(url=url, rev=rev, **kwargs)

    async def run(
        self,
        cmd: StrPath | list[StrPath],
        cwd: StrPath | None = None,
        check_returncode: bool = True,
        log_in_real_time: bool | None = None,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command asynchronously.

        This method will also prefix the VCS command bin_name. By default runs
        using the cwd of the repo.

        Parameters
        ----------
        cmd : str | list[str]
            Command and arguments to run
        cwd : str | Path, optional
            Working directory, defaults to self.path
        check_returncode : bool, default True
            Raise on non-zero exit code
        log_in_real_time : bool, optional
            Stream output to callback
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Combined stdout/stderr output
        """
        if cwd is None:
            cwd = getattr(self, "path", None)

        if isinstance(cmd, list):
            full_cmd = [self.bin_name, *[str(c) for c in cmd]]
        else:
            full_cmd = [self.bin_name, str(cmd)]

        should_log = log_in_real_time or self.log_in_real_time or False

        return await async_run(
            full_cmd,
            callback=self.progress_callback if should_log else None,
            check_returncode=check_returncode,
            cwd=cwd,
            timeout=timeout,
            **kwargs,
        )

    def ensure_dir(self, *args: t.Any, **kwargs: t.Any) -> bool:
        """Assure destination path exists. If not, create directories.

        Note: This is synchronous as it's just filesystem operations.
        """
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

    async def update_repo(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Pull latest changes from remote repository."""
        raise NotImplementedError

    async def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Checkout initial VCS repository from remote repository."""
        raise NotImplementedError

    def __repr__(self) -> str:
        """Representation of async VCS management object."""
        return f"<{self.__class__.__name__} {self.repo_name}>"
