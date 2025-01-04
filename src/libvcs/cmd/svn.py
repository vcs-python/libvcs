"""Run svn (subversion) commands directly against SVN working copy.

.. admonition:: Busman's holiday?.

   We need to fill these SVN commands and their tests to exquisite perfection, like the
   artisans in those Michelin-star videos on YouTube. We welcome your contributions,
   providing you "color between the lines" and stick to the interface. `Get in
   <https://github.com/vcs-python/libvcs>`_, 'APIs unstable until we fit the spec.
"""

from __future__ import annotations

import pathlib
import typing as t
from collections.abc import Sequence

from libvcs import exc
from libvcs._internal.run import ProgressCallbackProtocol, run
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = t.Union[StrOrBytesPath, Sequence[StrOrBytesPath]]

DepthLiteral = t.Union[t.Literal["infinity", "empty", "files", "immediates"], None]
RevisionLiteral = t.Union[t.Literal["HEAD", "BASE", "COMMITTED", "PREV"], None]


class SvnPropsetValueOrValuePathRequired(exc.LibVCSException, TypeError):
    """Raised when required parameters are not passed."""

    def __init__(self, *args: object) -> None:
        return super().__init__("Must enter a value or value_path")


class Svn:
    """Run commands directly against SVN working copy."""

    progress_callback: ProgressCallbackProtocol | None = None

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: ProgressCallbackProtocol | None = None,
    ) -> None:
        """Lite, typed, pythonic wrapper for svn(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding svn subcommand.

        Examples
        --------
        >>> Svn(path=tmp_path)
        <Svn path=...>
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.progress_callback = progress_callback

    def __repr__(self) -> str:
        """Representation of an SVN command object."""
        return f"<Svn path={self.path}>"

    def run(
        self,
        args: _CMD,
        *,
        quiet: bool | None = None,
        username: str | None = None,
        password: str | None = None,
        no_auth_cache: bool | None = None,
        non_interactive: bool | None = True,
        trust_server_cert: bool | None = None,
        config_dir: pathlib.Path | None = None,
        config_option: pathlib.Path | None = None,
        # Special behavior
        make_parents: bool | None = True,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command for this SVN working copy.

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
        cwd : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            Defaults to :attr:`~.cwd`
        make_parents : bool, default: ``True``
            Creates checkout directory (`:attr:`self.path`) if it doesn't already exist.
        check_returncode : bool, default: ``None``
            Passthrough to :meth:`Svn.run`

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.run(['help'])
        "usage: svn <subcommand> [options] [args]..."
        """
        cli_args = ["svn", *args] if isinstance(args, Sequence) else ["svn", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.path

        if no_auth_cache is True:
            cli_args.append("--no-auth-cache")
        if non_interactive is True:
            cli_args.append("--non-interactive")
        if username is not None:
            cli_args.extend(["--username", username])
        if password is not None:
            cli_args.extend(["--password", password])
        if trust_server_cert is True:
            cli_args.append("--trust-server_cert")
        if config_dir is not None:
            cli_args.extend(["--config-dir", str(config_dir)])
        if config_option is not None:
            cli_args.extend(["--config-option", str(config_option)])

        if self.progress_callback is not None:
            kwargs["callback"] = self.progress_callback

        return run(
            args=cli_args,
            check_returncode=True if check_returncode is None else check_returncode,
            **kwargs,
        )

    def checkout(
        self,
        *,
        url: str,
        revision: RevisionLiteral | str = None,
        force: bool | None = None,
        ignore_externals: bool | None = None,
        depth: DepthLiteral = None,
        quiet: bool | None = None,
        username: str | None = None,
        password: str | None = None,
        no_auth_cache: bool | None = None,
        non_interactive: bool | None = True,
        trust_server_cert: bool | None = None,
        # Special behavior
        make_parents: bool | None = True,
        check_returncode: bool | None = False,
    ) -> str:
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
        make_parents : bool, default: ``True``
            Creates checkout directory (`:attr:`self.path`) if it doesn't already exist.
        check_returncode : bool, default: True
            Passthrough to :meth:`Svn.run`

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn_remote_repo = create_svn_remote_repo()
        >>> svn.checkout(url=f'file://{svn_remote_repo}')
        '...Checked out revision ...'
        >>> svn.checkout(url=f'file://{svn_remote_repo}', revision=10)
        'svn: E160006: No such revision 10...'
        """
        local_flags: list[str] = [url, str(self.path)]

        if revision is not None:
            local_flags.extend(["--revision", str(revision)])
        if depth is not None:
            local_flags.extend(["--depth", depth])
        if force is True:
            local_flags.append("--force")
        if ignore_externals is True:
            local_flags.append("--ignore-externals")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)

        return self.run(
            ["checkout", *local_flags],
            quiet=quiet,
            username=username,
            password=password,
            no_auth_cache=no_auth_cache,
            non_interactive=non_interactive,
            trust_server_cert=trust_server_cert,
            check_returncode=check_returncode,
        )

    def add(
        self,
        *,
        path: list[pathlib.Path] | pathlib.Path,
        targets: pathlib.Path | None = None,
        depth: DepthLiteral = None,
        force: bool | None = None,
        auto_props: bool | None = None,
        no_auto_props: bool | None = None,
        parents: bool | None = None,
    ) -> str:
        """Stage an unversioned file to be pushed to repository next commit.

        Passing None means the flag won't be passed unless otherwise stated.

        Wraps `svn add
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.add.html>`_.

        Parameters
        ----------
        targets : pathlib.Path
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
        >>> svn = Svn(path=tmp_path)
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
        remove: str | None = None,
        show_passwords: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Manage stored authentication credentials.

        Wraps `svn auth
        <https://subversion.apache.org/faq.html#plaintext-passwords>`_.

        Parameters
        ----------
        remove : str, optional
            Remove matching auth credentials
        show_passwords : bool, optional
            Show cached passwords

        Examples
        --------
        >>> Svn(path=tmp_path).auth()
        "Credentials cache in '...' is empty"
        """
        local_flags: list[str] = []

        if remove is not None:
            local_flags.extend(["--remove", remove])
        if show_passwords is True:
            local_flags.append("--show-passwords")

        return self.run(["auth", *local_flags])

    def blame(
        self,
        target: StrOrBytesPath,
        *,
        revision: RevisionLiteral | str = None,
        verbose: bool | None = None,
        force: bool | None = None,
        use_merge_history: bool | None = None,
        incremental: bool | None = None,
        xml: bool | None = None,
        extensions: str | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Show authorship for file line-by-line.

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
        >>> svn = Svn(path=tmp_path)
        >>> repo = create_svn_remote_repo()
        >>> svn.checkout(url=f'file://{repo}')
        '...Checked out revision ...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        >>> svn.commit(path=new_file, message='My new commit')
        '...'
        >>> svn.blame('new.txt')
        '4        ... example text'
        """
        local_flags: list[str] = [str(target)]

        if revision is not None:
            local_flags.extend(["--revision", revision])
        if verbose is True:
            local_flags.append("--verbose")
        if use_merge_history is True:
            local_flags.append("--use-merge-history")
        if incremental is True:
            local_flags.append("--incremental")
        if xml is True:
            local_flags.append("--xml")
        if extensions is not None:
            local_flags.extend(["--extensions", extensions])
        if force is True:
            local_flags.append("--force")

        return self.run(["blame", *local_flags])

    def cat(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Output contents of files from working copy or repository URLs.

        Wraps `svn cat
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.cat.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["cat", *local_flags])

    def changelist(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Connect or disconnect files with a changelist.

        Wraps `svn changelist
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.changelist.html>`_ (cl).
        """
        local_flags: list[str] = [*args]

        return self.run(["changelist", *local_flags])

    def cleanup(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Recursively clean up working copy of locks. Unblocks operations.

        Wraps `svn cleanup
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.cleanup.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["cleanup", *local_flags])

    def commit(
        self,
        *,
        path: list[pathlib.Path] | pathlib.Path,
        targets: pathlib.Path | None = None,
        message: str | None = None,
        no_unlock: bool | None = None,
        file: pathlib.Path | None = None,
        depth: DepthLiteral = None,
        encoding: str | None = None,
        force_log: bool | None = None,
        keep_changelists: bool | None = None,
        include_externals: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Push changes from working copy to SVN repo.

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
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        >>> svn.commit(path=new_file, message='My new commit')
        'Adding          new.txt...Transmitting file data...Committed revision 4.'
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
            local_flags.extend(["--file", str(file)])
        if force_log is True:
            local_flags.append("--force")
        if include_externals is True:
            local_flags.append("--include-externals")

        return self.run(["commit", *local_flags])

    def copy(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Copy file or dir in this SVN working copy or repo.

        Wraps `svn copy
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.copy.html>`_ (cp).
        """
        local_flags: list[str] = [*args]

        return self.run(["copy", *local_flags])

    def delete(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Remove file from this SVN working copy or repo.

        Wraps `svn delete
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.delete.html>`_ (del, remove,
        rm).
        """
        local_flags: list[str] = [*args]

        return self.run(["delete", *local_flags])

    def diff(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Return diff of two files or revisions.

        Wraps `svn diff
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.delete.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["diff", *local_flags])

    def export(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Export clean directory tree of working directory.

        Wraps `svn export
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.export.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["export", *local_flags])

    def help(self, *args: t.Any, **kwargs: t.Any) -> str:
        """SVN Help command.

        Wraps `svn help
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.help.html>`_ (?, h).
        """
        local_flags: list[str] = [*args]

        return self.run(["help", *local_flags])

    def import_(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Import local directory into repository.

        Wraps `svn import
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.import.html>`_.

        Due to python limitation, .import isn't possible.
        """
        local_flags: list[str] = [*args]

        return self.run(["import", *local_flags])

    def info(
        self,
        target: StrPath | None = None,
        targets: list[StrPath] | StrPath | None = None,
        changelist: list[str] | None = None,
        revision: str | None = None,
        depth: DepthLiteral = None,
        incremental: bool | None = None,
        recursive: bool | None = None,
        xml: bool | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        """Return info about this SVN repository.

        Wraps `svn info
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.info.html>`_.

        targets : pathlib.Path
            `--targets ARG`: contents of file ARG as additional args
        xml : bool
            `--xml`, xml output
        revision : Union[RevisionLiteral, str]
            Number, '{ DATE }', 'HEAD', 'BASE', 'COMMITTED', 'PREV'
        depth :
            `--depth ARG`, Sparse checkout support, Optional
        incremental : bool
            `--incremental`, give output suitable for concatenation
        """
        local_flags: list[str] = [*args]

        if isinstance(target, pathlib.Path):
            local_flags.append(str(target.absolute()))
        elif isinstance(target, str):
            local_flags.append(target)

        if revision is not None:
            local_flags.extend(["--revision", revision])
        if targets is not None:
            if isinstance(targets, Sequence):
                local_flags.extend(["--targets", *[str(t) for t in targets]])
            else:
                local_flags.extend(["--targets", str(targets)])
        if changelist is not None:
            local_flags.extend(["--changelist", *changelist])
        if recursive is True:
            local_flags.append("--recursive")
        if xml is True:
            local_flags.append("--xml")
        if incremental is True:
            local_flags.append("--incremental")

        return self.run(["info", *local_flags])

    def ls(self, *args: t.Any, **kwargs: t.Any) -> str:
        """List files in SVN repository (without downloading them).

        Wraps `svn list
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.list.html>`_ (ls).
        """
        local_flags: list[str] = [*args]

        return self.run(["list", *local_flags])

    def lock(
        self,
        targets: pathlib.Path | None = None,
        force: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Lock path or URLs for working copy or repository.

        Wraps `svn lock
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.lock.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.lock(targets='samplepickle')
        "'samplepickle' locked by user '...'."
        """
        local_flags: list[str] = []

        if targets is not None:
            if isinstance(targets, str):
                local_flags.extend([str(targets)])
            elif isinstance(targets, Sequence):
                local_flags.extend([*[str(t) for t in targets]])

        if force:
            local_flags.append("--force")

        return self.run(["lock", *local_flags])

    def log(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Show logs from repository.

        Wraps `svn log
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.log.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["log", *local_flags])

    def merge(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Apply diffs between two places to SVN working copy.

        Wraps `svn merge
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.merge.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["merge", *local_flags])

    def mkdir(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Create directory in SVN working copy.

        Wraps `svn mkdir
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.mkdir.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["mkdir", *local_flags])

    def move(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Move a file in SVN working copy.

        Wraps `svn move
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.mkdir.html>`_ (mv, rename,
        ren).
        """
        local_flags: list[str] = [*args]

        return self.run(["move", *local_flags])

    def patch(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Apply a patch to SVN working copy.

        Wraps `svn patch
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.patch.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["patch", *local_flags])

    def propdel(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Remove a property for this SVN working copy.

        Wraps `svn propdel
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propdel.html>`_ (pdel, pd).
        """
        local_flags: list[str] = [*args]

        return self.run(["propdel", *local_flags])

    def propedit(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Change a property for this SVN working copy.

        Wraps `svn propedit
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propedit.html>`_ (pedit, pe).
        """
        local_flags: list[str] = [*args]

        return self.run(["propedit", *local_flags])

    def propget(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Return a property for this SVN working copy.

        Wraps `svn propget
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propget.html>`_ (pget, pg).
        """
        local_flags: list[str] = [*args]

        return self.run(["propget", *local_flags])

    def proplist(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Return list of properties for this SVN working copy.

        Wraps `svn proplist
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.proplist.html>`_ (plist, pl).
        """
        local_flags: list[str] = [*args]

        return self.run(["proplist", *local_flags])

    def propset(
        self,
        name: str,
        path: StrPath | None = None,
        value: str | None = None,
        value_path: StrPath | None = None,
        target: StrOrBytesPath | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        """Set property for this SVN working copy or a remote revision.

        Note: Setting remote properties via --revprop does not work yet.

        Wraps `svn propset
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.propset.html>`_ (pset, ps).

        Parameters
        ----------
        name : str
            propname
        value_path :
            VALFILE

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.propset(name="my_prop", value="value", path=".")
        "property 'my_prop' set on '.'"
        """
        local_flags: list[str] = [name, *args]

        if value is not None:
            local_flags.append(value)
        elif isinstance(value_path, pathlib.Path):
            local_flags.extend(["--file", str(pathlib.Path(value_path).absolute())])
        else:
            raise SvnPropsetValueOrValuePathRequired

        if path is not None:
            if isinstance(path, (str, pathlib.Path)):
                local_flags.append(str(pathlib.Path(path).absolute()))
        elif target is not None:
            local_flags.append(str(target))

        return self.run(["propset", *local_flags])

    def relocate(self, *, to_path: StrPath, **kwargs: t.Any) -> str:
        """Set the SVN repository URL for this working copy.

        Wraps `svn relocate
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.relocate.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path / 'initial_place')
        >>> repo_path = create_svn_remote_repo()
        >>> svn.checkout(url=repo_path.as_uri())
        '...Checked out revision ...'
        >>> new_place = repo_path.rename(tmp_path / 'new_place')
        >>> svn.relocate(to_path=new_place.absolute().as_uri())
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if isinstance(to_path, str):
            if to_path.startswith("file://"):
                required_flags.append(to_path)
            else:
                required_flags.append(str(pathlib.Path(to_path).absolute().as_uri()))
        elif isinstance(to_path, pathlib.Path):
            required_flags.append(str(to_path.absolute().as_uri()))

        return self.run(["relocate", *local_flags, *required_flags])

    def resolve(
        self,
        path: list[pathlib.Path] | pathlib.Path,
        targets: pathlib.Path | None = None,
        depth: DepthLiteral = None,
        force: bool | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        """Resolve conflicts with this SVN working copy.

        Wraps `svn resolve
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.resolve.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.resolve(path='.')
        ''
        """
        local_flags: list[str] = [*args]

        if isinstance(path, list):
            local_flags.extend(str(p.absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            local_flags.append(str(path.absolute()))

        if targets is not None:
            if isinstance(targets, Sequence):
                local_flags.extend(["--targets", *[str(t) for t in targets]])
            else:
                local_flags.extend(["--targets", str(targets)])

        if depth is not None:
            local_flags.extend(["--depth", depth])
        if force is not None:
            local_flags.append("--force")

        return self.run(["resolve", *local_flags])

    def resolved(
        self,
        *,
        path: list[pathlib.Path] | pathlib.Path,
        targets: pathlib.Path | None = None,
        depth: DepthLiteral = None,
        force: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Resolve this working copy's conflicted state.

        Wraps `svn resolved
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.resolved.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.resolved(path='.')
        ''
        """
        local_flags: list[str] = []

        if isinstance(path, list):
            local_flags.extend(str(p.absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            local_flags.append(str(path.absolute()))

        if path is not None:
            if isinstance(path, str):
                local_flags.append(str(pathlib.Path(path).absolute()))
            if isinstance(path, list):
                local_flags.extend(str(p.absolute()) for p in path)
            elif isinstance(path, pathlib.Path):
                local_flags.append(str(path.absolute()))
        elif targets is not None:
            if isinstance(targets, Sequence):
                local_flags.extend(["--targets", *[str(t) for t in targets]])
            else:
                local_flags.extend(["--targets", str(targets)])

        if depth is not None:
            local_flags.extend(["--depth", depth])
        if force is not None:
            local_flags.append("--force")

        return self.run(["resolved", *local_flags])

    def revert(
        self,
        *,
        path: list[pathlib.Path] | pathlib.Path,
        targets: pathlib.Path | None = None,
        depth: DepthLiteral = None,
        force: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Revert any changes to this SVN working copy.

        Wraps `svn revert
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.revert.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> new_file = tmp_path / 'new.txt'
        >>> new_file.write_text('example text', encoding="utf-8")
        12
        >>> svn.add(path=new_file)
        'A  new.txt'
        >>> svn.commit(path=new_file, message='My new commit')
        '...'
        >>> svn.revert(path=new_file)
        ''
        """
        local_flags: list[str] = []

        if isinstance(path, list):
            local_flags.extend(str(p.absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            local_flags.append(str(path.absolute()))

        if path is not None:
            if isinstance(path, str):
                local_flags.append(str(pathlib.Path(path).absolute()))
            if isinstance(path, list):
                local_flags.extend(str(p.absolute()) for p in path)
            elif isinstance(path, pathlib.Path):
                local_flags.append(str(path.absolute()))
        elif targets is not None:
            if isinstance(targets, Sequence):
                local_flags.extend(["--targets", *[str(t) for t in targets]])
            else:
                local_flags.extend(["--targets", str(targets)])

        if depth is not None:
            local_flags.extend(["--depth", depth])
        if force is not None:
            local_flags.append("--force")

        return self.run(["revert", *local_flags])

    def status(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Return status of this SVN working copy.

        Wraps `svn status
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.status.html>`_ (stat, st).

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.status()
        ''
        """
        local_flags: list[str] = [*args]

        return self.run(["status", *local_flags])

    def switch(
        self,
        *,
        to_path: StrPath,
        path: StrPath,
        ignore_ancestry: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Switch working copy to a different SVN repo URL.

        Wraps `svn switch
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.switch.html>`_ (sw).

        Examples
        --------
        >>> svn = Svn(path=tmp_path / 'initial_place')
        >>> repo_path = create_svn_remote_repo()
        >>> svn.checkout(url=(repo_path / 'sampledir').as_uri())
        '...Checked out revision ...'
        >>> other_dir = repo_path / 'otherdir'
        >>> svn.switch(to_path=other_dir.as_uri(), path='.', ignore_ancestry=True)
        'D...Updated to revision...'
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if isinstance(to_path, str):
            if to_path.startswith("file://"):
                local_flags.append(to_path)
            else:
                local_flags.append(str(pathlib.Path(to_path).absolute().as_uri()))
        elif isinstance(to_path, pathlib.Path):
            local_flags.append(str(to_path.absolute().as_uri()))

        if path is not None:
            if isinstance(path, str):
                local_flags.append(path)
            elif isinstance(path, pathlib.Path):
                local_flags.append(str(path.absolute()))

        if ignore_ancestry:
            local_flags.append("--ignore-ancestry")

        return self.run(["switch", *local_flags, *required_flags])

    def unlock(
        self,
        targets: pathlib.Path | None = None,
        force: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Unlock path or URL reserved by another user.

        Wraps `svn unlock
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.unlock.html>`_.

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.lock(targets='samplepickle')
        "'samplepickle' locked by user '...'."
        >>> svn.unlock(targets='samplepickle')
        "'samplepickle' unlocked."
        """
        local_flags: list[str] = []

        if targets is not None:
            if isinstance(targets, str):
                local_flags.extend([str(targets)])
            elif isinstance(targets, Sequence):
                local_flags.extend([*[str(t) for t in targets]])

        if force:
            local_flags.append("--force")

        return self.run(["unlock", *local_flags])

    def update(
        self,
        accept: str | None = None,
        changelist: list[str] | None = None,
        diff3_cmd: str | None = None,
        editor_cmd: str | None = None,
        force: bool | None = None,
        ignore_externals: bool | None = None,
        parents: bool | None = None,
        quiet: bool | None = None,
        revision: str | None = None,
        set_depth: str | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        """Fetch latest changes to working copy.

        Wraps `svn update
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.update.html>`_ (up).

        Examples
        --------
        >>> svn = Svn(path=tmp_path)
        >>> svn.checkout(url=f'file://{create_svn_remote_repo()}')
        '...Checked out revision ...'
        >>> svn.update()
        "Updating ..."
        """
        local_flags: list[str] = [*args]

        if revision is not None:
            local_flags.extend(["--revision", revision])
        if diff3_cmd is not None:
            local_flags.extend(["--diff3-cmd", diff3_cmd])
        if editor_cmd is not None:
            local_flags.extend(["--editor-cmd", editor_cmd])
        if set_depth is not None:
            local_flags.extend(["--set-depth", set_depth])
        if changelist is not None:
            local_flags.extend(["--changelist", *changelist])
        if force is True:
            local_flags.append("--force")
        if quiet is True:
            local_flags.append("--quiet")
        if parents is True:
            local_flags.append("--parents")
        if ignore_externals is True:
            local_flags.append("--ignore-externals")

        return self.run(["update", *local_flags])

    def upgrade(self, *args: t.Any, **kwargs: t.Any) -> str:
        """Upgrade working copy's metadata storage format.

        Wraps `svn upgrade
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.upgrade.html>`_.
        """
        local_flags: list[str] = [*args]

        return self.run(["upgrade", *local_flags])
