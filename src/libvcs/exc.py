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
    """CommandError which gets raised when a subprocess exceeds its timeout."""


class InvalidVCS(LibVCSException):
    """Invalid VCS."""
