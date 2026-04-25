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

    timeout_stdout: bytes | None = None
    timeout_stderr: bytes | None = None
    if timeout is None:
        while code is None:
            code = proc.poll()

            if callback and callable(callback) and proc.stderr is not None:
                line = console_to_str(proc.stderr.read(128))
                if line:
                    callback(output=line, timestamp=datetime.datetime.now())
    else:
        code, timeout_stdout, timeout_stderr = _wait_with_deadline(
            proc,
            deadline=time.monotonic() + timeout,
            timeout=timeout,
            callback=callback,
            cmd=_stringify_command(normalized_args),
        )
    if callback and callable(callback):
        callback(output="\r", timestamp=datetime.datetime.now())

    if proc.stdout is not None:
        stdout_lines: list[bytes] = (
            timeout_stdout.split(b"\n")
            if timeout_stdout is not None
            else proc.stdout.readlines()
        )
        lines: t.Iterable[bytes] = filter(
            None,
            (line.strip() for line in stdout_lines),
        )
        all_output = console_to_str(b"\n".join(lines))
    else:
        all_output = ""
    if code and proc.stderr is not None:
        stderr_raw: list[bytes] = (
            timeout_stderr.split(b"\n")
            if timeout_stderr is not None
            else proc.stderr.readlines()
        )
        stderr_lines: t.Iterable[bytes] = filter(
            None,
            (line.strip() for line in stderr_raw),
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
    timeout: float,
    callback: ProgressCallbackProtocol | None,
    cmd: str | list[str],
) -> tuple[int, bytes | None, bytes | None]:
    """Wait for ``proc`` to exit, enforcing a wall-clock deadline.

    Drains both ``stdout`` and ``stderr`` concurrently so a child that fills
    either kernel pipe buffer (~64 KiB on Linux) cannot deadlock waiting for
    libvcs to read its output. Uses :mod:`selectors` to unblock when either
    stream is readable, when the child exits, or when the per-iteration poll
    interval expires -- whichever comes first.

    When the deadline is exceeded the subprocess is reaped and
    :class:`libvcs.exc.CommandTimeoutError` is raised with the bytes captured
    before the timeout. Otherwise the captured stdout/stderr are returned to
    the caller alongside the exit code so they can be reused without re-
    reading the now-drained pipes.

    Returns
    -------
    tuple[int, bytes | None, bytes | None]
        ``(returncode, stdout_bytes, stderr_bytes)``. A byte buffer is
        ``None`` when the corresponding pipe could not be put into non-
        blocking mode (Windows pipes, unusual fd types) -- in that case the
        caller should fall back to reading the pipe directly.

    Notes
    -----
    The progress ``callback`` is invoked for ``stderr`` chunks only,
    matching the legacy non-timeout codepath. ``stdout`` is drained into
    the returned buffer to prevent the child from blocking on a full pipe,
    but its chunks are not forwarded to the callback in real time. Callers
    that want streaming ``stdout`` should redirect it themselves
    (e.g. ``stdout=`` to a file) rather than relying on ``callback``.
    """
    sel = selectors.DefaultSelector()
    buffers: dict[t.IO[bytes], list[bytes]] = {}
    registered: set[t.IO[bytes]] = set()
    fds_to_restore: list[int] = []

    for stream in (proc.stdout, proc.stderr):
        if stream is None:
            continue
        # Non-blocking reads so the selector loop never stalls on a short read
        # and a chatty child cannot fill a pipe buffer and wedge itself.
        try:
            fd = stream.fileno()
            os.set_blocking(fd, False)
        except (OSError, ValueError):
            continue
        sel.register(stream, selectors.EVENT_READ)
        buffers[stream] = []
        registered.add(stream)
        fds_to_restore.append(fd)

    code: int | None = None
    try:
        while True:
            code = proc.poll()
            if code is not None:
                # Final drain: data written between the last ``select()`` wake
                # and the child's exit would otherwise be lost on the early
                # return. Only drain streams we put into non-blocking mode.
                for stream in list(registered):
                    trailing = _drain_stream(stream)
                    if trailing:
                        buffers[stream].append(trailing)
                        if (
                            stream is proc.stderr
                            and callback is not None
                            and callable(callback)
                        ):
                            callback(
                                output=console_to_str(trailing),
                                timestamp=datetime.datetime.now(),
                            )
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "subprocess deadline exceeded after %.3gs",
                    timeout,
                    extra={
                        "vcs_cmd": _format_cmd_for_log(cmd),
                        "vcs_exit_code": proc.returncode,
                    },
                )
                _terminate_process(proc, cmd)
                for stream in list(registered):
                    trailing = _drain_stream(stream)
                    if trailing:
                        buffers[stream].append(trailing)
                stdout_data = _join_buffer(buffers, proc.stdout)
                stderr_data = _join_buffer(buffers, proc.stderr)
                message = console_to_str((stdout_data or b"") + (stderr_data or b""))
                raise exc.CommandTimeoutError(
                    output=message,
                    returncode=proc.returncode,
                    cmd=cmd,
                    timeout=timeout,
                )

            wait = min(_TIMEOUT_POLL_INTERVAL_SECONDS, remaining)
            if not registered:
                # No streams to select on (e.g. ``os.set_blocking`` failed on
                # Windows pipes). Yield the CPU explicitly instead of busy-
                # looping until the deadline or process exit.
                time.sleep(wait)
                continue

            events = sel.select(timeout=wait)
            if not events:
                continue

            for key, _mask in events:
                stream = t.cast("t.IO[bytes]", key.fileobj)
                try:
                    chunk = stream.read(128)
                except (BlockingIOError, OSError):
                    chunk = b""
                if not chunk:
                    # EOF from the child closing the pipe. Stop selecting on
                    # it so the loop doesn't spin on an always-readable fd.
                    sel.unregister(stream)
                    registered.discard(stream)
                    continue
                buffers[stream].append(chunk)
                if (
                    stream is proc.stderr
                    and callback is not None
                    and callable(callback)
                ):
                    callback(
                        output=console_to_str(chunk),
                        timestamp=datetime.datetime.now(),
                    )
    finally:
        # Restore blocking mode so any subsequent read by the caller behaves
        # as expected; ignore failures (fd already closed, Windows pipe).
        for fd in fds_to_restore:
            with contextlib.suppress(OSError, ValueError):
                os.set_blocking(fd, True)
        sel.close()

    return code, _join_buffer(buffers, proc.stdout), _join_buffer(buffers, proc.stderr)


def _join_buffer(
    buffers: dict[t.IO[bytes], list[bytes]],
    stream: t.IO[bytes] | None,
) -> bytes | None:
    """Concatenate captured chunks for ``stream``, or ``None`` if not tracked."""
    if stream is None or stream not in buffers:
        return None
    return b"".join(buffers[stream])


def _terminate_process(proc: subprocess.Popen[bytes], cmd: str | list[str]) -> None:
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
        logger.debug(
            "subprocess sigkill escalated after sigterm grace expired",
            extra={"vcs_cmd": _format_cmd_for_log(cmd)},
        )
        with contextlib.suppress(OSError, ProcessLookupError):
            proc.kill()
        # If the child is still unreachable after SIGKILL, bail rather than
        # block forever -- we've already signalled the user-facing timeout.
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=_TIMEOUT_KILL_GRACE_SECONDS)
        if proc.poll() is None:
            logger.warning(
                "subprocess sigkill did not reap; child may be leaked",
                extra={"vcs_cmd": _format_cmd_for_log(cmd)},
            )


def _format_cmd_for_log(cmd: str | list[str]) -> str:
    """Render ``cmd`` as a flat string for the ``vcs_cmd`` log extra."""
    if isinstance(cmd, list):
        return " ".join(cmd)
    return cmd


def _drain_stream(stream: t.IO[bytes] | None) -> bytes:
    """Best-effort read of any remaining bytes from a subprocess pipe."""
    if stream is None:
        return b""
    try:
        data = stream.read() or b""
    except (BlockingIOError, OSError, ValueError):
        data = b""
    return data
