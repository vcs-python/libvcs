"""Misc. legacy helpers :mod:`subprocess` and finding VCS binaries.

:class:`libvcs._internal.run.run` will be deprecated by
:mod:`libvcs._internal.subprocess`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import contextlib
import datetime
import logging
import os
import selectors
import subprocess
import sys
import time
import typing as t
from collections.abc import Iterable, Mapping, MutableMapping, Sequence

from libvcs import exc
from libvcs._internal.types import StrOrBytesPath

logger = logging.getLogger(__name__)

console_encoding = sys.stdout.encoding


def console_to_str(s: bytes) -> str:
    """From pypa/pip project, pip.backwardwardcompat. License MIT."""
    try:
        return s.decode(console_encoding)
    except UnicodeDecodeError:
        return s.decode("utf_8")
    except AttributeError:  # for tests, #13
        return str(s)


if t.TYPE_CHECKING:
    _LoggerAdapter = logging.LoggerAdapter[logging.Logger]
else:
    _LoggerAdapter = logging.LoggerAdapter


class CmdLoggingAdapter(_LoggerAdapter):
    """Adapter for additional command-related data to :py:mod:`logging`.

    Extends :py:class:`logging.LoggerAdapter`'s functionality.

    Mixes in additional context via :py:meth:`logging.LoggerAdapter.process()` for
    :class:`logging.Formatter` when emitting log entries.

    Parameters
    ----------
    bin_name : str
        name of the command or vcs tool being wrapped, e.g. 'git'
    keyword : str
        directory basename, name of repo, hint, etc. e.g. 'django'
    """

    def __init__(
        self,
        bin_name: str,
        keyword: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        #: bin_name
        self.bin_name = bin_name
        #: directory basename, name of repository, hint, etc.
        self.keyword = keyword

        logging.LoggerAdapter.__init__(self, *args, **kwargs)

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, t.Any],
    ) -> tuple[t.Any, MutableMapping[str, t.Any]]:
        """Add additional context information for loggers."""
        prefixed_dict = {}
        prefixed_dict["bin_name"] = self.bin_name
        prefixed_dict["keyword"] = self.keyword

        kwargs["extra"] = prefixed_dict

        return msg, kwargs


class ProgressCallbackProtocol(t.Protocol):
    """Callback to report subprocess communication."""

    def __call__(self, output: str, timestamp: datetime.datetime) -> None:
        """Process progress for subprocess communication."""
        ...


if sys.platform == "win32":
    _ENV: t.TypeAlias = Mapping[str, str]
else:
    _ENV: t.TypeAlias = Mapping[bytes, StrOrBytesPath] | Mapping[str, StrOrBytesPath]

_CMD: t.TypeAlias = StrOrBytesPath | Sequence[StrOrBytesPath]
_FILE: t.TypeAlias = int | t.IO[t.Any] | None


def _normalize_command_args(args: _CMD) -> list[StrOrBytesPath]:
    """Return subprocess arguments without splitting scalar strings or bytes."""
    if isinstance(args, (str, bytes, os.PathLike)):
        return [os.fspath(args)]

    return [os.fspath(arg) for arg in args]


def _stringify_command(args: _CMD) -> str | list[str]:
    """Return a human-readable command for CommandError."""
    if isinstance(args, (str, bytes, os.PathLike)):
        return os.fsdecode(args)

    return [os.fsdecode(arg) for arg in args]


def run(
    args: _CMD,
    bufsize: int = -1,
    executable: StrOrBytesPath | None = None,
    stdin: _FILE | None = None,
    stdout: _FILE | None = None,
    stderr: _FILE | None = None,
    preexec_fn: t.Callable[[], t.Any] | None = None,
    close_fds: bool = True,
    shell: bool = False,
    cwd: StrOrBytesPath | None = None,
    env: _ENV | None = None,
    startupinfo: t.Any | None = None,
    creationflags: int = 0,
    restore_signals: bool = True,
    start_new_session: bool = False,
    pass_fds: t.Any = (),
    *,
    encoding: str | None = None,
    errors: str | None = None,
    user: str | int | None = None,
    group: str | int | None = None,
    extra_groups: Iterable[str | int] | None = None,
    umask: int = -1,
    log_in_real_time: bool = False,
    check_returncode: bool = True,
    callback: ProgressCallbackProtocol | None = None,
    timeout: float | None = None,
) -> str:
    """Run a command.

    Run 'args' in a shell and return the combined contents of stdout and
    stderr (Blocking). Throws an exception if the command exits non-zero.

    Keyword arguments are passthrough to :class:`subprocess.Popen`.

    Parameters
    ----------
    args : list or str, or single str, if shell=True
       the command to run

    shell : bool
        boolean indicating whether we are using advanced shell
        features. Use only when absolutely necessary, since this allows a lot
        more freedom which could be exploited by malicious code. See the
        warning here: http://docs.python.org/library/subprocess.html#popen-constructor

    cwd : str
        dir command is run from. Defaults to ``path``.

    log_in_real_time : bool
        boolean indicating whether to read stdout from the
        subprocess in real time instead of when the process finishes.

    check_returncode : bool
        Indicate whether a ``libvcs.exc.CommandError`` should be raised if return
        code is different from 0.

    callback : ProgressCallbackProtocol
        callback to return output as a command executes, accepts a function signature
        of ``(output, timestamp)``. Example usage::

            def progress_cb(output, timestamp):
                sys.stdout.write(output)
                sys.stdout.flush()
            run(['git', 'pull'], callback=progress_cb)

    timeout : float, optional
        Seconds to wait before terminating the subprocess. When the deadline is
        exceeded the process is sent ``SIGTERM`` (then ``SIGKILL`` after a short
        grace period) and :class:`libvcs.exc.CommandTimeoutError` is raised with
        any output collected so far. ``None`` (default) disables the deadline and
        preserves the legacy behaviour of blocking until the process exits.

    Upcoming changes
    ----------------
    When minimum python >= 3.10, pipesize: int = -1 will be added after umask.
    """
    normalized_args: _CMD
    if shell:
        normalized_args = os.fspath(args) if isinstance(args, os.PathLike) else args
    else:
        normalized_args = _normalize_command_args(args)

    proc = subprocess.Popen(
        normalized_args,
        bufsize=bufsize,
        executable=executable,
        stdin=stdin,
        stdout=stdout or subprocess.PIPE,
        stderr=stderr or subprocess.PIPE,
        preexec_fn=preexec_fn,
        close_fds=close_fds,
        shell=shell,
        cwd=cwd,
        env=env,
        startupinfo=startupinfo,
        creationflags=creationflags,
        restore_signals=restore_signals,
        start_new_session=start_new_session,
        pass_fds=pass_fds,
        text=False,  # Keep in bytes mode to preserve \r properly
        encoding=encoding,
        errors=errors,
        user=user,
        group=group,
        extra_groups=extra_groups,
        umask=umask,
    )

    all_output: str = ""
    code = None
    line = None
    if log_in_real_time and callback is None:

        def progress_cb(output: t.AnyStr, timestamp: datetime.datetime) -> None:
            sys.stdout.write(str(output))
            sys.stdout.flush()

        callback = progress_cb

    # Note: When git detects that stderr is not a TTY (e.g., when piped),
    # it outputs progress with newlines instead of carriage returns.
    # This causes each progress update to appear on a new line.
    # To get proper single-line progress updates, git would need to be
    # connected to a pseudo-TTY, which would require significant changes
    # to how subprocess execution is handled.

    if timeout is None:
        while code is None:
            code = proc.poll()

            if callback and callable(callback) and proc.stderr is not None:
                line = console_to_str(proc.stderr.read(128))
                if line:
                    callback(output=line, timestamp=datetime.datetime.now())
    else:
        code = _wait_with_deadline(
            proc,
            deadline=time.monotonic() + timeout,
            callback=callback,
            cmd=_stringify_command(normalized_args),
        )
    if callback and callable(callback):
        callback(output="\r", timestamp=datetime.datetime.now())

    if proc.stdout is not None:
        lines: t.Iterable[bytes] = filter(
            None,
            (line.strip() for line in proc.stdout.readlines()),
        )
        all_output = console_to_str(b"\n".join(lines))
    else:
        all_output = ""
    if code and proc.stderr is not None:
        stderr_lines: t.Iterable[bytes] = filter(
            None,
            (line.strip() for line in proc.stderr.readlines()),
        )
        all_output = console_to_str(b"".join(stderr_lines))
    output = "".join(all_output)
    if code != 0 and check_returncode:
        raise exc.CommandError(
            output=output,
            returncode=code,
            cmd=_stringify_command(normalized_args),
        )
    return output


#: Grace period after ``terminate()`` before escalating to ``kill()``.
_TIMEOUT_KILL_GRACE_SECONDS = 0.5

#: Upper bound on the ``selectors.select()`` wait inside the deadline loop.
_TIMEOUT_POLL_INTERVAL_SECONDS = 0.1


def _wait_with_deadline(
    proc: subprocess.Popen[bytes],
    *,
    deadline: float,
    callback: ProgressCallbackProtocol | None,
    cmd: str | list[str],
) -> int:
    """Wait for ``proc`` to exit, enforcing a wall-clock deadline.

    Uses :mod:`selectors` so the wait unblocks when stderr is readable, when the
    child exits, or when the per-iteration poll interval expires -- whichever
    comes first. When the deadline is exceeded, the subprocess is reaped and
    :class:`libvcs.exc.CommandTimeoutError` is raised with whatever output was
    collected before the timeout.
    """
    sel = selectors.DefaultSelector()
    stderr_stream = proc.stderr
    if stderr_stream is not None:
        # Non-blocking reads so the selector loop never stalls on a short read
        # from a stuck child (e.g. git waiting on network or credentials).
        try:
            os.set_blocking(stderr_stream.fileno(), False)
        except (OSError, ValueError):
            stderr_stream = None
        else:
            sel.register(stderr_stream, selectors.EVENT_READ)

    partial_chunks: list[bytes] = []
    try:
        while True:
            code = proc.poll()
            if code is not None:
                return code

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_process(proc)
                drained = _drain_stream(stderr_stream) + _drain_stream(proc.stdout)
                message = console_to_str(b"".join(partial_chunks) + drained)
                raise exc.CommandTimeoutError(
                    output=message,
                    returncode=proc.returncode,
                    cmd=cmd,
                )

            wait = min(_TIMEOUT_POLL_INTERVAL_SECONDS, remaining)
            events = sel.select(timeout=wait) if stderr_stream is not None else ()
            if not events:
                continue

            for key, _mask in events:
                if key.fileobj is not stderr_stream:
                    continue
                try:
                    chunk = stderr_stream.read(128)
                except (BlockingIOError, OSError):
                    chunk = b""
                if not chunk:
                    continue
                partial_chunks.append(chunk)
                if callback is not None and callable(callback):
                    callback(
                        output=console_to_str(chunk),
                        timestamp=datetime.datetime.now(),
                    )
    finally:
        sel.close()


def _terminate_process(proc: subprocess.Popen[bytes]) -> None:
    """Terminate ``proc`` gracefully, falling back to ``kill`` on the grace."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except (OSError, ProcessLookupError):
        return
    try:
        proc.wait(timeout=_TIMEOUT_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError, ProcessLookupError):
            proc.kill()
        # If the child is still unreachable after SIGKILL, bail rather than
        # block forever -- we've already signalled the user-facing timeout.
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=_TIMEOUT_KILL_GRACE_SECONDS)


def _drain_stream(stream: t.IO[bytes] | None) -> bytes:
    """Best-effort read of any remaining bytes from a subprocess pipe."""
    if stream is None:
        return b""
    try:
        data = stream.read() or b""
    except (BlockingIOError, OSError, ValueError):
        data = b""
    return data
