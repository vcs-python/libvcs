"""Async hg (Mercurial) commands directly against a local mercurial repo.

Async equivalent of :mod:`libvcs.cmd.hg`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import enum
import pathlib
import typing as t
from collections.abc import Sequence

from libvcs._internal.async_run import (
    AsyncProgressCallbackProtocol,
    async_run,
)
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = StrOrBytesPath | Sequence[StrOrBytesPath]


class HgColorType(enum.Enum):
    """CLI Color enum for Mercurial."""

    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"
    debug = "debug"


class HgPagerType(enum.Enum):
    """CLI Pagination enum for Mercurial."""

    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"


class AsyncHg:
    """Run commands directly on a Mercurial repository asynchronously.

    Async equivalent of :class:`~libvcs.cmd.hg.Hg`.

    Parameters
    ----------
    path : str | Path
        Path to the hg repository
    progress_callback : AsyncProgressCallbackProtocol, optional
        Async callback for progress reporting

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     hg = AsyncHg(path="/path/to/repo")
    ...     output = await hg.pull()
    ...     return output
    >>> # asyncio.run(example())
    """

    progress_callback: AsyncProgressCallbackProtocol | None = None

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
    ) -> None:
        """Initialize AsyncHg command wrapper.

        Parameters
        ----------
        path : str | Path
            Path to the hg repository
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress reporting
        """
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.progress_callback = progress_callback

    def __repr__(self) -> str:
        """Representation of AsyncHg repo command object."""
        return f"<AsyncHg path={self.path}>"

    async def run(
        self,
        args: _CMD,
        *,
        config: str | None = None,
        repository: str | None = None,
        quiet: bool | None = None,
        _help: bool | None = None,
        encoding: str | None = None,
        encoding_mode: str | None = None,
        verbose: bool | None = None,
        traceback: bool | None = None,
        debug: bool | None = None,
        debugger: bool | None = None,
        profile: bool | None = None,
        version: bool | None = None,
        hidden: bool | None = None,
        time: bool | None = None,
        pager: HgPagerType | None = None,
        color: HgColorType | None = None,
        # Pass-through to async_run()
        cwd: StrOrBytesPath | None = None,
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command for this Mercurial repository asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.hg.Hg.run`.

        Parameters
        ----------
        args : list[str] | str
            Hg subcommand and arguments
        quiet : bool, optional
            -q / --quiet
        repository : str, optional
            --repository REPO
        cwd : str | Path, optional
            Working directory. Defaults to self.path.
        verbose : bool, optional
            -v / --verbose
        color : HgColorType, optional
            --color
        debug : bool, optional
            --debug
        config : str, optional
            --config CONFIG, section.name=value
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        cli_args: list[str]
        if isinstance(args, Sequence) and not isinstance(args, (str, bytes)):
            cli_args = ["hg", *[str(a) for a in args]]
        else:
            cli_args = ["hg", str(args)]

        run_cwd = cwd if cwd is not None else self.path

        # Build flags
        if repository is not None:
            cli_args.extend(["--repository", repository])
        if config is not None:
            cli_args.extend(["--config", config])
        if pager is not None:
            cli_args.extend(["--pager", pager.value])
        if color is not None:
            cli_args.extend(["--color", color.value])
        if verbose is True:
            cli_args.append("--verbose")
        if quiet is True:
            cli_args.append("--quiet")
        if debug is True:
            cli_args.append("--debug")
        if debugger is True:
            cli_args.append("--debugger")
        if traceback is True:
            cli_args.append("--traceback")
        if time is True:
            cli_args.append("--time")
        if profile is True:
            cli_args.append("--profile")
        if version is True:
            cli_args.append("--version")
        if _help is True:
            cli_args.append("--help")

        return await async_run(
            cli_args,
            cwd=run_cwd,
            callback=self.progress_callback if log_in_real_time else None,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def clone(
        self,
        *,
        url: str,
        no_update: bool | None = None,
        update_rev: str | None = None,
        rev: str | None = None,
        branch: str | None = None,
        ssh: str | None = None,
        remote_cmd: str | None = None,
        pull: bool | None = None,
        stream: bool | None = None,
        insecure: bool | None = None,
        quiet: bool | None = None,
        # Special behavior
        make_parents: bool | None = True,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Clone a working copy from a mercurial repo asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.hg.Hg.clone`.

        Parameters
        ----------
        url : str
            URL of the repository to clone
        no_update : bool, optional
            Don't update the working directory
        rev : str, optional
            Revision to clone
        branch : str, optional
            Branch to clone
        ssh : str, optional
            SSH command to use
        make_parents : bool, default True
            Creates checkout directory if it doesn't exist
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        required_flags: list[str] = [url, str(self.path)]
        local_flags: list[str] = []

        if ssh is not None:
            local_flags.extend(["--ssh", ssh])
        if remote_cmd is not None:
            local_flags.extend(["--remotecmd", remote_cmd])
        if rev is not None:
            local_flags.extend(["--rev", rev])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if no_update is True:
            local_flags.append("--noupdate")
        if pull is True:
            local_flags.append("--pull")
        if stream is True:
            local_flags.append("--stream")
        if insecure is True:
            local_flags.append("--insecure")
        if quiet is True:
            local_flags.append("--quiet")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)

        return await self.run(
            ["clone", *local_flags, "--", *required_flags],
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )

    async def update(
        self,
        quiet: bool | None = None,
        verbose: bool | None = None,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Update working directory asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.hg.Hg.update`.

        Parameters
        ----------
        quiet : bool, optional
            Suppress output
        verbose : bool, optional
            Enable verbose output
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []

        if quiet:
            local_flags.append("--quiet")
        if verbose:
            local_flags.append("--verbose")

        return await self.run(
            ["update", *local_flags],
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )

    async def pull(
        self,
        quiet: bool | None = None,
        verbose: bool | None = None,
        update: bool | None = None,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Pull changes from remote asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.hg.Hg.pull`.

        Parameters
        ----------
        quiet : bool, optional
            Suppress output
        verbose : bool, optional
            Enable verbose output
        update : bool, optional
            Update to new branch head after pull
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []

        if quiet:
            local_flags.append("--quiet")
        if verbose:
            local_flags.append("--verbose")
        if update:
            local_flags.append("--update")

        return await self.run(
            ["pull", *local_flags],
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )
