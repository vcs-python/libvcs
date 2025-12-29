"""Async git commands directly against a local git repo.

Async equivalent of :mod:`libvcs.cmd.git`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import pathlib
import typing as t
from collections.abc import Sequence

from libvcs._internal.async_run import (
    AsyncProgressCallbackProtocol,
    async_run,
)
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = StrOrBytesPath | Sequence[StrOrBytesPath]


class AsyncGit:
    """Run commands directly on a git repository asynchronously.

    Async equivalent of :class:`~libvcs.cmd.git.Git`.

    Parameters
    ----------
    path : str | Path
        Path to the git repository
    progress_callback : AsyncProgressCallbackProtocol, optional
        Async callback for progress reporting

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     git = AsyncGit(path="/path/to/repo")
    ...     status = await git.status()
    ...     return status
    >>> # asyncio.run(example())
    """

    progress_callback: AsyncProgressCallbackProtocol | None = None

    # Sub-commands (will be populated in __init__)
    submodule: AsyncGitSubmoduleCmd
    remotes: AsyncGitRemoteManager
    stash: AsyncGitStashCmd

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
    ) -> None:
        """Initialize AsyncGit command wrapper.

        Parameters
        ----------
        path : str | Path
            Path to the git repository
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress reporting
        """
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.progress_callback = progress_callback

        # Initialize sub-command managers
        self.submodule = AsyncGitSubmoduleCmd(path=self.path, cmd=self)
        self.remotes = AsyncGitRemoteManager(path=self.path, cmd=self)
        self.stash = AsyncGitStashCmd(path=self.path, cmd=self)

    def __repr__(self) -> str:
        """Representation of AsyncGit repo command object."""
        return f"<AsyncGit path={self.path}>"

    async def run(
        self,
        args: _CMD,
        *,
        # Normal flags
        C: StrOrBytesPath | list[StrOrBytesPath] | None = None,
        cwd: StrOrBytesPath | None = None,
        git_dir: StrOrBytesPath | None = None,
        work_tree: StrOrBytesPath | None = None,
        namespace: StrOrBytesPath | None = None,
        bare: bool | None = None,
        no_replace_objects: bool | None = None,
        literal_pathspecs: bool | None = None,
        no_optional_locks: bool | None = None,
        config: dict[str, t.Any] | None = None,
        # Pass-through to async_run()
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command for this git repository asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.run`.

        Parameters
        ----------
        args : list[str] | str
            Git subcommand and arguments
        cwd : str | Path, optional
            Working directory. Defaults to self.path.
        config : dict[str, Any], optional
            Git config options to pass via --config
        check_returncode : bool, default True
            Raise on non-zero exit code
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output

        Examples
        --------
        >>> import asyncio
        >>> async def example():
        ...     git = AsyncGit(path="/path/to/repo")
        ...     return await git.run(["status"])
        >>> # asyncio.run(example())
        """
        cli_args: list[str]
        if isinstance(args, Sequence) and not isinstance(args, (str, bytes)):
            cli_args = ["git", *[str(a) for a in args]]
        else:
            cli_args = ["git", str(args)]

        run_cwd = cwd if cwd is not None else self.path

        # Build flags
        if C is not None:
            c_list = [C] if not isinstance(C, list) else C
            for c in c_list:
                cli_args.extend(["-C", str(c)])
        if config is not None:
            for k, v in config.items():
                val = "true" if v is True else ("false" if v is False else str(v))
                cli_args.extend(["--config", f"{k}={val}"])
        if git_dir is not None:
            cli_args.extend(["--git-dir", str(git_dir)])
        if work_tree is not None:
            cli_args.extend(["--work-tree", str(work_tree)])
        if namespace is not None:
            cli_args.extend(["--namespace", str(namespace)])
        if bare is True:
            cli_args.append("--bare")
        if no_replace_objects is True:
            cli_args.append("--no-replace-objects")
        if literal_pathspecs is True:
            cli_args.append("--literal-pathspecs")
        if no_optional_locks is True:
            cli_args.append("--no-optional-locks")

        return await async_run(
            args=cli_args,
            cwd=run_cwd,
            check_returncode=check_returncode,
            callback=self.progress_callback if log_in_real_time else None,
            timeout=timeout,
            **kwargs,
        )

    async def clone(
        self,
        *,
        url: str,
        depth: int | None = None,
        branch: str | None = None,
        origin: str | None = None,
        progress: bool | None = None,
        no_checkout: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        config: dict[str, t.Any] | None = None,
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        make_parents: bool | None = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Clone a working copy from a git repo asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.clone`.

        Parameters
        ----------
        url : str
            Repository URL to clone
        depth : int, optional
            Create a shallow clone with history truncated
        branch : str, optional
            Branch to checkout after clone
        origin : str, optional
            Name for the remote
        progress : bool, optional
            Force progress reporting
        quiet : bool, optional
            Suppress output
        make_parents : bool, default True
            Create parent directories if they don't exist
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output

        Examples
        --------
        >>> import asyncio
        >>> async def example():
        ...     git = AsyncGit(path="/tmp/myrepo")
        ...     await git.clone(url="https://github.com/user/repo")
        >>> # asyncio.run(example())
        """
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)

        local_flags: list[str] = []
        if depth is not None:
            local_flags.extend(["--depth", str(depth)])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if origin is not None:
            local_flags.extend(["--origin", origin])
        if quiet is True:
            local_flags.append("--quiet")
        if verbose is True:
            local_flags.append("--verbose")
        if progress is True:
            local_flags.append("--progress")
        if no_checkout is True:
            local_flags.append("--no-checkout")

        return await self.run(
            ["clone", *local_flags, url, str(self.path)],
            cwd=self.path.parent,
            config=config,
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode if check_returncode is not None else True,
            timeout=timeout,
            **kwargs,
        )

    async def fetch(
        self,
        *,
        repository: str | None = None,
        refspec: str | list[str] | None = None,
        _all: bool | None = None,
        append: bool | None = None,
        depth: int | None = None,
        force: bool | None = None,
        prune: bool | None = None,
        prune_tags: bool | None = None,
        tags: bool | None = None,
        no_tags: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        progress: bool | None = None,
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Fetch from remote repository asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.fetch`.

        Parameters
        ----------
        repository : str, optional
            Remote name to fetch from
        refspec : str | list[str], optional
            Refspec(s) to fetch
        _all : bool, optional
            Fetch all remotes
        depth : int, optional
            Deepen shallow clone
        prune : bool, optional
            Remove remote-tracking refs that no longer exist
        tags : bool, optional
            Fetch all tags
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if _all is True:
            local_flags.append("--all")
        if append is True:
            local_flags.append("--append")
        if depth is not None:
            local_flags.extend(["--depth", str(depth)])
        if force is True:
            local_flags.append("--force")
        if prune is True:
            local_flags.append("--prune")
        if prune_tags is True:
            local_flags.append("--prune-tags")
        if tags is True:
            local_flags.append("--tags")
        if no_tags is True:
            local_flags.append("--no-tags")
        if quiet is True:
            local_flags.append("--quiet")
        if verbose is True:
            local_flags.append("--verbose")
        if progress is True:
            local_flags.append("--progress")

        args: list[str] = ["fetch", *local_flags]
        if repository is not None:
            args.append(repository)
        if refspec is not None:
            if isinstance(refspec, list):
                args.extend(refspec)
            else:
                args.append(refspec)

        return await self.run(
            args,
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def checkout(
        self,
        *,
        branch: str | None = None,
        pathspec: str | list[str] | None = None,
        force: bool | None = None,
        quiet: bool | None = None,
        detach: bool | None = None,
        track: bool | str | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Checkout a branch or paths asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.checkout`.

        Parameters
        ----------
        branch : str, optional
            Branch name to checkout
        pathspec : str | list[str], optional
            Path(s) to checkout
        force : bool, optional
            Force checkout (discard local changes)
        quiet : bool, optional
            Suppress output
        detach : bool, optional
            Detach HEAD at named commit
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if force is True:
            local_flags.append("--force")
        if quiet is True:
            local_flags.append("--quiet")
        if detach is True:
            local_flags.append("--detach")
        if track is True:
            local_flags.append("--track")
        elif isinstance(track, str):
            local_flags.append(f"--track={track}")

        args: list[str] = ["checkout", *local_flags]
        if branch is not None:
            args.append(branch)
        if pathspec is not None:
            args.append("--")
            if isinstance(pathspec, list):
                args.extend(pathspec)
            else:
                args.append(pathspec)

        return await self.run(
            args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def status(
        self,
        *,
        short: bool | None = None,
        branch: bool | None = None,
        porcelain: bool | str | None = None,
        untracked_files: str | None = None,
        ignored: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Show working tree status asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.status`.

        Parameters
        ----------
        short : bool, optional
            Give output in short format
        branch : bool, optional
            Show branch info even in short format
        porcelain : bool | str, optional
            Machine-readable format
        untracked_files : str, optional
            Untracked files mode: "no", "normal", "all"
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Status output
        """
        local_flags: list[str] = []
        if short is True:
            local_flags.append("--short")
        if branch is True:
            local_flags.append("--branch")
        if porcelain is True:
            local_flags.append("--porcelain")
        elif isinstance(porcelain, str):
            local_flags.append(f"--porcelain={porcelain}")
        if untracked_files is not None:
            local_flags.append(f"--untracked-files={untracked_files}")
        if ignored is True:
            local_flags.append("--ignored")

        return await self.run(
            ["status", *local_flags],
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def rev_parse(
        self,
        *,
        args: str | list[str] | None = None,
        verify: bool | None = None,
        short: bool | int | None = None,
        abbrev_ref: bool | str | None = None,
        show_toplevel: bool | None = None,
        git_dir: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Parse git references asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.rev_parse`.

        Parameters
        ----------
        args : str | list[str], optional
            Revision arguments to parse
        verify : bool, optional
            Verify the parameter is a valid object name
        short : bool | int, optional
            Use short object name
        abbrev_ref : bool | str, optional
            Use abbreviated ref format
        show_toplevel : bool, optional
            Show path of top-level directory
        git_dir : bool, optional
            Show path of .git directory
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Parsed reference
        """
        local_flags: list[str] = []
        if verify is True:
            local_flags.append("--verify")
        if short is True:
            local_flags.append("--short")
        elif isinstance(short, int):
            local_flags.append(f"--short={short}")
        if abbrev_ref is True:
            local_flags.append("--abbrev-ref")
        elif isinstance(abbrev_ref, str):
            local_flags.append(f"--abbrev-ref={abbrev_ref}")
        if show_toplevel is True:
            local_flags.append("--show-toplevel")
        if git_dir is True:
            local_flags.append("--git-dir")

        cmd_args: list[str] = ["rev-parse", *local_flags]
        if args is not None:
            if isinstance(args, list):
                cmd_args.extend(args)
            else:
                cmd_args.append(args)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def symbolic_ref(
        self,
        *,
        name: str,
        ref: str | None = None,
        short: bool | None = None,
        quiet: bool | None = None,
        delete: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Read, modify, or delete symbolic refs asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.symbolic_ref`.

        Parameters
        ----------
        name : str
            Symbolic ref name
        ref : str, optional
            Ref to set symbolic ref to
        short : bool, optional
            Shorten ref name
        quiet : bool, optional
            Suppress error messages
        delete : bool, optional
            Delete symbolic ref
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Symbolic ref value
        """
        local_flags: list[str] = []
        if short is True:
            local_flags.append("--short")
        if quiet is True:
            local_flags.append("--quiet")
        if delete is True:
            local_flags.append("--delete")

        cmd_args: list[str] = ["symbolic-ref", *local_flags, name]
        if ref is not None:
            cmd_args.append(ref)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def rev_list(
        self,
        *,
        commit: str | list[str] | None = None,
        max_count: int | None = None,
        abbrev_commit: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """List commit objects asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.rev_list`.

        Parameters
        ----------
        commit : str | list[str], optional
            Commit(s) to list
        max_count : int, optional
            Limit output to n commits
        abbrev_commit : bool, optional
            Show abbreviated commit IDs
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            List of commit objects
        """
        local_flags: list[str] = []
        if max_count is not None:
            local_flags.extend(["--max-count", str(max_count)])
        if abbrev_commit is True:
            local_flags.append("--abbrev-commit")

        cmd_args: list[str] = ["rev-list", *local_flags]
        if commit is not None:
            if isinstance(commit, list):
                cmd_args.extend(commit)
            else:
                cmd_args.append(commit)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def show_ref(
        self,
        *,
        pattern: str | list[str] | None = None,
        heads: bool | None = None,
        tags: bool | None = None,
        hash_only: bool | None = None,
        verify: bool | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """List references asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.show_ref`.

        Parameters
        ----------
        pattern : str | list[str], optional
            Pattern(s) to filter refs
        heads : bool, optional
            Show only heads
        tags : bool, optional
            Show only tags
        hash_only : bool, optional
            Show only hash
        verify : bool, optional
            Verify ref exists
        quiet : bool, optional
            Suppress output (just exit status)
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Reference list
        """
        local_flags: list[str] = []
        if heads is True:
            local_flags.append("--heads")
        if tags is True:
            local_flags.append("--tags")
        if hash_only is True:
            local_flags.append("--hash")
        if verify is True:
            local_flags.append("--verify")
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["show-ref", *local_flags]
        if pattern is not None:
            if isinstance(pattern, list):
                cmd_args.extend(pattern)
            else:
                cmd_args.append(pattern)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def reset(
        self,
        *,
        pathspec: str | list[str] | None = None,
        soft: bool | None = None,
        mixed: bool | None = None,
        hard: bool | None = None,
        merge: bool | None = None,
        keep: bool | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Reset current HEAD asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.reset`.

        Parameters
        ----------
        pathspec : str | list[str], optional
            Commit or paths to reset
        soft : bool, optional
            Reset HEAD only
        mixed : bool, optional
            Reset HEAD and index (default)
        hard : bool, optional
            Reset HEAD, index, and working tree
        quiet : bool, optional
            Suppress output
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if soft is True:
            local_flags.append("--soft")
        if mixed is True:
            local_flags.append("--mixed")
        if hard is True:
            local_flags.append("--hard")
        if merge is True:
            local_flags.append("--merge")
        if keep is True:
            local_flags.append("--keep")
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["reset", *local_flags]
        if pathspec is not None:
            if isinstance(pathspec, list):
                cmd_args.extend(pathspec)
            else:
                cmd_args.append(pathspec)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def rebase(
        self,
        *,
        upstream: str | None = None,
        onto: str | None = None,
        abort: bool | None = None,
        _continue: bool | None = None,
        skip: bool | None = None,
        interactive: bool | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Rebase commits asynchronously.

        Async equivalent of :meth:`~libvcs.cmd.git.Git.rebase`.

        Parameters
        ----------
        upstream : str, optional
            Upstream branch to rebase onto
        onto : str, optional
            Starting point for rebase
        abort : bool, optional
            Abort current rebase
        _continue : bool, optional
            Continue current rebase
        skip : bool, optional
            Skip current patch
        interactive : bool, optional
            Interactive rebase (use with caution in async)
        quiet : bool, optional
            Suppress output
        timeout : float, optional
            Timeout in seconds

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if onto is not None:
            local_flags.extend(["--onto", onto])
        if abort is True:
            local_flags.append("--abort")
        if _continue is True:
            local_flags.append("--continue")
        if skip is True:
            local_flags.append("--skip")
        if interactive is True:
            local_flags.append("--interactive")
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["rebase", *local_flags]
        if upstream is not None:
            cmd_args.append(upstream)

        return await self.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def version(
        self,
        *,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Get git version asynchronously.

        Returns
        -------
        str
            Git version string
        """
        return await self.run(["version"], timeout=timeout, **kwargs)


class AsyncGitSubmoduleCmd:
    """Async git submodule commands.

    Async equivalent of :class:`~libvcs.cmd.git.GitSubmoduleCmd`.
    """

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: AsyncGit,
    ) -> None:
        """Initialize submodule command wrapper."""
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)
        self.cmd = cmd

    async def init(
        self,
        *,
        path: StrPath | list[StrPath] | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Initialize submodules asynchronously.

        Parameters
        ----------
        path : str | Path | list, optional
            Submodule path(s) to initialize

        Returns
        -------
        str
            Command output
        """
        cmd_args: list[str] = ["submodule", "init"]
        if path is not None:
            if isinstance(path, list):
                cmd_args.extend([str(p) for p in path])
            else:
                cmd_args.append(str(path))

        return await self.cmd.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def update(
        self,
        *,
        path: StrPath | list[StrPath] | None = None,
        init: bool | None = None,
        recursive: bool | None = None,
        force: bool | None = None,
        remote: bool | None = None,
        log_in_real_time: bool = False,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Update submodules asynchronously.

        Parameters
        ----------
        path : str | Path | list, optional
            Submodule path(s) to update
        init : bool, optional
            Initialize uninitialized submodules
        recursive : bool, optional
            Update nested submodules
        force : bool, optional
            Force checkout

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if init is True:
            local_flags.append("--init")
        if recursive is True:
            local_flags.append("--recursive")
        if force is True:
            local_flags.append("--force")
        if remote is True:
            local_flags.append("--remote")

        cmd_args: list[str] = ["submodule", "update", *local_flags]
        if path is not None:
            cmd_args.append("--")
            if isinstance(path, list):
                cmd_args.extend([str(p) for p in path])
            else:
                cmd_args.append(str(path))

        return await self.cmd.run(
            cmd_args,
            log_in_real_time=log_in_real_time,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )


class AsyncGitRemoteManager:
    """Async git remote management commands.

    Async equivalent of :class:`~libvcs.cmd.git.GitRemoteManager`.
    """

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: AsyncGit,
    ) -> None:
        """Initialize remote manager."""
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)
        self.cmd = cmd

    async def ls(
        self,
        *,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> list[str]:
        """List remote names asynchronously.

        Returns
        -------
        list[str]
            List of remote names
        """
        output = await self.cmd.run(["remote"], timeout=timeout, **kwargs)
        if not output.strip():
            return []
        return output.strip().split("\n")

    async def show(
        self,
        *,
        name: str | None = None,
        verbose: bool | None = None,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Show remotes asynchronously.

        Parameters
        ----------
        name : str, optional
            Remote name to show details for
        verbose : bool, optional
            Show URLs

        Returns
        -------
        str
            Remote information
        """
        local_flags: list[str] = []
        if verbose is True:
            local_flags.append("--verbose")

        cmd_args: list[str] = ["remote", *local_flags]
        if name is not None:
            cmd_args.extend(["show", name])

        return await self.cmd.run(cmd_args, timeout=timeout, **kwargs)

    async def add(
        self,
        *,
        name: str,
        url: str,
        fetch: bool | None = None,
        tags: bool | None = None,
        no_tags: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Add a remote asynchronously.

        Parameters
        ----------
        name : str
            Remote name
        url : str
            Remote URL
        fetch : bool, optional
            Fetch after adding
        tags : bool, optional
            Import tags
        no_tags : bool, optional
            Don't import tags

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if fetch is True:
            local_flags.append("--fetch")
        if tags is True:
            local_flags.append("--tags")
        if no_tags is True:
            local_flags.append("--no-tags")

        return await self.cmd.run(
            ["remote", "add", *local_flags, name, url],
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def remove(
        self,
        *,
        name: str,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Remove a remote asynchronously.

        Parameters
        ----------
        name : str
            Remote name to remove

        Returns
        -------
        str
            Command output
        """
        return await self.cmd.run(
            ["remote", "remove", name],
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def get_url(
        self,
        *,
        name: str,
        push: bool | None = None,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Get URL for a remote asynchronously.

        Parameters
        ----------
        name : str
            Remote name
        push : bool, optional
            Get push URL

        Returns
        -------
        str
            Remote URL
        """
        local_flags: list[str] = []
        if push is True:
            local_flags.append("--push")

        return await self.cmd.run(
            ["remote", "get-url", *local_flags, name],
            timeout=timeout,
            **kwargs,
        )


class AsyncGitStashCmd:
    """Async git stash commands.

    Async equivalent of :class:`~libvcs.cmd.git.GitStashCmd`.
    """

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: AsyncGit,
    ) -> None:
        """Initialize stash command wrapper."""
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)
        self.cmd = cmd

    async def ls(
        self,
        *,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """List stashes asynchronously.

        Returns
        -------
        str
            Stash list
        """
        return await self.cmd.run(["stash", "list"], timeout=timeout, **kwargs)

    async def save(
        self,
        *,
        message: str | None = None,
        keep_index: bool | None = None,
        include_untracked: bool | None = None,
        all_files: bool | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Save changes to stash asynchronously.

        Parameters
        ----------
        message : str, optional
            Stash message
        keep_index : bool, optional
            Keep staged changes in index
        include_untracked : bool, optional
            Include untracked files
        all_files : bool, optional
            Include ignored files too
        quiet : bool, optional
            Suppress output

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if keep_index is True:
            local_flags.append("--keep-index")
        if include_untracked is True:
            local_flags.append("--include-untracked")
        if all_files is True:
            local_flags.append("--all")
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["stash", "save", *local_flags]
        if message is not None:
            cmd_args.append(message)

        return await self.cmd.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def pop(
        self,
        *,
        stash: str | None = None,
        index: bool | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Pop stash asynchronously.

        Parameters
        ----------
        stash : str, optional
            Stash to pop (defaults to latest)
        index : bool, optional
            Also restore index
        quiet : bool, optional
            Suppress output

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if index is True:
            local_flags.append("--index")
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["stash", "pop", *local_flags]
        if stash is not None:
            cmd_args.append(stash)

        return await self.cmd.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def drop(
        self,
        *,
        stash: str | None = None,
        quiet: bool | None = None,
        check_returncode: bool = True,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Drop stash asynchronously.

        Parameters
        ----------
        stash : str, optional
            Stash to drop (defaults to latest)
        quiet : bool, optional
            Suppress output

        Returns
        -------
        str
            Command output
        """
        local_flags: list[str] = []
        if quiet is True:
            local_flags.append("--quiet")

        cmd_args: list[str] = ["stash", "drop", *local_flags]
        if stash is not None:
            cmd_args.append(stash)

        return await self.cmd.run(
            cmd_args,
            check_returncode=check_returncode,
            timeout=timeout,
            **kwargs,
        )

    async def clear(
        self,
        *,
        timeout: float | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Clear all stashes asynchronously.

        Returns
        -------
        str
            Command output
        """
        return await self.cmd.run(["stash", "clear"], timeout=timeout, **kwargs)
