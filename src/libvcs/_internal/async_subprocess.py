# ruff: noqa: A002
r"""Async invocable :mod:`subprocess` wrapper.

Async equivalent of :mod:`libvcs._internal.subprocess`.

Note
----
This is an internal API not covered by versioning policy.

Examples
--------
- :class:`~AsyncSubprocessCommand`: Async wrapper for subprocess execution.

  Before (sync):

  >>> import subprocess
  >>> subprocess.run(
  ...    ['echo', 'hi'],
  ...    capture_output=True, text=True
  ... ).stdout
  'hi\n'

  With this (async):

  >>> async def example():
  ...     cmd = AsyncSubprocessCommand(['echo', 'hi'])
  ...     result = await cmd.run()
  ...     return result.stdout
  >>> asyncio.run(example())
  b'hi\n'
"""

from __future__ import annotations

import asyncio
import asyncio.subprocess
import dataclasses
import subprocess
import typing as t
from collections.abc import Mapping, Sequence

from libvcs._internal.types import StrOrBytesPath

from .dataclasses import SkipDefaultFieldsReprMixin

#: Command type alias
_CMD: t.TypeAlias = StrOrBytesPath | Sequence[StrOrBytesPath]

#: Environment type alias
_ENV: t.TypeAlias = Mapping[str, str]


@dataclasses.dataclass
class AsyncCompletedProcess(t.Generic[t.AnyStr]):
    """Result of an async subprocess execution.

    Mirrors :class:`subprocess.CompletedProcess` for async context.

    Parameters
    ----------
    args : list[str]
        The command arguments
    returncode : int
        Exit code of the process
    stdout : str | bytes | None
        Captured stdout, if any
    stderr : str | bytes | None
        Captured stderr, if any
    """

    args: list[str]
    returncode: int
    stdout: t.AnyStr | None = None
    stderr: t.AnyStr | None = None

    def check_returncode(self) -> None:
        """Raise CalledProcessError if returncode is non-zero.

        Raises
        ------
        subprocess.CalledProcessError
            If the process exited with a non-zero code
        """
        if self.returncode != 0:
            raise subprocess.CalledProcessError(
                self.returncode,
                self.args,
                self.stdout,
                self.stderr,
            )


