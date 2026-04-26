"""Async subprocess execution with progress callbacks.

Async equivalent of :mod:`libvcs._internal.run`.

Note
----
This is an internal API not covered by versioning policy.

Examples
--------
- :func:`~async_run`: Async command execution with progress callback.

  Before (sync):

  >>> from libvcs._internal.run import run
  >>> output = run(['echo', 'hello'], check_returncode=True)

  With this (async):

  >>> from libvcs._internal.async_run import async_run
  >>> async def example():
  ...     output = await async_run(['echo', 'hello'])
  ...     return output.strip()
  >>> asyncio.run(example())
  'hello'
"""

from __future__ import annotations

import asyncio
import asyncio.subprocess
import datetime
import logging
import sys
import typing as t
from collections.abc import Mapping, Sequence

from libvcs import exc
from libvcs._internal.types import StrOrBytesPath

from .run import console_to_str

logger = logging.getLogger(__name__)


class AsyncProgressCallbackProtocol(t.Protocol):
    """Async callback to report subprocess communication.

    Async equivalent of :class:`~libvcs._internal.run.ProgressCallbackProtocol`.

    Examples
    --------
    >>> async def my_progress(output: str, timestamp: datetime.datetime) -> None:
    ...     print(f"[{timestamp}] {output}", end="")

    See Also
    --------
    libvcs._internal.run.ProgressCallbackProtocol : Sync equivalent
    wrap_sync_callback : Helper to wrap sync callbacks for async use
    """

    async def __call__(self, output: str, timestamp: datetime.datetime) -> None:
        """Process progress for subprocess communication."""
        ...


def wrap_sync_callback(
    sync_cb: t.Callable[[str, datetime.datetime], None],
) -> AsyncProgressCallbackProtocol:
    """Wrap a sync callback for use with async APIs.

    This helper allows users with existing sync callbacks to use them
    with async APIs without modification.

    Parameters
    ----------
    sync_cb : Callable[[str, datetime.datetime], None]
        Synchronous callback function

    Returns
    -------
    AsyncProgressCallbackProtocol
        Async wrapper that calls the sync callback

    Examples
    --------
    >>> def my_sync_progress(output: str, timestamp: datetime.datetime) -> None:
    ...     print(output, end="")
    >>> async_cb = wrap_sync_callback(my_sync_progress)
    >>> # Now use async_cb with async_run()
    """

    async def wrapper(output: str, timestamp: datetime.datetime) -> None:
        sync_cb(output, timestamp)

    return wrapper


if sys.platform == "win32":
    _ENV: t.TypeAlias = Mapping[str, str]
else:
    _ENV: t.TypeAlias = Mapping[bytes, StrOrBytesPath] | Mapping[str, StrOrBytesPath]

_CMD: t.TypeAlias = StrOrBytesPath | Sequence[StrOrBytesPath]


def _args_to_list(args: _CMD) -> list[str]:
    """Convert command args to list of strings.

    Parameters
    ----------
    args : str | bytes | Path | Sequence[str | bytes | Path]
        Command arguments in various forms

    Returns
    -------
    list[str]
        Normalized list of string arguments
    """
    from os import PathLike

    if isinstance(args, (str, bytes, PathLike)):
        if isinstance(args, bytes):
            return [args.decode()]
        return [str(args)]
    return [arg.decode() if isinstance(arg, bytes) else str(arg) for arg in args]


