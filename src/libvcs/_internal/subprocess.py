r"""Invocable :mod:`subprocess` wrapper.

Defer running a subprocess, such as by handing to an executor.

Note
----
This is an internal API not covered by versioning policy.

Examples
--------
- :class:`~SubprocessCommand`: Wraps :class:`subprocess.Popen` and
  :func:`subprocess.run` in a :func:`~dataclasses.dataclass`.

  Before:

  >>> import subprocess
  >>> subprocess.run(
  ...    ['echo', 'hi'],
  ...    capture_output=True, universal_newlines=True
  ... ).stdout
  'hi\n'

  With this:

  >>> cmd = SubprocessCommand(['echo', 'hi'])
  >>> cmd.args
  ['echo', 'hi']
  >>> cmd.run(capture_output=True, universal_newlines=True).stdout
  'hi\n'

  Tweak params before invocation:

  >>> cmd = SubprocessCommand(['echo', 'hi'])
  >>> cmd.args[1] = 'hello'
  >>> cmd.args
  ['echo', 'hello']
  >>> cmd.run(capture_output=True, universal_newlines=True).stdout
  'hello\n'
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
import typing as t
from collections.abc import Mapping, Sequence

from libvcs._internal.types import StrOrBytesPath

from .dataclasses import SkipDefaultFieldsReprMixin

F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class SubprocessCheckOutputError(Exception):
    def __init__(self, output: str, *args: object) -> None:
        super().__init__(f"output is not str or bytes: {output}")


if sys.platform == "win32":
    _ENV: t.TypeAlias = Mapping[str, str]
else:
    _ENV: t.TypeAlias = Mapping[bytes, StrOrBytesPath] | Mapping[str, StrOrBytesPath]
_FILE: t.TypeAlias = int | t.IO[t.Any] | None
_TXT: t.TypeAlias = bytes | str
#: Command
_CMD: t.TypeAlias = StrOrBytesPath | Sequence[StrOrBytesPath]


@dataclasses.dataclass(repr=False)
class SubprocessCommand(SkipDefaultFieldsReprMixin):
    """Wraps a :mod:`subprocess` request. Inspect, mutate, control before invocation.

    Fields mirror the parameters of :class:`subprocess.Popen`. Each is passed
    through as-is when :meth:`Popen`, :meth:`run`, :meth:`check_call`, or
    :meth:`check_output` fires, and the defaults match the ones
    :mod:`subprocess` uses.

    Attributes
    ----------
    args : _CMD
        Program and its arguments, as a sequence like ``['echo', 'hi']`` or
        as a single string when ``shell`` is set.
    bufsize : int
        Buffering policy for the pipe file objects: ``-1`` for
        :data:`io.DEFAULT_BUFFER_SIZE`, ``0`` for unbuffered, ``1`` for line
        buffered in text mode.
    executable : StrOrBytesPath | None
        Program to execute in place of ``args[0]``, or the shell to use when
        ``shell`` is set. ``None`` runs ``args[0]`` itself.
    stdin : _FILE
        Child's standard input: a file descriptor, a file object,
        :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`, or ``None`` to
        inherit the parent's.
    stdout : _FILE
        Child's standard output, taking the same values as ``stdin``.
    stderr : _FILE
        Child's standard error, taking the same values as ``stdin``, plus
        :data:`subprocess.STDOUT` to fold it into ``stdout``.
    preexec_fn : t.Callable[[], t.Any] | None
        POSIX-only callable run in the child between fork and exec, or
        ``None`` to run nothing.
    close_fds : bool
        Close inherited file descriptors above stderr in the child before
        exec.
    shell : bool
        Run ``args`` through the system shell instead of exec'ing it
        directly.
    cwd : StrOrBytesPath | None
        Directory to change into before running, or ``None`` to inherit the
        parent's working directory.
    env : _ENV | None
        Environment for the child, replacing the parent's, or ``None`` to
        inherit it.
    creationflags : int
        Windows-only process creation flags, e.g.
        :data:`subprocess.CREATE_NEW_CONSOLE`. ``0`` applies none.
    startupinfo : t.Any | None
        Windows-only :class:`subprocess.STARTUPINFO` controlling how the
        child's window appears, or ``None`` for the defaults.
    restore_signals : bool
        POSIX-only: reset signals Python set to ``SIG_IGN`` back to
        ``SIG_DFL`` in the child before exec.
    start_new_session : bool
        POSIX-only: run :func:`os.setsid` in the child, detaching it from the
        parent's process group and controlling terminal.
    pass_fds : t.Any
        POSIX-only file descriptors to keep open in the child regardless of
        ``close_fds``. The empty ``()`` passes none.
    umask : int
        POSIX-only umask to apply in the child before exec. ``-1`` leaves the
        inherited umask alone.
    pipesize : int
        Capacity of the pipes opened for ``stdin``, ``stdout``, and
        ``stderr``. ``-1`` keeps the operating system default.
    user : str | None
        POSIX-only user to switch the child to, or ``None`` to stay as the
        calling user.
    group : str | None
        POSIX-only group to switch the child to, or ``None`` to keep the
        calling group.
    extra_groups : list[str] | None
        POSIX-only supplementary groups for the child, or ``None`` to leave
        them untouched.
    universal_newlines : bool | None
        Alias of ``text``, kept for backwards compatibility. ``None`` leaves
        the mode to the other text options.
    text : t.Literal[True] | None
        Open the pipe file objects in text mode. ``None`` leaves them binary
        unless ``encoding``, ``errors``, or ``universal_newlines`` selects
        text.
    encoding : str | None
        Codec for the text-mode pipe file objects. Setting it turns text mode
        on; ``None`` leaves the choice to the other text options.
    errors : str | None
        Decoding error handler for the text-mode pipe file objects, e.g.
        ``"replace"``. Setting it turns text mode on.

    Examples
    --------
    >>> cmd = SubprocessCommand("ls")
    >>> cmd.args
    'ls'

    With ``shell=True``:

    >>> cmd = SubprocessCommand("ls -l", shell=True)
    >>> cmd.shell
    True
    >>> cmd.args
    'ls -l'
    >>> cmd.check_call()
    0
    """

    args: _CMD
    bufsize: int = -1
    executable: StrOrBytesPath | None = None
    stdin: _FILE = None
    stdout: _FILE = None
    stderr: _FILE = None
    preexec_fn: t.Callable[[], t.Any] | None = None
    close_fds: bool = True
    shell: bool = False
    cwd: StrOrBytesPath | None = None
    env: _ENV | None = None

    # Windows
    creationflags: int = 0
    startupinfo: t.Any | None = None

    # POSIX-only
    restore_signals: bool = True
    start_new_session: bool = False
    pass_fds: t.Any = ()
    umask: int = -1
    pipesize: int = -1
    user: str | None = None
    group: str | None = None
    extra_groups: list[str] | None = None

    # Alias of text, for backwards compatibility
    universal_newlines: bool | None = None
    text: t.Literal[True] | None = None

    # Text mode encoding and error handling to use for file objects
    # stdin, stdout, stderr
    encoding: str | None = None
    errors: str | None = None

    # user, group, extra_groups, umask were added in 3.9
    @t.overload
    def Popen(
        self,
        args: _CMD | None = ...,
        universal_newlines: bool = ...,
        *,
        text: bool | None = ...,
        encoding: str,
        errors: str | None = ...,
    ) -> subprocess.Popen[str]: ...

    @t.overload
    def Popen(
        self,
        args: _CMD | None = ...,
        universal_newlines: bool = ...,
        *,
        text: bool | None = ...,
        encoding: str | None = ...,
        errors: str,
    ) -> subprocess.Popen[str]: ...

    @t.overload
    def Popen(
        self,
        args: _CMD | None = ...,
        *,
        universal_newlines: t.Literal[True],
        # where the *real* keyword only args start
        text: bool | None = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
    ) -> subprocess.Popen[str]: ...

    @t.overload
    def Popen(
        self,
        args: _CMD | None = ...,
        universal_newlines: bool = ...,
        *,
        text: t.Literal[True],
        encoding: str | None = ...,
        errors: str | None = ...,
    ) -> subprocess.Popen[str]: ...

    @t.overload
    def Popen(
        self,
        args: _CMD | None = ...,
        universal_newlines: t.Literal[False] = ...,
        *,
        text: t.Literal[False] | None = ...,
        encoding: None = ...,
        errors: None = ...,
    ) -> subprocess.Popen[bytes]: ...

    def Popen(
        self,
        args: _CMD | None = None,
        universal_newlines: bool | None = None,
        *,
        text: bool | None = None,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs: t.Any,
    ) -> subprocess.Popen[t.Any]:
        r"""Run commands :class:`subprocess.Popen`, optionally overrides via kwargs.

        Parameters
        ----------
        **kwargs : dict, optional
            Overrides existing attributes for :class:`subprocess.Popen`

        Examples
        --------
        >>> cmd = SubprocessCommand(args=['echo', 'hello'])
        >>> proc = cmd.Popen(stdout=subprocess.PIPE)
        >>> proc.communicate()
        (b'hello\n', None)
        """
        return subprocess.Popen(
            **dataclasses.replace(
                self,
                args=args or self.args,
                encoding=encoding,
                errors=errors,
                text=text or None,
                universal_newlines=universal_newlines,
                **kwargs,
            ).__dict__,
        )

    def check_call(self, **kwargs: t.Any) -> int:
        """Run command :func:`subprocess.check_call`, optionally overrides via kwargs.

        Parameters
        ----------
        **kwargs : dict, optional
            Overrides existing attributes for :func:`subprocess.check_call`

        Examples
        --------
        >>> cmd = SubprocessCommand(args=['echo', 'hello'])
        >>> cmd.check_call(stdout=subprocess.PIPE)
        0
        """
        return subprocess.check_call(**dataclasses.replace(self, **kwargs).__dict__)

    @t.overload
    def check_output(
        self,
        universal_newlines: bool = ...,
        *,
        input: str | bytes | None = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        text: t.Literal[True],
        **kwargs: t.Any,
    ) -> str: ...

    @t.overload
    def check_output(
        self,
        universal_newlines: bool | None = ...,
        *,
        input: str | bytes | None = ...,
        encoding: str,
        errors: str | None = ...,
        text: bool | None = ...,
        **kwargs: t.Any,
    ) -> str: ...

    @t.overload
    def check_output(
        self,
        universal_newlines: bool = ...,
        *,
        input: str | bytes | None = ...,
        encoding: str | None = ...,
        errors: str,
        text: bool | None = ...,
        **kwargs: t.Any,
    ) -> str: ...

    @t.overload
    def check_output(
        self,
        universal_newlines: t.Literal[True] = ...,
        *,
        input: str | bytes | None = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        text: bool | None = ...,
        **kwargs: t.Any,
    ) -> str: ...

    @t.overload
    def check_output(
        self,
        universal_newlines: t.Literal[False],
        *,
        input: str | bytes | None = ...,
        encoding: None = ...,
        errors: None = ...,
        text: t.Literal[False] | None = ...,
        **kwargs: t.Any,
    ) -> bytes: ...

    def check_output(
        self,
        universal_newlines: bool | None = None,
        *,
        input: str | bytes | None = None,
        encoding: str | None = None,
        errors: str | None = None,
        text: bool | None = None,
        **kwargs: t.Any,
    ) -> bytes | str:
        r"""Run command :func:`subprocess.check_output`, optionally override via kwargs.

        Parameters
        ----------
        input : t.Union[bytes, str], optional
            pass string to subprocess's stdin. Bytes by default, str in text mode.

            Text mode is triggered by setting any of text, encoding, errors or
            universal_newlines.
        **kwargs : dict, optional
            Overrides existing attributes for :func:`subprocess.check_output`

        Examples
        --------
        >>> cmd = SubprocessCommand(args=['echo', 'hello'])
        >>> proc = cmd.check_output(shell=True)

        Examples from :mod:`subprocess`:

        >>> import subprocess
        >>> cmd = SubprocessCommand(
        ...     ["/bin/sh", "-c", "ls -l non_existent_file ; exit 0"])
        >>> cmd.check_output(stderr=subprocess.STDOUT)
        b"ls: ...non_existent_file...: No such file or directory\n"

        >>> cmd = SubprocessCommand(["sed", "-e", "s/foo/bar/"])
        >>> cmd.check_output(input=b"when in the course of fooman events\n")
        b'when in the course of barman events\n'
        """
        params = dataclasses.replace(self, **kwargs).__dict__
        params.pop("stdout")
        output = subprocess.check_output(input=input, **params)
        if isinstance(output, (bytes, str)):
            return output

        raise SubprocessCheckOutputError(output=output)

    @t.overload
    def run(
        self,
        universal_newlines: bool = ...,
        *,
        capture_output: bool = ...,
        check: bool = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        input: str | None = ...,
        text: t.Literal[True],
    ) -> subprocess.CompletedProcess[str]: ...

    @t.overload
    def run(
        self,
        universal_newlines: bool = ...,
        *,
        capture_output: bool = ...,
        check: bool = ...,
        encoding: str,
        errors: str | None = ...,
        input: str | None = ...,
        text: bool | None = ...,
    ) -> subprocess.CompletedProcess[str]: ...

    @t.overload
    def run(
        self,
        universal_newlines: bool = ...,
        *,
        capture_output: bool = ...,
        check: bool = ...,
        encoding: str | None = ...,
        errors: str,
        input: str | None = ...,
        text: bool | None = ...,
    ) -> subprocess.CompletedProcess[str]: ...

    @t.overload
    def run(
        self,
        *,
        universal_newlines: t.Literal[True],
        # where the *real* keyword only args start
        capture_output: bool = ...,
        check: bool = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        input: str | None = ...,
        text: bool | None = ...,
    ) -> subprocess.CompletedProcess[str]: ...

    @t.overload
    def run(
        self,
        universal_newlines: t.Literal[False] = ...,
        *,
        capture_output: bool = ...,
        check: bool = ...,
        encoding: None = ...,
        errors: None = ...,
        input: bytes | None = ...,
        text: t.Literal[False] | None = ...,
    ) -> subprocess.CompletedProcess[bytes]: ...

    def run(
        self,
        universal_newlines: bool | None = None,
        *,
        capture_output: bool = False,
        check: bool = False,
        encoding: str | None = None,
        errors: str | None = None,
        input: str | bytes | None = None,
        text: bool | None = None,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> subprocess.CompletedProcess[t.Any]:
        r"""Run command in :func:`subprocess.run`, optionally overrides via kwargs.

        Parameters
        ----------
        input : t.Union[bytes, str], optional
            pass string to subprocess's stdin. Bytes by default, str in text mode.

            Text mode is triggered by setting any of text, encoding, errors or
            universal_newlines.

        check : bool
            If True and the exit code was non-zero, it raises a
            :exc:`subprocess.CalledProcessError`. The CalledProcessError object will
            have the return code in the returncode attribute, and output & stderr
            attributes if those streams were captured.

        timeout : int
            If given, and the process takes too long, a :exc:`subprocess.TimeoutExpired`

        **kwargs : dict, optional
            Overrides existing attributes for :func:`subprocess.run`

        Examples
        --------
        >>> import subprocess
        >>> cmd = SubprocessCommand(
        ...     ["/bin/sh", "-c", "ls -l non_existent_file ; exit 0"])
        >>> cmd.run()
        CompletedProcess(args=['/bin/sh', '-c', 'ls -l non_existent_file ; exit 0'],
                         returncode=0)

        >>> import subprocess
        >>> cmd = SubprocessCommand(
        ...     ["/bin/sh", "-c", "ls -l non_existent_file ; exit 0"])
        >>> cmd.run(check=True)
        CompletedProcess(args=['/bin/sh', '-c', 'ls -l non_existent_file ; exit 0'],
                         returncode=0)

        >>> cmd = SubprocessCommand(["sed", "-e", "s/foo/bar/"])
        >>> completed = cmd.run(input=b"when in the course of fooman events\n")
        >>> completed
        CompletedProcess(args=['sed', '-e', 's/foo/bar/'], returncode=0)
        >>> completed.stderr

        >>> cmd = SubprocessCommand(["sed", "-e", "s/foo/bar/"])
        >>> completed = cmd.run(input=b"when in the course of fooman events\n",
        ...                     capture_output=True)
        >>> completed
        CompletedProcess(args=['sed', '-e', 's/foo/bar/'], returncode=0,
                        stdout=b'when in the course of barman events\n', stderr=b'')
        >>> completed.stdout
        b'when in the course of barman events\n'
        >>> completed.stderr
        b''
        """
        return subprocess.run(
            **dataclasses.replace(
                self,
                universal_newlines=universal_newlines,
                errors=errors,
                text=text or None,
                **kwargs,
            ).__dict__,
            check=check,
            capture_output=capture_output,
            input=input,
            timeout=timeout,
        )
