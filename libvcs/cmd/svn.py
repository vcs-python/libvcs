import pathlib
from typing import Literal, Optional, Sequence, Union

from ..types import StrOrBytesPath, StrOrPath
from .core import run

_CMD = Union[StrOrBytesPath, Sequence[StrOrBytesPath]]

DepthLiteral = Union[Literal["infinity", "empty", "files", "immediates"], None]
RevisionLiteral = Union[Literal["HEAD", "BASE", "COMMITTED", "PREV"], None]


class Svn:
    def __init__(self, dir: StrOrPath):
        """Lite, typed, pythonic wrapper for svn(1).

        Parameters
        ----------
        dir :
            Operates as PATH in the corresonding svn subcommand.

        Examples
        --------
        >>> Svn(dir=tmp_path)
        <Svn dir=...>
        """
        #: Directory to check out
        self.dir: pathlib.Path
        if isinstance(dir, pathlib.Path):
            self.dir = dir
        else:
            self.dir = pathlib.Path(dir)

    def __repr__(self):
        return f"<Svn dir={self.dir}>"

    def run(
        self,
        args: _CMD,
        quiet: Optional[bool] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        no_auth_cache: Optional[bool] = None,
        non_interactive: Optional[bool] = True,
        trust_server_cert: Optional[bool] = None,
        config_dir: Optional[pathlib.Path] = None,
        config_option: Optional[pathlib.Path] = None,
        **kwargs,
    ):
        """
        Passing None to a subcommand option, the flag won't be passed unless otherwise
        stated.

        `svn help` and `svn help [cmd]`

        Wraps svn's `Options
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.html#svn.ref.svn.sw>`_.

        Parameters
        ----------
        quiet :
            -q / --quiet
        username :
            --username
        password :
            --password
        no_auth_cache :
            --no-auth-cache
        non_interactive :
            --non-interactive, defaults to True
        trust_server_cert :
            --trust-server-cert
        config_dir :
            --config-dir
        config_option :
            --config-option, ``FILE:SECTION:OPTION=[VALUE]``
        cwd : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            Defaults to :attr:`~.cwd`

        Examples
        --------
        >>> svn = Svn(dir=tmp_path)
        >>> svn.run(['help'])  # doctest: +NORMALIZE_WHITESPACE
        "usage: svn <subcommand> [options] [args]..."
        """

        if isinstance(args, Sequence):
            cli_args = ["svn", *args]
        else:
            cli_args = ["svn", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.dir

        if no_auth_cache is True:
            cli_args.append("--no-auth-cache")
        if non_interactive is True:
            cli_args.append("--non-interactive")
        if username is not None:
            cli_args.append(f"--username {username}")
        if password is not None:
            cli_args.append(f"--password {password}")
        if trust_server_cert is True:
            cli_args.append("--trust-server_cert")
        if config_dir is not None:
            cli_args.append("--config-dir {config_dir}")
        if config_option is not None:
            cli_args.append("--config-option {config_option}")

        return run(cmd=cli_args, **kwargs)

    def checkout(
        self,
        url: str,
        revision: Union[RevisionLiteral, str] = None,
        force: Optional[bool] = None,
        ignore_externals: Optional[bool] = None,
        depth: DepthLiteral = None,
    ):
        """Check out a working copy from an SVN repo.

        Wraps `svn checkout
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.checkout.html>`_ (co).

        Parameters
        ----------
        url : str
        revision : Union[RevisionLiteral, str]
            Number, '{ DATE }', 'HEAD', 'BASE', 'COMMITTED', 'PREV'
        force : bool, optional
            force operation to run
        ignore_externals : bool, optional
            ignore externals definitions
        depth :
            Sparse checkout support, Optional

        Examples
        --------
        >>> svn = Svn(dir=tmp_path)
        >>> svn_remote_repo = create_svn_remote_repo()
        >>> svn.checkout(url=f'file://{svn_remote_repo}')
        'Checked out revision ...'
        >>> svn.checkout(url=f'file://{svn_remote_repo}', revision=1)
        'svn: E160006: No such revision 1...'
        """
        local_flags: list[str] = [url, str(self.dir)]

        if revision is not None:
            local_flags.append(f"--revision={revision}")
        if depth is not None:
            local_flags.append(depth)
        if force is True:
            local_flags.append("--force")
        if ignore_externals is True:
            local_flags.append("--ignore-externals")

        return self.run(["checkout", *local_flags], check_returncode=False)

    def add(
        self,
        path: Union[list[pathlib.Path], pathlib.Path],
        targets: Optional[pathlib.Path] = None,
        depth: DepthLiteral = None,
        force: Optional[bool] = None,
        auto_props: Optional[bool] = None,
        no_auto_props: Optional[bool] = None,
        parents: Optional[bool] = None,
    ):
        """
        Passing None means the flag won't be passed unless otherwise stated.

        Wraps `svn add
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.add.html>`_.

        Parameters
        ----------
        targets : pathlib.path
            `--targets ARG`: contents of file ARG as additional args
        depth :
            `--depth ARG`, Sparse checkout support, Optional
        force :
            `--force`, Ignore already versioned paths
        no_ignore :
            `--no-ignore`
        auto_props :
            `--auto-props`
        no_auto_props :
            `--no-auto-props`
        parents :
            `--parents`

        Examples
        --------
        >>> svn = Svn(dir=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        """
        local_flags: list[str] = []

        if isinstance(path, list):
            local_flags.extend(str(p.absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            local_flags.append(str(path.absolute()))

        if force is True:
            local_flags.append("--force")
        if depth is not None:
            local_flags.append(depth)
        if auto_props is True:
            local_flags.append("--auto-props")
        if no_auto_props is True:
            local_flags.append("--no-auto-props")
        if parents is True:
            local_flags.append("--parents")

        return self.run(["add", *local_flags])

    def auth(
        self,
        remove: Optional[str] = None,
        show_passwords: Optional[bool] = None,
        *args,
        **kwargs,
    ):
        """
        Wraps `svn auth
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.auth.html>`_.

        Parameters
        ----------
        remove : str, optional
            Remove matching auth credentials
        show_passwords : bool, optional
            Show cached passwords

        Examples
        --------
        >>> Svn(dir=tmp_path).auth()
        "Credentials cache in '...' is empty"
        """
        local_flags: list[str] = [*args]

        if remove is not None:
            local_flags.append(f"--remove {remove}")
        if show_passwords is True:
            local_flags.append("--show-passwords")

        return self.run(["auth", *local_flags])

    def blame(
        self,
        target: pathlib.Path,
        revision: Union[RevisionLiteral, str] = None,
        verbose: Optional[bool] = None,
        force: Optional[bool] = None,
        use_merge_history: Optional[bool] = None,
        incremental: Optional[bool] = None,
        xml: Optional[bool] = None,
        extensions: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """
        Wraps `svn blame
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.blame.html>`_.

        Parameters
        ----------
        target : pathlib.Path
            path of file
        revision : Union[RevisionLiteral, str]
            Number, '{ DATE }', 'HEAD', 'BASE', 'COMMITTED', 'PREV'
        verbose : bool
            `-v`, `--verbose`, output extra info
        use_merge_history : bool
            `-g`, `--use-merge-history`, show extra mergeg info
        incremental : bool
            `--incremental`, give output suitable for concatenation
        xml : bool
            `--xml`, xml output
        extensions : str, optional
            Diff or blame tool (pass raw args).
        force : bool, optional
            force operation to run

        Examples
        --------
        >>> svn = Svn(dir=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        'Checked out revision ...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        >>> svn.commit(path=new_file, message='My new commit')
        '...'
        >>> svn.blame('new.txt')
        '1        ... example text'
        """
        local_flags: list[str] = [target, *args]

        if revision is not None:
            local_flags.append(f"--revision={revision}")
        if verbose is True:
            local_flags.append("--verbose")
        if use_merge_history is True:
            local_flags.append("--use-merge-history")
        if incremental is True:
            local_flags.append("--incremental")
        if xml is True:
            local_flags.append("--xml")
        if extensions is not None:
            local_flags.append(f"--extensions {extensions}")
        if force is True:
            local_flags.append("--force")

        return self.run(["blame", *local_flags])

    def cat(self, *args, **kwargs):
        """
        Wraps `svn cat
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.cat.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["cat", *local_flags])

    def changelist(self, *args, **kwargs):
        """
        Wraps `svn changelist
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.changelist.html>`_ (cl).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["changelist", *local_flags])

    def cleanup(self, *args, **kwargs):
        """
        Wraps `svn cleanup
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.cleanup.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["cleanup", *local_flags])

    def commit(
        self,
        path: Union[list[pathlib.Path], pathlib.Path],
        targets: Optional[pathlib.Path] = None,
        message: Optional[str] = None,
        no_unlock: Optional[bool] = None,
        file: Optional[pathlib.Path] = None,
        depth: DepthLiteral = None,
        encoding: Optional[str] = None,
        force_log: Optional[bool] = None,
        keep_changelists: Optional[bool] = None,
        include_externals: Optional[bool] = None,
        *args,
        **kwargs,
    ):
        """
        Wraps `svn commit
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.commit.html>`_ (ci).

        Parameters
        ----------
        targets : pathlib.Path
            `--targets ARG`: contents of file ARG as additional args
        depth :
            `--depth ARG`, Sparse checkout support, Optional
        encoding :
            `--encoding`, treat value as charset encoding passed
        keep_changelists :
            `--keep_changelists`, don't delete changelists after commit
        force_log :
            `--force-log`, Ignore already versioned paths

        Examples
        --------
        >>> svn = Svn(dir=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        >>> svn.commit(path=new_file, message='My new commit')
        'Adding          new.txt...Transmitting file data...Committed revision 1.'
        """
        local_flags: list[str] = []

        if isinstance(path, list):
            local_flags.extend(str(p.absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            local_flags.append(str(path.absolute()))

        if depth is not None:
            local_flags.append(depth)
        if message is not None:
            local_flags.append(f'--message="{message}"')
        if no_unlock is True:
            local_flags.append("--no-unlock")
        if file is not None:
            local_flags.append(f"--file {file}")
        if force_log is True:
            local_flags.append("--force")
        if include_externals is True:
            local_flags.append("--include-externals")

        return self.run(["commit", *local_flags])

    def copy(self, *args, **kwargs):
        """
        Wraps `svn copy
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.copy.html>`_ (cp).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["copy", *local_flags])

    def delete(self, *args, **kwargs):
        """
        Wraps `svn delete
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.delete.html>`_ (del, remove,
        rm).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["delete", *local_flags])

    def diff(self, *args, **kwargs):
        """
        Wraps `svn diff
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.delete.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["diff", *local_flags])

    def export(self, *args, **kwargs):
        """
        Wraps `svn export
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.export.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["export", *local_flags])

    def help(self, *args, **kwargs):
        """
        Wraps `svn help
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.help.html>`_ (?, h).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["help", *local_flags])

    def import_(self, *args, **kwargs):
        """
        Wraps `svn import
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.import.html>`_.

        Due to python limitation, .import isn't possible.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["import", *local_flags])

    def info(self, *args, **kwargs):
        """
        Wraps `svn info
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.info.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["info", *local_flags])

    def list(self, *args, **kwargs):
        """
        Wraps `svn list
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.list.html>`_ (ls).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["list", *local_flags])

    def lock(self, *args, **kwargs):
        """
        Wraps `svn lock
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.lock.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["lock", *local_flags])

    def log(self, *args, **kwargs):
        """
        Wraps `svn log
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.log.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["log", *local_flags])

    def merge(self, *args, **kwargs):
        """
        Wraps `svn merge
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.merge.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["merge", *local_flags])

    def mergelist(self, *args, **kwargs):
        """
        Wraps `svn mergelist
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.mergelist.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["mergelist", *local_flags])

    def mkdir(self, *args, **kwargs):
        """
        Wraps `svn mkdir
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.mkdir.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["mkdir", *local_flags])

    def move(self, *args, **kwargs):
        """
        Wraps `svn move
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.mkdir.html>`_ (mv, rename,
        ren).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["move", *local_flags])

    def patch(self, *args, **kwargs):
        """
        Wraps `svn patch
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.patch.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["patch", *local_flags])

    def propdel(self, *args, **kwargs):
        """
        Wraps `svn propdel
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propdel.html>`_ (pdel, pd).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["propdel", *local_flags])

    def propedit(self, *args, **kwargs):
        """
        Wraps `svn propedit
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propedit.html>`_ (pedit, pe).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["propedit", *local_flags])

    def propget(self, *args, **kwargs):
        """
        Wraps `svn propget
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propget.html>`_ (pget, pg).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["propget", *local_flags])

    def proplist(self, *args, **kwargs):
        """
        Wraps `svn proplist
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.proplist.html>`_ (plist, pl).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["proplist", *local_flags])

    def propset(self, *args, **kwargs):
        """
        Wraps `svn propset
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propset.html>`_ (pset, ps).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["propset", *local_flags])

    def relocate(self, *args, **kwargs):
        """
        Wraps `svn relocate
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.relocate.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["relocate", *local_flags])

    def resolve(self, *args, **kwargs):
        """
        Wraps `svn resolve
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.resolve.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["resolve", *local_flags])

    def resolved(self, *args, **kwargs):
        """
        Wraps `svn resolved
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.resolved.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["resolved", *local_flags])

    def revert(self, *args, **kwargs):
        """
        Wraps `svn revert
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.revert.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["revert", *local_flags])

    def status(self, *args, **kwargs):
        """
        Wraps `svn status
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.status.html>`_ (stat, st).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["status", *local_flags])

    def switch(self, *args, **kwargs):
        """
        Wraps `svn switch
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.switch.html>`_ (sw).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["switch", *local_flags])

    def unlock(self, *args, **kwargs):
        """
        Wraps `svn unlock
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.unlock.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["unlock", *local_flags])

    def update(self, *args, **kwargs):
        """
        Wraps `svn update
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.update.html>`_ (up).

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["update", *local_flags])

    def upgrade(self, *args, **kwargs):
        """
        Wraps `svn upgrade
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.upgrade.html>`_.

        Parameters
        ----------
        """
        local_flags: list[str] = [*args]

        self.run(["upgrade", *local_flags])
