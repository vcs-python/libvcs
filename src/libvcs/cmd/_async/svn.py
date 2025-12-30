"""Async svn (subversion) commands directly against SVN working copy.

Async equivalent of :mod:`libvcs.cmd.svn`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import pathlib
import typing as t
from collections.abc import Sequence

from libvcs._internal.async_run import (
    AsyncProgressCallbackProtocol,
    async_run,
)
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = StrOrBytesPath | Sequence[StrOrBytesPath]

DepthLiteral = t.Literal["infinity", "empty", "files", "immediates"] | None
RevisionLiteral = t.Literal["HEAD", "BASE", "COMMITTED", "PREV"] | None


class AsyncSvn:
    """Run commands directly on a Subversion working copy asynchronously.

    Async equivalent of :class:`~libvcs.cmd.svn.Svn`.

    Parameters
    ----------
    path : str | Path
        Path to the SVN working copy
    progress_callback : AsyncProgressCallbackProtocol, optional
        Async callback for progress reporting

    Examples
    --------
    >>> async def example():
    ...     repo_path = tmp_path / 'svn_wc'
    ...     svn = AsyncSvn(path=repo_path)
    ...     url = f'file://{create_svn_remote_repo()}'
    ...     await svn.checkout(url=url)
    ...     return (repo_path / '.svn').exists()
    >>> asyncio.run(example())
    True
    """

    progress_callback: AsyncProgressCallbackProtocol | None = None

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
    ) -> None:
        """Initialize AsyncSvn command wrapper.

        Parameters
        ----------
        path : str | Path
            Path to the SVN working copy
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
        """Representation of AsyncSvn command object."""
        return f"<AsyncSvn path={self.path}>"

    async def run(
        self,
        args: _CMD,
        *,
        quiet: bool | None = None,
        username: str | None = None,
        password: str | None = None,
        no_auth_cache: bool | None = None,
        non_interactive: bool | None = True,
        trust_server_cert: bool | None = None,
        config_dir: pathlib.Path | None = None,
        config_option: pathlib.Path | None = None,
        # Pass-through to async_run()
        cwd: StrOrBytesPath | None = None,
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command for this SVN working copy asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.svn.Svn.run`.

        Parameters
        ----------
        args : list[str] | str
            SVN subcommand and arguments
        quiet : bool, optional
            -q / --quiet
        username : str, optional
            --username
        password : str, optional
            --password
        no_auth_cache : bool, optional
            --no-auth-cache
        non_interactive : bool, default True
            --non-interactive
        trust_server_cert : bool, optional
            --trust-server-cert
        config_dir : Path, optional
            --config-dir
        cwd : str | Path, optional
            Working directory. Defaults to self.path.
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
            cli_args = ["svn", *[str(a) for a in args]]
        else:
            cli_args = ["svn", str(args)]

        run_cwd = cwd if cwd is not None else self.path

        # Build flags
        if no_auth_cache is True:
            cli_args.append("--no-auth-cache")
        if non_interactive is True:
            cli_args.append("--non-interactive")
        if username is not None:
            cli_args.extend(["--username", username])
        if password is not None:
            cli_args.extend(["--password", password])
        if trust_server_cert is True:
            cli_args.append("--trust-server-cert")
        if config_dir is not None:
            cli_args.extend(["--config-dir", str(config_dir)])
        if config_option is not None:
            cli_args.extend(["--config-option", str(config_option)])

        return await async_run(
            cli_args,
            cwd=run_cwd,
            callback=self.progress_callback if log_in_real_time else None,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def checkout(
        self,
        *,
        url: str,
        revision: RevisionLiteral | str = None,
        force: bool | None = None,
        ignore_externals: bool | None = None,
        depth: DepthLiteral = None,
        quiet: bool | None = None,
        username: str | None = None,
        password: str | None = None,
        no_auth_cache: bool | None = None,
        non_interactive: bool | None = True,
        trust_server_cert: bool | None = None,
        # Special behavior
        make_parents: bool | None = True,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Check out a working copy from an SVN repo asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.svn.Svn.checkout`.

        Parameters
        ----------
        url : str
            Repository URL to checkout
        revision : str, optional
            Number, '{ DATE }', 'HEAD', 'BASE', 'COMMITTED', 'PREV'
        force : bool, optional
            Force operation to run
        ignore_externals : bool, optional
            Ignore externals definitions
        depth : str, optional
            Sparse checkout depth
        quiet : bool, optional
            Suppress output
        username : str, optional
            SVN username
        password : str, optional
            SVN password
        make_parents : bool, default True
            Create checkout directory if it doesn't exist
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        # URL and PATH come first, matching sync Svn.checkout pattern
        local_flags: list[str] = [url, str(self.path)]

        if revision is not None:
            local_flags.extend(["--revision", str(revision)])
        if depth is not None:
            local_flags.extend(["--depth", depth])
        if force is True:
            local_flags.append("--force")
        if ignore_externals is True:
            local_flags.append("--ignore-externals")
        if quiet is True:
            local_flags.append("--quiet")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)

        return await self.run(
            ["checkout", *local_flags],
            username=username,
            password=password,
            no_auth_cache=no_auth_cache,
            non_interactive=non_interactive,
            trust_server_cert=trust_server_cert,
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )

    async def update(
        self,
        accept: str | None = None,
        force: bool | None = None,
        ignore_externals: bool | None = None,
        parents: bool | None = None,
        quiet: bool | None = None,
        revision: str | None = None,
        set_depth: str | None = None,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Fetch latest changes to working copy asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.svn.Svn.update`.

        Parameters
        ----------
        accept : str, optional
            Conflict resolution action
        force : bool, optional
            Force operation
        ignore_externals : bool, optional
            Ignore externals definitions
        parents : bool, optional
            Make intermediate directories
        quiet : bool, optional
            Suppress output
        revision : str, optional
            Update to specific revision
        set_depth : str, optional
            Set new working copy depth
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

        if revision is not None:
            local_flags.extend(["--revision", revision])
        if set_depth is not None:
            local_flags.extend(["--set-depth", set_depth])
        if accept is not None:
            local_flags.extend(["--accept", accept])
        if force is True:
            local_flags.append("--force")
        if ignore_externals is True:
            local_flags.append("--ignore-externals")
        if parents is True:
            local_flags.append("--parents")
        if quiet is True:
            local_flags.append("--quiet")

        return await self.run(
            ["update", *local_flags],
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )

    async def info(
        self,
        target: StrPath | None = None,
        revision: str | None = None,
        depth: DepthLiteral = None,
        incremental: bool | None = None,
        recursive: bool | None = None,
        xml: bool | None = None,
        # Pass-through
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Return info about this SVN repository asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.svn.Svn.info`.

        Parameters
        ----------
        target : str | Path, optional
            Target path or URL
        revision : str, optional
            Revision to get info for
        depth : str, optional
            Limit operation depth
        incremental : bool, optional
            Give output suitable for concatenation
        recursive : bool, optional
            Descend recursively
        xml : bool, optional
            Output in XML format
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output (optionally XML)
        """
        local_flags: list[str] = []

        if isinstance(target, pathlib.Path):
            local_flags.append(str(target.absolute()))
        elif isinstance(target, str):
            local_flags.append(target)

        if revision is not None:
            local_flags.extend(["--revision", revision])
        if depth is not None:
            local_flags.extend(["--depth", depth])
        if incremental is True:
            local_flags.append("--incremental")
        if recursive is True:
            local_flags.append("--recursive")
        if xml is True:
            local_flags.append("--xml")

        return await self.run(
            ["info", *local_flags],
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
        )
