"""Misc. legacy helpers :mod:`subprocess` and finding VCS binaries.

:class:`libvcs._internal.run.run` will be deprecated by
:mod:`libvcs._internal.subprocess`.

Note
----
This is an internal API not covered by versioning policy.
"""
import datetime
import errno
import logging
import os
import subprocess
import sys
from typing import (
    IO,
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Union,
)

from typing_extensions import TypeAlias

from .. import exc
from ..types import StrOrBytesPath

logger = logging.getLogger(__name__)

console_encoding = sys.__stdout__.encoding


def console_to_str(s):
    """From pypa/pip project, pip.backwardwardcompat. License MIT."""
    try:
        return s.decode(console_encoding)
    except UnicodeDecodeError:
        return s.decode("utf_8")
    except AttributeError:  # for tests, #13
        return s


def which(
    exe=None, default_paths=["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin"]
):
    """Return path of bin. Python clone of /usr/bin/which.

    from salt.util - https://www.github.com/saltstack/salt - license apache

    Parameters
    ----------
    exe : str
        Application to search PATHs for.
    default_path : list
        Application to search PATHs for.

    Returns
    -------
    str :
        Path to binary
    """

    def _is_executable_file_or_link(exe):
        # check for os.X_OK doesn't suffice because directory may executable
        return os.access(exe, os.X_OK) and (os.path.isfile(exe) or os.path.islink(exe))

    if _is_executable_file_or_link(exe):
        # executable in cwd or fullpath
        return exe

    # Enhance POSIX path for the reliability at some environments, when
    # $PATH is changing. This also keeps order, where 'first came, first
    # win' for cases to find optional alternatives
    search_path = (
        os.environ.get("PATH") and os.environ["PATH"].split(os.pathsep) or list()
    )
    for default_path in default_paths:
        if default_path not in search_path:
            search_path.append(default_path)
    os.environ["PATH"] = os.pathsep.join(search_path)
    for path in search_path:
        full_path = os.path.join(path, exe)
        if _is_executable_file_or_link(full_path):
            return full_path
    logger.info(
        "'{}' could not be found in the following search path: "
        "'{}'".format(exe, search_path)
    )

    return None


def mkdir_p(path):
    """Make directories recursively.

    Parameters
    ----------
    path : str
        path to create
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise Exception("Could not create directory %s" % path)


class CmdLoggingAdapter(logging.LoggerAdapter):
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

    def __init__(self, bin_name: str, keyword: str, *args, **kwargs):
        #: bin_name
        self.bin_name = bin_name
        #: directory basename, name of repository, hint, etc.
        self.keyword = keyword

        logging.LoggerAdapter.__init__(self, *args, **kwargs)

    def process(self, msg, kwargs):
        """Add additional context information for loggers."""
        prefixed_dict = {}
        prefixed_dict["bin_name"] = self.bin_name
        prefixed_dict["keyword"] = self.keyword

        kwargs["extra"] = prefixed_dict

        return msg, kwargs


class ProgressCallbackProtocol(Protocol):
    """Callback to report subprocess communication."""

    def __call__(self, output: Union[str, bytes], timestamp: datetime.datetime):
        """Callback signature for subprocess communication."""
        ...


if sys.platform == "win32":
    _ENV: TypeAlias = Mapping[str, str]
else:
    _ENV: TypeAlias = Union[
        Mapping[bytes, StrOrBytesPath], Mapping[str, StrOrBytesPath]
    ]

_CMD = Union[StrOrBytesPath, Sequence[StrOrBytesPath]]
_FILE: TypeAlias = Optional[Union[int, IO[Any]]]


def run(
    args: _CMD,
    bufsize: int = -1,
    executable: Optional[StrOrBytesPath] = None,
    stdin: Optional[_FILE] = None,
    stdout: Optional[_FILE] = None,
    stderr: Optional[_FILE] = None,
    preexec_fn: Optional[Callable[[], Any]] = None,
    close_fds: bool = True,
    shell: bool = False,
    cwd: Optional[StrOrBytesPath] = None,
    env: Optional[_ENV] = None,
    universal_newlines: Optional[bool] = None,
    startupinfo: Optional[Any] = None,
    creationflags: int = 0,
    restore_signals: bool = True,
    start_new_session: bool = False,
    pass_fds: Any = (),
    *,
    text: Optional[bool] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    user: Optional[Union[str, int]] = None,
    group: Optional[Union[str, int]] = None,
    extra_groups: Optional[Iterable[Union[str, int]]] = None,
    umask: int = -1,
    # Not until sys.version_info >= (3, 10)
    # pipesize: int = -1,
    # custom
    log_in_real_time: bool = True,
    check_returncode: bool = True,
    callback: Optional[ProgressCallbackProtocol] = None,
):
    """Run 'args' in a shell and return the combined contents of stdout and
    stderr (Blocking). Throws an exception if the command exits non-zero.

    Keyword arguments are passthrough to {class}`subprocess.Popen`.

    Parameters
    ----------
    args : list or str, or single str, if shell=True
       the command to run

    shell : boolean
        boolean indicating whether we are using advanced shell
        features. Use only when absolutely necessary, since this allows a lot
        more freedom which could be exploited by malicious code. See the
        warning here: http://docs.python.org/library/subprocess.html#popen-constructor

    cwd : str
        dir command is run from. Defaults to ``path``.

    log_in_real_time : boolean
        boolean indicating whether to read stdout from the
        subprocess in real time instead of when the process finishes.

    check_returncode : bool
        Indicate whether a `libvcs.exc.CommandError` should be raised if return code is
        different from 0.

    callback : ProgressCallbackProtocol
        callback to return output as a command executes, accepts a function signature
        of `(output, timestamp)`. Example usage::

            def progress_cb(output, timestamp):
                sys.stdout.write(output)
                sys.stdout.flush()
            run(['git', 'pull'], callback=progress_cb)
    """
    proc = subprocess.Popen(
        args,
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
        universal_newlines=universal_newlines,
        startupinfo=startupinfo,
        creationflags=creationflags,
        restore_signals=restore_signals,
        start_new_session=start_new_session,
        pass_fds=pass_fds,
        text=text,
        encoding=encoding,
        errors=errors,
        user=user,
        group=group,
        extra_groups=extra_groups,
        umask=umask,
    )

    all_output = []
    code = None
    line = None
    while code is None:
        code = proc.poll()

        # output = console_to_str(proc.stdout.readline())
        # all_output.append(output)
        if callback and callable(callback):
            line = console_to_str(proc.stderr.read(128))
            if line:
                callback(output=line, timestamp=datetime.datetime.now())
    if callback and callable(callback):
        callback(output="\r", timestamp=datetime.datetime.now())

    lines = filter(None, (line.strip() for line in proc.stdout.readlines()))
    all_output = console_to_str(b"\n".join(lines))
    if code:
        stderr_lines = filter(None, (line.strip() for line in proc.stderr.readlines()))
        all_output = console_to_str(b"".join(stderr_lines))
    output = "".join(all_output)
    if code != 0 and check_returncode:
        raise exc.CommandError(output=output, returncode=code, cmd=args)
    return output
