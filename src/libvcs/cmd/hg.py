"""Run hg (Mercurial) commands directly against a local mercurial repo.

.. Note::

   At a Mercurial shop? Can you help us jimmy this module into the next `Sunbeam toaster
   <https://automaticbeyondbelief.org/>`_ of Mercurialian perfection? We need to patch
   and shimmy this thing into shape and seek a skilled tradesperson to give it - in
   Robert M. Pirsig's sense - *care*.  Connect with us `on the tracker
   <https://github.com/vcs-python/libvcs>`_. It's not too late to change the API.
"""
import enum
import pathlib
from collections.abc import Sequence
from typing import Any, Optional, Union

from libvcs._internal.run import ProgressCallbackProtocol, run
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = Union[StrOrBytesPath, Sequence[StrOrBytesPath]]


class HgColorType(enum.Enum):
    """CLI Color enum for Mercurial."""

    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"
    debug = "debug"


class HgPagerType(enum.Enum):
    """CLI Pagination enum for Mercurial."""

    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"


class Hg:
    """Run commands directly on a Mercurial repository."""

    progress_callback: Optional[ProgressCallbackProtocol] = None

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: Optional[ProgressCallbackProtocol] = None,
    ) -> None:
        """Lite, typed, pythonic wrapper for hg(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding hg subcommand.

        Examples
        --------
        >>> Hg(path=tmp_path)
        <Hg path=...>
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.progress_callback = progress_callback

    def __repr__(self) -> str:
        """Representation of Mercurial Repo command object."""
        return f"<Hg path={self.path}>"

    def run(
        self,
        args: _CMD,
        *,
        config: Optional[str] = None,
        repository: Optional[str] = None,
        quiet: Optional[bool] = None,
        _help: Optional[bool] = None,
        encoding: Optional[str] = None,
        encoding_mode: Optional[str] = None,
        verbose: Optional[bool] = None,
        traceback: Optional[bool] = None,
        debug: Optional[bool] = None,
        debugger: Optional[bool] = None,
        profile: Optional[bool] = None,
        version: Optional[bool] = None,
        hidden: Optional[bool] = None,
        time: Optional[bool] = None,
        pager: Optional[HgPagerType] = None,
        color: Optional[HgColorType] = None,
        check_returncode: Optional[bool] = None,
        **kwargs: Any,
    ) -> str:
        """Run a command for this Mercurial repository.

        Passing None to a subcommand option, the flag won't be passed unless otherwise
        stated.

        `hg help` and `hg help [cmd]`

        Wraps hg's `Options <https://www.mercurial-scm.org/doc/hg.1.html>`_.

        Parameters
        ----------
        quiet : bool
            -q / --quiet
        repository : str
            ``--repository REPO``
        cwd : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--cwd DIR``, Defaults to :attr:`~.cwd`
        verbose : bool
            ``-v / --verbose``
        non_interactive : bool
            ``-y / --noninteractive``, defaults to True
        color : HgColorTypeLiteral
            ``--color``
        debug : bool
            ``--debug``
        debugger : bool
            ``--debugger``
        encoding : str
            ``--encoding ENCODE``
        encoding_mode : str
            ``--encodingmode MODE``
        traceback : bool
            ``--traceback``
        time : bool
            ``--time``
        profile : bool
            ``--profile``
        version : bool
            ``--version``
        _help : bool
            ``-h / --help``
        hidden : bool
            ``--hidden``
        pager : HgPagerType
            ``--pager TYPE``
        config :
            ``--config CONFIG [+]``, ``section.name=value``
        check_returncode : bool, default: ``True``
            Passthrough to :func:`libvcs._internal.run.run()`

        Examples
        --------
        >>> hg = Hg(path=tmp_path)
        >>> hg.run(['help'])
        "Mercurial Distributed SCM..."
        """
        cli_args = ["hg", *args] if isinstance(args, Sequence) else ["hg", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.path

        if repository is not None:
            cli_args.extend(["--repository", repository])
        if config is not None:
            cli_args.extend(["--config", config])
        if pager is not None:
            cli_args.append(["--pager", pager])
        if color is not None:
            cli_args.append(["--color", color])
        if verbose is True:
            cli_args.append("--verbose")
        if quiet is True:
            cli_args.append("--quiet")
        if debug is True:
            cli_args.append("--debug")
        if debugger is True:
            cli_args.append("--debugger")
        if traceback is True:
            cli_args.append("--traceback")
        if time is True:
            cli_args.append("--time")
        if profile is True:
            cli_args.append("--profile")
        if version is True:
            cli_args.append("--version")
        if _help is True:
            cli_args.append("--help")

        if self.progress_callback is not None:
            kwargs["callback"] = self.progress_callback

        return run(
            args=cli_args,
            check_returncode=True if check_returncode is None else check_returncode,
            **kwargs,
        )

    def clone(
        self,
        *,
        url: str,
        no_update: Optional[bool] = None,
        update_rev: Optional[str] = None,
        rev: Optional[str] = None,
        branch: Optional[str] = None,
        ssh: Optional[str] = None,
        remote_cmd: Optional[str] = None,
        pull: Optional[bool] = None,
        stream: Optional[bool] = None,
        insecure: Optional[bool] = None,
        quiet: Optional[bool] = None,
        # Special behavior
        make_parents: Optional[bool] = True,
        check_returncode: Optional[bool] = None,
    ) -> str:
        """Clone a working copy from a mercurial repo.

        Wraps `hg clone <https://www.mercurial-scm.org/doc/hg.1.html#clone>`_.

        Parameters
        ----------
        make_parents : bool, default: ``True``
            Creates checkout directory (`:attr:`self.path`) if it doesn't already exist.
        check_returncode : bool, default: ``None``
            Passthrough to :meth:`Hg.run`

        Examples
        --------
        >>> hg = Hg(path=tmp_path)
        >>> hg_remote_repo = create_hg_remote_repo()
        >>> hg.clone(url=f'file://{hg_remote_repo}')
        'updating to branch default...1 files updated, 0 files merged, ...'
        >>> hg.path.exists()
        True
        """
        required_flags: list[str] = [url, str(self.path)]
        local_flags: list[str] = []

        if ssh is not None:
            local_flags.extend(["--ssh", ssh])
        if remote_cmd is not None:
            local_flags.extend(["--remotecmd", remote_cmd])
        if rev is not None:
            local_flags.extend(["--rev", rev])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if no_update is True:
            local_flags.append("--noupdate")
        if pull is True:
            local_flags.append("--pull")
        if stream is True:
            local_flags.append("--stream")
        if insecure is True:
            local_flags.append("--insecure")
        if quiet is True:
            local_flags.append("--quiet")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)
        return self.run(
            ["clone", *local_flags, "--", *required_flags],
            check_returncode=check_returncode,
        )

    def update(
        self,
        quiet: Optional[bool] = None,
        verbose: Optional[bool] = None,
        # libvcs special behavior
        check_returncode: Optional[bool] = True,
        *args: object,
        **kwargs: object,
    ) -> str:
        """Update working directory.

        Wraps `hg update <https://www.mercurial-scm.org/doc/hg.1.html#update>`_.

        Examples
        --------
        >>> hg = Hg(path=tmp_path)
        >>> hg_remote_repo = create_hg_remote_repo()
        >>> hg.clone(url=f'file://{hg_remote_repo}')
        'updating to branch default...1 files updated, 0 files merged, ...'
        >>> hg.update()
        '0 files updated, 0 files merged, 0 files removed, 0 files unresolved'
        """
        local_flags: list[str] = []

        if quiet:
            local_flags.append("--quiet")
        if verbose:
            local_flags.append("--verbose")

        return self.run(["update", *local_flags], check_returncode=check_returncode)

    def pull(
        self,
        quiet: Optional[bool] = None,
        verbose: Optional[bool] = None,
        update: Optional[bool] = None,
        # libvcs special behavior
        check_returncode: Optional[bool] = True,
        *args: object,
        **kwargs: object,
    ) -> str:
        """Update working directory.

        Wraps `hg update <https://www.mercurial-scm.org/doc/hg.1.html#pull>`_.

        Examples
        --------
        >>> hg = Hg(path=tmp_path)
        >>> hg_remote_repo = create_hg_remote_repo()
        >>> hg.clone(url=f'file://{hg_remote_repo}')
        'updating to branch default...1 files updated, 0 files merged, ...'
        >>> hg.pull()
        'pulling from ...searching for changes...no changes found'
        >>> hg.pull(update=True)
        'pulling from ...searching for changes...no changes found'
        """
        local_flags: list[str] = []

        if quiet:
            local_flags.append("--quiet")
        if verbose:
            local_flags.append("--verbose")
        if update:
            local_flags.append("--update")

        return self.run(["pull", *local_flags], check_returncode=check_returncode)