async def async_run(
    args: _CMD,
    *,
    cwd: StrOrBytesPath | None = None,
    env: _ENV | None = None,
    check_returncode: bool = True,
    callback: AsyncProgressCallbackProtocol | None = None,
    timeout: float | None = None,
) -> str:
    """Run a command asynchronously.

    Run 'args' and return stdout content (non-blocking). Optionally stream
    stderr to a callback for progress reporting. Raises an exception if
    the command exits non-zero (when check_returncode=True).

    This is the async equivalent of :func:`~libvcs._internal.run.run`.

    Parameters
    ----------
    args : list[str] | str
        The command to run
    cwd : str | Path, optional
        Working directory for the command
    env : Mapping[str, str], optional
        Environment variables for the command
    check_returncode : bool, default True
        If True, raise :class:`~libvcs.exc.CommandError` on non-zero exit
    callback : AsyncProgressCallbackProtocol, optional
        Async callback to receive stderr output in real-time.
        Signature: ``async def callback(output: str, timestamp: datetime) -> None``
    timeout : float, optional
        Timeout in seconds. Raises :class:`~libvcs.exc.CommandTimeoutError`
        if exceeded.

    Returns
    -------
    str
        Combined stdout output

    Raises
    ------
    libvcs.exc.CommandError
        If check_returncode=True and process exits with non-zero code
    libvcs.exc.CommandTimeoutError
        If timeout is exceeded

    Examples
    --------
    Basic usage:

    >>> async def example():
    ...     output = await async_run(['echo', 'hello'])
    ...     return output.strip()
    >>> asyncio.run(example())
    'hello'

    With progress callback:

    >>> async def progress(output: str, timestamp: datetime.datetime) -> None:
    ...     pass  # Handle progress output
    >>> async def clone_example():
    ...     url = f'file://{create_git_remote_repo()}'
    ...     output = await async_run(['git', 'clone', url, str(tmp_path / 'cb_repo')])
    ...     return 'Cloning' in output or output == ''
    >>> asyncio.run(clone_example())
    True

    See Also
    --------
    libvcs._internal.run.run : Synchronous equivalent
    AsyncSubprocessCommand : Lower-level async subprocess wrapper
    """
    args_list = _args_to_list(args)

    # Create subprocess with pipes (using non-shell exec for security)
    proc = await asyncio.subprocess.create_subprocess_exec(
        *args_list,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    async def _run_with_callback() -> tuple[bytes, bytes, int]:
        """Run subprocess, streaming stderr to callback."""
        stdout_data = b""
        stderr_data = b""

        assert proc.stdout is not None
        assert proc.stderr is not None

        # Read stderr line-by-line for progress callback
        if callback is not None:
            # Stream stderr to callback while collecting stdout
            async def read_stderr() -> bytes:
                collected = b""
                assert proc.stderr is not None
                while True:
                    line = await proc.stderr.readline()
                    if not line:
                        break
                    collected += line
                    # Call progress callback with decoded line
                    await callback(
                        output=console_to_str(line),
                        timestamp=datetime.datetime.now(),
                    )
                return collected

            # Run stdout collection and stderr streaming concurrently
            stdout_task = asyncio.create_task(proc.stdout.read())
            stderr_task = asyncio.create_task(read_stderr())

            stdout_data, stderr_data = await asyncio.gather(stdout_task, stderr_task)

            # Send final carriage return (matching sync behavior)
            await callback(output="\r", timestamp=datetime.datetime.now())
        else:
            # No callback - just collect both streams
            stdout_data, stderr_data = await proc.communicate()

        # Wait for process to complete
        await proc.wait()
        returncode = proc.returncode
        assert returncode is not None

        return stdout_data, stderr_data, returncode

    try:
        if timeout is not None:
            stdout_bytes, stderr_bytes, returncode = await asyncio.wait_for(
                _run_with_callback(),
                timeout=timeout,
            )
        else:
            stdout_bytes, stderr_bytes, returncode = await _run_with_callback()
    except asyncio.TimeoutError:
        # Kill process on timeout
        proc.kill()
        await proc.wait()
        raise exc.CommandTimeoutError(
            output="Command timed out",
            returncode=-1,
            cmd=args_list,
        ) from None

    # Process stdout: strip and join lines (matching sync behavior)
    if stdout_bytes:
        lines = filter(
            None,
            (line.strip() for line in stdout_bytes.splitlines()),
        )
        output = console_to_str(b"\n".join(lines))
    else:
        output = ""

    # On error, use stderr content
    if returncode != 0 and stderr_bytes:
        stderr_lines = filter(
            None,
            (line.strip() for line in stderr_bytes.splitlines()),
        )
        output = console_to_str(b"".join(stderr_lines))

    if returncode != 0 and check_returncode:
        raise exc.CommandError(
            output=output,
            returncode=returncode,
            cmd=args_list,
        )

    return output
