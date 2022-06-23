"""Exceptions for libvcs.

If you see this, we're publishing to S3 automatically

"""


class LibVCSException(Exception):
    """Standard exception raised by libvcs."""


class CommandError(LibVCSException):
    """This exception is raised on non-zero return codes."""

    def __init__(self, output, returncode=None, cmd=None):
        self.returncode = returncode
        self.output = output
        if cmd:
            if isinstance(cmd, list):
                cmd = " ".join(cmd)
            self.cmd = cmd

    def __str__(self):
        message = self.message.format(returncode=self.returncode, cmd=self.cmd)
        if len(self.output.strip()):
            message += "\n%s" % self.output
        return message

    message = "Command failed with code {returncode}: {cmd}"


class CommandTimeoutError(CommandError):
    """CommandError which gets raised when a subprocess exceeds its timeout."""


class InvalidVCS(LibVCSException):
    """Invalid VCS."""
