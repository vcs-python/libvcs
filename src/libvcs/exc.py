"""Exceptions for libvcs."""

from __future__ import annotations


class LibVCSException(Exception):
    """Standard exception raised by libvcs."""


class CommandError(LibVCSException):
    """Raised on non-zero return codes."""

    def __init__(
        self,
        output: str,
        returncode: int | None = None,
        cmd: str | list[str] | None = None,
    ) -> None:
        self.returncode = returncode
        self.output = output
        if cmd:
            if isinstance(cmd, list):
                cmd = " ".join(cmd)
            self.cmd = cmd

    def __str__(self) -> str:
        """Return command output."""
        message = self.message.format(returncode=self.returncode, cmd=self.cmd)
        if len(self.output.strip()):
            message += f"\n{self.output}"
        return message

    message = "Command failed with code {returncode}: {cmd}"


class CommandTimeoutError(CommandError):
    r"""CommandError raised when a subprocess exceeds its wall-clock timeout.

    Carries the deadline used when the timeout fired so callers and human
    readers see the duration in the rendered message rather than the
    misleading ``"Command failed with code None: ..."`` produced by the
    bare :class:`CommandError` template (the child is not necessarily reaped
    before the exception is raised, leaving ``returncode`` ``None``).

    Examples
    --------
    >>> err = CommandTimeoutError(
    ...     output='partial output',
    ...     cmd='git fetch',
    ...     timeout=2.5,
    ... )
    >>> print(str(err))
    Command timed out after 2.5s: git fetch
    partial output
    """

    def __init__(
        self,
        output: str,
        returncode: int | None = None,
        cmd: str | list[str] | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(output=output, returncode=returncode, cmd=cmd)
        #: Wall-clock deadline (seconds) the subprocess exceeded, if known.
        self.timeout = timeout

    def __str__(self) -> str:
        """Render the timeout duration alongside the command and partial output."""
        cmd = getattr(self, "cmd", "")
        if self.timeout is not None:
            message = f"Command timed out after {self.timeout:g}s: {cmd}"
        else:
            message = f"Command timed out: {cmd}"
        if self.output.strip():
            message += f"\n{self.output}"
        return message


class InvalidVCS(LibVCSException):
    """Invalid VCS."""