@dataclasses.dataclass(repr=False)
class AsyncSubprocessCommand(SkipDefaultFieldsReprMixin):
    r"""Async subprocess command wrapper.

    Wraps asyncio subprocess execution in a dataclass for inspection
    and mutation before invocation.

    Parameters
    ----------
    args : list[str]
        Command and arguments to run
    cwd : str | Path, optional
        Working directory for the command
    env : dict[str, str], optional
        Environment variables for the command

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     cmd = AsyncSubprocessCommand(['echo', 'hello'])
    ...     result = await cmd.run()
    ...     return result.stdout
    >>> asyncio.run(example())
    b'hello\n'

    Modify before running:

    >>> cmd = AsyncSubprocessCommand(['echo', 'hi'])
    >>> cmd.args
    ['echo', 'hi']
    >>> cmd.args[1] = 'hello'
    >>> cmd.args
    ['echo', 'hello']
    """

    args: _CMD
    cwd: StrOrBytesPath | None = None
    env: _ENV | None = None

    # Limits for stdout/stderr
    limit: int = 2**16  # 64 KiB default buffer

    def _args_as_list(self) -> list[str]:
        """Convert args to list of strings for asyncio."""
        from os import PathLike

        args = self.args
        if isinstance(args, (str, bytes, PathLike)):
            # Single command (str, bytes, or PathLike)
            return [str(args) if not isinstance(args, bytes) else args.decode()]
        # At this point, args is Sequence[StrOrBytesPath]
        return [
            str(arg) if not isinstance(arg, bytes) else arg.decode() for arg in args
        ]

    async def _create_process(
        self,
        *,
        stdin: int | None = None,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> asyncio.subprocess.Process:
        """Create an async subprocess.

        Uses asyncio.create_subprocess_exec for secure, non-shell execution.
        """
        args_list = self._args_as_list()
        # Use asyncio's subprocess creation (non-shell variant for security)
        return await asyncio.subprocess.create_subprocess_exec(
            *args_list,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            cwd=self.cwd,
            env=self.env,
            limit=self.limit,
        )

    @t.overload
    async def run(
        self,
        *,
        check: bool = ...,
        timeout: float | None = ...,
        input: bytes | None = ...,
        text: t.Literal[False] = ...,
    ) -> AsyncCompletedProcess[bytes]: ...

    @t.overload
    async def run(
        self,
        *,
        check: bool = ...,
        timeout: float | None = ...,
        input: str | None = ...,
        text: t.Literal[True],
    ) -> AsyncCompletedProcess[str]: ...

    @t.overload
    async def run(
        self,
        *,
        check: bool = ...,
        timeout: float | None = ...,
        input: str | bytes | None = ...,
        text: bool = ...,
    ) -> AsyncCompletedProcess[t.Any]: ...

    async def run(
        self,
        *,
        check: bool = False,
        timeout: float | None = None,
        input: str | bytes | None = None,
        text: bool = False,
    ) -> AsyncCompletedProcess[t.Any]:
        r"""Run command asynchronously and return completed process.

        Uses asyncio subprocess APIs for non-blocking operation.

        Parameters
        ----------
        check : bool, default False
            If True, raise CalledProcessError on non-zero exit
        timeout : float, optional
            Timeout in seconds. Raises asyncio.TimeoutError if exceeded.
        input : str | bytes, optional
            Data to send to stdin
        text : bool, default False
            If True, decode stdout/stderr as text

        Returns
        -------
        AsyncCompletedProcess
            Result with args, returncode, stdout, stderr

        Raises
        ------
        subprocess.CalledProcessError
            If check=True and process exits with non-zero code
        asyncio.TimeoutError
            If timeout is exceeded

        Examples
        --------
        >>> import asyncio
        >>> async def example():
        ...     cmd = AsyncSubprocessCommand(['echo', 'hello'])
        ...     result = await cmd.run(text=True)
        ...     return result.stdout.strip()
        >>> asyncio.run(example())
        'hello'
        """
        args_list = self._args_as_list()

        # Prepare input as bytes
        input_bytes: bytes | None = None
        if input is not None:
            input_bytes = input.encode() if isinstance(input, str) else input

        # Create subprocess
        proc = await self._create_process(
            stdin=asyncio.subprocess.PIPE if input_bytes else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Use communicate() with optional timeout via wait_for
            if timeout is not None:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input_bytes),
                    timeout=timeout,
                )
            else:
                stdout_bytes, stderr_bytes = await proc.communicate(input_bytes)
        except asyncio.TimeoutError:
            # Kill process on timeout
            proc.kill()
            await proc.wait()
            raise

        # Get return code (should be set after communicate)
        returncode = proc.returncode
        assert returncode is not None, "returncode should be set after communicate()"

        # Decode if text mode
        stdout: str | bytes | None = stdout_bytes
        stderr: str | bytes | None = stderr_bytes
        if text:
            stdout = stdout_bytes.decode() if stdout_bytes else ""
            stderr = stderr_bytes.decode() if stderr_bytes else ""

        result: AsyncCompletedProcess[t.Any] = AsyncCompletedProcess(
            args=args_list,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

        if check:
            result.check_returncode()

        return result

    async def check_output(
        self,
        *,
        timeout: float | None = None,
        input: str | bytes | None = None,
        text: bool = False,
    ) -> str | bytes:
        r"""Run command and return stdout, raising on non-zero exit.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds
        input : str | bytes, optional
            Data to send to stdin
        text : bool, default False
            If True, return stdout as text

        Returns
        -------
        str | bytes
            Command stdout

        Raises
        ------
        subprocess.CalledProcessError
            If process exits with non-zero code
        asyncio.TimeoutError
            If timeout is exceeded

        Examples
        --------
        >>> import asyncio
        >>> async def example():
        ...     cmd = AsyncSubprocessCommand(['echo', 'hello'])
        ...     return await cmd.check_output(text=True)
        >>> asyncio.run(example())
        'hello\n'
        """
        result = await self.run(check=True, timeout=timeout, input=input, text=text)
        return result.stdout if result.stdout is not None else (b"" if not text else "")

    async def wait(
        self,
        *,
        timeout: float | None = None,
    ) -> int:
        """Run command and return exit code.

        Discards stdout/stderr.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        int
            Process exit code

        Raises
        ------
        asyncio.TimeoutError
            If timeout is exceeded

        Examples
        --------
        >>> import asyncio
        >>> async def example():
        ...     cmd = AsyncSubprocessCommand(['true'])
        ...     return await cmd.wait()
        >>> asyncio.run(example())
        0
        """
        proc = await self._create_process(
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            if timeout is not None:
                returncode = await asyncio.wait_for(
                    proc.wait(),
                    timeout=timeout,
                )
            else:
                returncode = await proc.wait()
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        return returncode
