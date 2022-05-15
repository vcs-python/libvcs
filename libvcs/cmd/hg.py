import enum
import pathlib
from typing import Optional, Sequence, Union

from ..types import StrOrBytesPath, StrPath
from libvcs.utils.run import run

_CMD = Union[StrOrBytesPath, Sequence[StrOrBytesPath]]


class HgColorType(enum.Enum):
    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"
    debug = "debug"


class HgPagerType(enum.Enum):
    boolean = "boolean"
    always = "always"
    auto = "auto"
    never = "never"


class Hg:
    def __init__(self, dir: StrPath):
        """Lite, typed, pythonic wrapper for hg(1).

        Parameters
        ----------
        dir :
            Operates as PATH in the corresponding hg subcommand.

        Examples
        --------
        >>> Hg(dir=tmp_path)
        <Hg dir=...>
        """
        #: Directory to check out
        self.dir: pathlib.Path
        if isinstance(dir, pathlib.Path):
            self.dir = dir
        else:
            self.dir = pathlib.Path(dir)

    def __repr__(self):
        return f"<Hg dir={self.dir}>"

    def run(
        self,
        args: _CMD,
        config: Optional[str] = None,
        repository: Optional[str] = None,
        quiet: Optional[bool] = None,
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
        **kwargs,
    ):
        """
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
        cwd : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
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
        help : bool
            ``-h / --help``
        hidden : bool
            ``--hidden``
        pager : HgPagerType
            ``--pager TYPE``
        config :
            ``--config CONFIG [+]``, ``section.name=value``

        Examples
        --------
        >>> hg = Hg(dir=tmp_path)
        >>> hg.run(['help'])
        "Mercurial Distributed SCM..."
        """

        if isinstance(args, Sequence):
            cli_args = ["hg", *args]
        else:
            cli_args = ["hg", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.dir

        if repository is not None:
            cli_args.append(f"--repository {repository}")
        if config is not None:
            cli_args.append("--config {config}")
        if pager is not None:
            cli_args.append(f"--pager {pager}")
        if color is not None:
            cli_args.append(f"--color {color}")
        if verbose is True:
            cli_args.append("verbose")
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
        if help is True:
            cli_args.append("--help")

        return run(cmd=cli_args, **kwargs)

    def clone(
        self,
        url: str,
        no_update: Optional[str] = None,
        update_rev: Optional[str] = None,
        rev: Optional[str] = None,
        branch: Optional[str] = None,
        ssh: Optional[str] = None,
        remote_cmd: Optional[str] = None,
        pull: Optional[bool] = None,
        stream: Optional[bool] = None,
        insecure: Optional[bool] = None,
    ):
        """Clone a working copy from a mercurial repo.

        Wraps `hg clone <https://www.mercurial-scm.org/doc/hg.1.html#clone>`_.

        Examples
        --------
        >>> hg = Hg(dir=tmp_path)
        >>> hg_remote_repo = create_hg_remote_repo()
        >>> hg.clone(url=f'file://{hg_remote_repo}')
        'updating to branch default...1 files updated, 0 files merged, ...'
        >>> hg.dir.exists()
        True
        """
        required_flags: list[str] = [url, str(self.dir)]
        local_flags: list[str] = []

        if ssh is not None:
            local_flags.append(f"--ssh {ssh}")
        if remote_cmd is not None:
            local_flags.append(f"--remotecmd {remote_cmd}")
        if rev is not None:
            local_flags.append(f"--rev {rev}")
        if branch is not None:
            local_flags.append(f"--branch {branch}")
        if no_update is True:
            local_flags.append("--noupdate")
        if pull is True:
            local_flags.append("--pull")
        if stream is True:
            local_flags.append("--stream")
        if insecure is True:
            local_flags.append("--insecure")
        return self.run(
            ["clone", *local_flags, "--", *required_flags], check_returncode=False
        )
