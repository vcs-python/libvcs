"""Run git commands directly against a local git repo."""

from __future__ import annotations

import datetime
import pathlib
import re
import shlex
import string
import typing as t
from collections.abc import Sequence

from libvcs._internal.query_list import QueryList
from libvcs._internal.run import ProgressCallbackProtocol, run
from libvcs._internal.types import StrOrBytesPath, StrPath

_CMD = StrOrBytesPath | Sequence[StrOrBytesPath]


class Git:
    """Run commands directly on a git repository."""

    progress_callback: ProgressCallbackProtocol | None = None

    # Sub-commands
    submodule: GitSubmoduleCmd
    remote: GitRemoteManager
    stash: GitStashCmd  # Deprecated: use stashes
    stashes: GitStashManager
    branch: GitBranchManager
    tags: GitTagManager

    def __init__(
        self,
        *,
        path: StrPath,
        progress_callback: ProgressCallbackProtocol | None = None,
    ) -> None:
        r"""Lite, typed, pythonic wrapper for git(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)
        >>> git
        <Git path=...>

        Subcommands:

        >>> git.remotes.show()
        'origin'

        >>> git.remotes.add(
        ...     name='my_remote', url=f'file:///dev/null'
        ... )
        ''

        >>> git.remotes.show()
        'my_remote\norigin'

        >>> git.stash.save(message="Message")
        'No local changes to save'

        >>> git.submodule.init()
        ''

        # Additional tests
        >>> git.remotes.get(remote_name='my_remote').remove()
        ''
        >>> git.remotes.show()
        'origin'

        >>> git.stash.ls()
        ''

        >>> git.stashes.ls()
        []

        >>> git.tags.create(name='v1.0.0', message='Version 1.0.0')
        ''

        >>> any(t.tag_name == 'v1.0.0' for t in git.tags.ls())
        True
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.progress_callback = progress_callback

        self.submodule = GitSubmoduleCmd(path=self.path, cmd=self)
        self.remotes = GitRemoteManager(path=self.path, cmd=self)
        self.stash = GitStashCmd(path=self.path, cmd=self)  # Deprecated: use stashes
        self.stashes = GitStashManager(path=self.path, cmd=self)
        self.branches = GitBranchManager(path=self.path, cmd=self)
        self.tags = GitTagManager(path=self.path, cmd=self)

    def __repr__(self) -> str:
        """Representation of Git repo command object."""
        return f"<Git path={self.path}>"

    def run(
        self,
        args: _CMD,
        *,
        # Print-and-exit flags
        version: bool | None = None,
        _help: bool | None = None,
        html_path: bool | None = None,
        man_path: bool | None = None,
        info_path: bool | None = None,
        # Normal flags
        C: StrOrBytesPath | list[StrOrBytesPath] | None = None,
        cwd: StrOrBytesPath | None = None,
        git_dir: StrOrBytesPath | None = None,
        work_tree: StrOrBytesPath | None = None,
        namespace: StrOrBytesPath | None = None,
        super_prefix: StrOrBytesPath | None = None,
        exec_path: StrOrBytesPath | None = None,
        bare: bool | None = None,
        no_replace_objects: bool | None = None,
        literal_pathspecs: bool | None = None,
        global_pathspecs: bool | None = None,
        noglob_pathspecs: bool | None = None,
        icase_pathspecs: bool | None = None,
        no_optional_locks: bool | None = None,
        config: dict[str, t.Any] | None = None,
        config_env: str | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        **kwargs: t.Any,
    ) -> str:
        """Run a command for this git repository.

        Passing None to a subcommand option, the flag won't be passed unless otherwise
        stated.

        `git help` and `git help [cmd]`

        Wraps git's `Options <https://git-scm.com/docs/git#_options>`_.

        Parameters
        ----------
        cwd : :attr:`libvcs._internal.types.StrOrBytesPath`, optional, passed to
            subprocess's ``cwd`` the command runs from. Defaults to :attr:`~.cwd`.
        C : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``-C <path>``
        git_dir : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--git-dir <path>``
        work_tree : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--work-tree <path>``
        namespace : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--namespace <path>``
        super_prefix : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--super-prefix <path>``
        exec_path : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            ``--exec-path=<path>``
        bare : bool
            ``--bare``
        no_replace_objects : bool
            ``--no-replace-objects``
        literal_pathspecs : bool
            ``--literal-pathspecs``
        global_pathspecs : bool
            ``--glob-pathspecs``
        noglob_pathspecs : bool
            ``--noglob-pathspecs``
        icase_pathspecs : bool
            ``--icase-pathspecs``
        no_optional_locks : bool
            ``--no-optional-locks``
        version : bool
            ``--version``
        html_path : bool
            ``--html-path``
        man_path : bool
            ``--man-path``
        info_path : bool
            ``--info-path``
        _help : bool
            ``-h / --help``
        pager : bool
            ``-p --pager``
        no_pager : bool
            ``-P / --no-pager``
        config :
            ``--config=<name>=<value>``
        config_env :
            ``--config-env=<name>=<envvar>``

        Examples
        --------
        >>> git = Git(path=tmp_path)
        >>> git.run(['help'])
        "usage: git [...--version] [...--help] [-C <path>]..."
        """
        cli_args = ["git", *args] if isinstance(args, Sequence) else ["git", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.path

        #
        # Print-and-exit
        #
        if version is True:
            cli_args.append("--version")
        if _help is True:
            cli_args.append("--help")
        if html_path is True:
            cli_args.append("--html-path")
        if man_path is True:
            cli_args.append("--man-path")
        if info_path is True:
            cli_args.append("--info-path")

        #
        # Flags
        #
        if C is not None:
            if not isinstance(C, list):
                C = [C]
            C = [str(c) for c in C]
            cli_args.extend(["-C", C])
        if config is not None:
            assert isinstance(config, dict)

            def stringify(v: t.Any) -> str:
                if isinstance(v, bool):
                    return "true" if True else "false"
                if not isinstance(v, str):
                    return str(v)
                return v

            for k, v in config.items():
                cli_args.extend(["--config", f"{k}={stringify(v)}"])
        if git_dir is not None:
            cli_args.extend(["--git-dir", str(git_dir)])
        if work_tree is not None:
            cli_args.extend(["--work-tree", str(work_tree)])
        if namespace is not None:
            cli_args.extend(["--namespace", namespace])
        if super_prefix is not None:
            cli_args.extend(["--super-prefix", super_prefix])
        if exec_path is not None:
            cli_args.extend(["--exec-path", exec_path])
        if bare is True:
            cli_args.append("--bare")
        if no_replace_objects is True:
            cli_args.append("--no-replace-objects")
        if literal_pathspecs is True:
            cli_args.append("--literal-pathspecs")
        if global_pathspecs is True:
            cli_args.append("--global-pathspecs")
        if noglob_pathspecs is True:
            cli_args.append("--noglob-pathspecs")
        if icase_pathspecs is True:
            cli_args.append("--icase-pathspecs")
        if no_optional_locks is True:
            cli_args.append("--no-optional-locks")

        if self.progress_callback is not None:
            kwargs["callback"] = self.progress_callback

        return run(args=cli_args, **kwargs)

    def clone(
        self,
        *,
        url: str,
        separate_git_dir: StrOrBytesPath | None = None,
        template: str | None = None,
        depth: int | None = None,
        branch: str | None = None,
        origin: str | None = None,
        upload_pack: str | None = None,
        shallow_since: str | None = None,
        shallow_exclude: str | None = None,
        reference: str | None = None,
        reference_if_able: str | None = None,
        server_option: str | None = None,
        jobs: str | None = None,
        force: bool | None = None,
        local: bool | None = None,
        _all: bool | None = None,
        no_hardlinks: bool | None = None,
        hardlinks: bool | None = None,
        shared: bool | None = None,
        progress: bool | None = None,
        no_checkout: bool | None = None,
        no_reject_shallow: bool | None = None,
        reject_shallow: bool | None = None,
        sparse: bool | None = None,
        shallow_submodules: bool | None = None,
        no_shallow_submodules: bool | None = None,
        remote_submodules: bool | None = None,
        no_remote_submodules: bool | None = None,
        verbose: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run
        config: dict[str, t.Any] | None = None,
        log_in_real_time: bool = False,
        # Special behavior
        check_returncode: bool | None = None,
        make_parents: bool | None = True,
        **kwargs: t.Any,
    ) -> str:
        """Clone a working copy from an git repo.

        Wraps `git clone <https://git-scm.com/docs/git-clone>`_.

        Parameters
        ----------
        url : str
        directory : str
        separate_git_dir : StrOrBytesPath
            Separate repository (.git/ ) from working tree
        force : bool, optional
            force operation to run
        make_parents : bool, default: ``True``
            Creates checkout directory (`:attr:`self.path`) if it doesn't already exist.

        Examples
        --------
        >>> git = Git(path=tmp_path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.clone(url=f'file://{git_remote_repo}')
        ''
        >>> git.path.exists()
        True
        """
        required_flags: list[str] = [url, str(self.path)]
        local_flags: list[str] = []

        if template is not None:
            local_flags.append(f"--template={template}")
        if separate_git_dir is not None:
            local_flags.append(f"--separate-git-dir={separate_git_dir!r}")
        if (_filter := kwargs.pop("_filter", None)) is not None:
            local_flags.append(f"--filter={_filter}")
        if depth is not None:
            local_flags.extend(["--depth", str(depth)])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if origin is not None:
            local_flags.extend(["--origin", origin])
        if upload_pack is not None:
            local_flags.extend(["--upload-pack", upload_pack])
        if shallow_since is not None:
            local_flags.append(f"--shallow-since={shallow_since}")
        if shallow_exclude is not None:
            local_flags.append(f"--shallow-exclude={shallow_exclude}")
        if reference is not None:
            local_flags.extend(["--reference", reference])
        if reference_if_able is not None:
            local_flags.extend(["--reference", reference_if_able])
        if server_option is not None:
            local_flags.append(f"--server-option={server_option}")
        if jobs is not None:
            local_flags.extend(["--jobs", jobs])
        if local is True:
            local_flags.append("--local")
        if hardlinks is True:
            local_flags.append("--hardlinks")
        if no_hardlinks is True:
            local_flags.append("--no-hardlinks")
        if shared is True:
            local_flags.append("--shared")
        if quiet is True:
            local_flags.append("--quiet")
        if verbose is True:
            local_flags.append("--verbose")
        if progress is True:
            local_flags.append("--progress")
        if no_checkout is True:
            local_flags.append("--no-checkout")
        if no_reject_shallow is True:
            local_flags.append("--no-reject-shallow")
        if reject_shallow is True:
            local_flags.append("--reject-shallow")
        if sparse is True:
            local_flags.append("--sparse")
        if shallow_submodules is True:
            local_flags.append("--shallow-submodules")
        if no_shallow_submodules is True:
            local_flags.append("--no-shallow-submodules")
        if remote_submodules is True:
            local_flags.append("--remote-submodules")
        if no_remote_submodules is True:
            local_flags.append("--no-remote-submodules")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)
        return self.run(
            ["clone", *local_flags, "--", *required_flags],
            config=config,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def fetch(
        self,
        *,
        reftag: t.Any | None = None,
        deepen: str | None = None,
        depth: str | None = None,
        branch: str | None = None,
        origin: str | None = None,
        upload_pack: str | None = None,
        shallow_since: str | None = None,
        shallow_exclude: str | None = None,
        negotiation_tip: str | None = None,
        jobs: str | None = None,
        server_option: str | None = None,
        recurse_submodules: bool | t.Literal["yes", "on-demand", "no"] | None = None,
        recurse_submodules_default: bool | t.Literal["yes", "on-demand"] | None = None,
        submodule_prefix: StrOrBytesPath | None = None,
        _all: bool | None = None,
        force: bool | None = None,
        keep: bool | None = None,
        multiple: bool | None = None,
        dry_run: bool | None = None,
        append: bool | None = None,
        atomic: bool | None = None,
        ipv4: bool | None = None,
        ipv6: bool | None = None,
        progress: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        unshallow: bool | None = None,
        update_shallow: bool | None = None,
        negotiate_tip: bool | None = None,
        no_write_fetch_head: bool | None = None,
        write_fetch_head: bool | None = None,
        no_auto_maintenance: bool | None = None,
        auto_maintenance: bool | None = None,
        no_write_commit_graph: bool | None = None,
        write_commit_graph: bool | None = None,
        prefetch: bool | None = None,
        prune: bool | None = None,
        prune_tags: bool | None = None,
        no_tags: bool | None = None,
        tags: bool | None = None,
        no_recurse_submodules: bool | None = None,
        set_upstream: bool | None = None,
        update_head_ok: bool | None = None,
        show_forced_updates: bool | None = None,
        no_show_forced_updates: bool | None = None,
        negotiate_only: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Download from repo. Wraps `git fetch <https://git-scm.com/docs/git-fetch>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.fetch()
        ''
        >>> git = Git(path=example_git_repo.path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.fetch(reftag=f'file://{git_remote_repo}')
        ''
        >>> git.path.exists()
        True
        """
        required_flags: list[str] = []
        if reftag:
            required_flags.insert(0, reftag)
        local_flags: list[str] = []

        if submodule_prefix is not None:
            local_flags.append(f"--submodule-prefix={submodule_prefix!r}")
        if (_filter := kwargs.pop("_filter", None)) is not None:
            local_flags.append(f"--filter={_filter}")
        if depth is not None:
            local_flags.extend(["--depth", depth])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if origin is not None:
            local_flags.extend(["--origin", origin])
        if upload_pack is not None:
            local_flags.extend(["--upload-pack", upload_pack])
        if shallow_since is not None:
            local_flags.append(f"--shallow-since={shallow_since}")
        if shallow_exclude is not None:
            local_flags.append(f"--shallow-exclude={shallow_exclude}")
        if server_option is not None:
            local_flags.append(f"--server-option={server_option}")
        if jobs is not None:
            local_flags.extend(["--jobs", jobs])
        if keep:
            local_flags.append("--keep")
        if force:
            local_flags.append("--force")
        if multiple:
            local_flags.append("--multiple")
        if quiet:
            local_flags.append("--quiet")
        if progress:
            local_flags.append("--progress")
        if verbose:
            local_flags.append("--verbose")
        if _all:
            local_flags.append("--all")
        if atomic:
            local_flags.append("--atomic")
        if unshallow:
            local_flags.append("--unshallow")
        if append:
            local_flags.append("--append")
        if update_shallow:
            local_flags.append("--update-shallow")
        if dry_run:
            local_flags.append("--dry-run")
        if no_write_fetch_head:
            local_flags.append("--no-write-fetch-head")
        if write_fetch_head:
            local_flags.append("--write-fetch-head")
        if auto_maintenance:
            local_flags.append("--auto-maintenance")
        if no_auto_maintenance:
            local_flags.append("--no-auto-maintenance")
        if write_commit_graph:
            local_flags.append("--write-commit-graph")
        if no_write_commit_graph:
            local_flags.append("--no-write-commit-graph")
        if prefetch:
            local_flags.append("--prefetch")
        if prune:
            local_flags.append("--prune")
        if prune_tags:
            local_flags.append("--prune-tags")
        if tags:
            local_flags.append("--tags")
        if no_tags:
            local_flags.append("--no-tags")
        if no_recurse_submodules:
            local_flags.append("--no-recurse-submodules")
        if set_upstream:
            local_flags.append("--set-upstream")
        if update_head_ok:
            local_flags.append("--update-head-ok")
        if show_forced_updates:
            local_flags.append("--show-forced-updates")
        if no_show_forced_updates:
            local_flags.append("--no-show-forced-updates")
        if negotiate_only:
            local_flags.append("--negotiate-only")
        return self.run(
            ["fetch", *local_flags, "--", *required_flags],
            check_returncode=check_returncode,
        )

    def rebase(
        self,
        *,
        upstream: str | None = None,
        onto: str | None = None,
        branch: str | None = None,
        apply: bool | None = None,
        merge: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        stat: bool | None = None,
        no_stat: bool | None = None,
        verify: bool | None = None,
        no_verify: bool | None = None,
        fork_point: bool | None = None,
        no_fork_point: bool | None = None,
        whitespace: str | None = None,
        no_whitespace: bool | None = None,
        commit_date_is_author_date: bool | None = None,
        ignore_date: bool | None = None,
        root: bool | None = None,
        autostash: bool | None = None,
        no_autostash: bool | None = None,
        autosquash: bool | None = None,
        no_autosquash: bool | None = None,
        reschedule_failed_exec: bool | None = None,
        no_reschedule_failed_exec: bool | None = None,
        context: int | None = None,
        rerere_autoupdate: bool | None = None,
        no_rerere_autoupdate: bool | None = None,
        keep_empty: bool | None = None,
        no_keep_empty: bool | None = None,
        reapply_cherry_picks: bool | None = None,
        no_reapply_cherry_picks: bool | None = None,
        allow_empty_message: bool | None = None,
        signoff: bool | None = None,
        keep_base: bool | None = None,
        strategy: str | bool | None = None,
        strategy_option: str | None = None,
        _exec: str | None = None,
        gpg_sign: str | bool | None = None,
        no_gpg_sign: bool | None = None,
        empty: str | t.Literal["drop", "keep", "ask"] | None = None,
        rebase_merges: str
        | t.Literal["rebase-cousins", "no-rebase-cousins"]
        | None = None,
        #
        # Interactive
        #
        interactive: bool | None = None,
        edit_todo: bool | None = None,
        skip: bool | None = None,
        show_current_patch: bool | None = None,
        abort: bool | None = None,
        _quit: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Reapply commit on top of another tip.

        Wraps `git rebase <https://git-scm.com/docs/git-rebase>`_.

        Parameters
        ----------
        continue : bool
            Accepted via kwargs

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.rebase()
        'Current branch master is up to date.'

        Declare upstream:

        >>> git = Git(path=example_git_repo.path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.rebase(upstream='origin')
        'Current branch master is up to date.'
        >>> git.path.exists()
        True
        """
        required_flags: list[str] = []
        local_flags: list[str] = []

        if upstream:
            required_flags.insert(0, upstream)
        if branch:
            required_flags.insert(0, branch)
        if onto:
            local_flags.extend(["--onto", onto])
        if context:
            local_flags.extend(["--C", str(context)])

        if _exec:
            local_flags.extend(["--exec", shlex.quote(_exec)])
        if reschedule_failed_exec:
            local_flags.append("--reschedule-failed-exec")
        if no_reschedule_failed_exec:
            local_flags.append("--no-reschedule-failed-exec")
        if fork_point:
            local_flags.append("--fork-point")
        if no_fork_point:
            local_flags.append("--no-fork-point")
        if root:
            local_flags.append("--root")
        if keep_base:
            local_flags.append("--keep-base")
        if autostash:
            local_flags.append("--autostash")
        if no_autostash:
            local_flags.append("--no-autostash")

        if merge:
            local_flags.append("--merge")

        if verbose:
            local_flags.append("--verbose")
        if quiet:
            local_flags.append("--quiet")
        if stat:
            local_flags.append("--stat")
        if no_stat:
            local_flags.append("--no-stat")

        if whitespace:
            local_flags.append("--whitespace")
        if no_whitespace:
            local_flags.append("--no-whitespace")

        if rerere_autoupdate:
            local_flags.append("--rerere-autoupdate")
        if no_rerere_autoupdate:
            local_flags.append("--no-rerwre-autoupdate")

        if reapply_cherry_picks:
            local_flags.append("--reapply-cherry-picks")
        if no_reapply_cherry_picks:
            local_flags.append("--no-reapply-cherry-picks")

        if keep_empty:
            local_flags.append("--keep-empty")
        if no_keep_empty:
            local_flags.append("--no-keep-empty")

        if verify:
            local_flags.append("--verify")
        if no_verify:
            local_flags.append("--no-verify")

        if ignore_date:
            local_flags.append("--ignore-date")
        if commit_date_is_author_date:
            local_flags.append("--commit-date-is-author-date")

        if empty is not None:
            if isinstance(empty, str):
                local_flags.append(f"--empty={empty}")
            else:
                local_flags.append("--empty")

        if rebase_merges is not None:
            if isinstance(rebase_merges, str):
                local_flags.append(f"--rebase-merges={rebase_merges}")
            else:
                local_flags.append("--rebase-merges")

        if gpg_sign is not None:
            if isinstance(gpg_sign, str):
                local_flags.append(f"--gpg-sign={gpg_sign}")
            else:
                local_flags.append("--gpg-sign")
        if no_gpg_sign:
            local_flags.append("--no-gpg-sign")
        if signoff:
            local_flags.append("--signoff")

        #
        # Interactive
        #
        if interactive:
            local_flags.append("--interactive")
        if kwargs.get("continue"):
            local_flags.append("--continue")
        if abort:
            local_flags.append("--abort")
        if edit_todo:
            local_flags.append("--edit-todo")
        if show_current_patch:
            local_flags.append("--show-current-patch")
        if _quit:
            local_flags.append("--quit")

        return self.run(
            ["rebase", *local_flags, *required_flags],
            check_returncode=check_returncode,
        )

    def pull(
        self,
        *,
        reftag: t.Any | None = None,
        repository: str | None = None,
        deepen: str | None = None,
        depth: str | None = None,
        branch: str | None = None,
        origin: str | None = None,
        upload_pack: str | None = None,
        shallow_since: str | None = None,
        shallow_exclude: str | None = None,
        negotiation_tip: str | None = None,
        jobs: str | None = None,
        server_option: str | None = None,
        recurse_submodules: bool | t.Literal["yes", "on-demand", "no"] | None = None,
        recurse_submodules_default: bool | t.Literal["yes", "on-demand"] | None = None,
        submodule_prefix: StrOrBytesPath | None = None,
        #
        # Pull specific flags
        #
        # Options related to git pull
        # https://git-scm.com/docs/git-pull#_options_related_to_pull
        #
        cleanup: str | None = None,
        rebase: str | bool | None = None,
        no_rebase: bool | None = None,
        strategy: str | bool | None = None,
        strategy_option: str | None = None,
        gpg_sign: str | bool | None = None,
        no_gpg_sign: bool | None = None,
        commit: bool | None = None,
        no_commit: bool | None = None,
        edit: bool | None = None,
        no_edit: bool | None = None,
        fast_forward_only: bool | None = None,
        fast_forward: bool | None = None,
        no_fast_forward: bool | None = None,
        sign_off: bool | None = None,
        no_sign_off: bool | None = None,
        stat: bool | None = None,
        no_stat: bool | None = None,
        squash: bool | None = None,
        no_squash: bool | None = None,
        verify: bool | None = None,
        no_verify: bool | None = None,
        verify_signatures: bool | None = None,
        no_verify_signatures: bool | None = None,
        summary: bool | None = None,
        no_summary: bool | None = None,
        autostash: bool | None = None,
        no_autostash: bool | None = None,
        allow_unrelated_histories: bool | None = None,
        #
        # Options related to git fetch
        # https://git-scm.com/docs/git-pull#_options_related_to_fetching
        #
        fetch: bool | None = None,
        no_fetch: bool | None = None,
        _all: bool | None = None,
        force: bool | None = None,
        keep: bool | None = None,
        multiple: bool | None = None,
        dry_run: bool | None = None,
        append: bool | None = None,
        atomic: bool | None = None,
        ipv4: bool | None = None,
        ipv6: bool | None = None,
        progress: bool | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        unshallow: bool | None = None,
        update_shallow: bool | None = None,
        negotiate_tip: bool | None = None,
        no_write_fetch_head: bool | None = None,
        write_fetch_head: bool | None = None,
        no_auto_maintenance: bool | None = None,
        auto_maintenance: bool | None = None,
        no_write_commit_graph: bool | None = None,
        write_commit_graph: bool | None = None,
        prefetch: bool | None = None,
        prune: bool | None = None,
        prune_tags: bool | None = None,
        no_tags: bool | None = None,
        tags: bool | None = None,
        no_recurse_submodules: bool | None = None,
        set_upstream: bool | None = None,
        update_head_ok: bool | None = None,
        show_forced_updates: bool | None = None,
        no_show_forced_updates: bool | None = None,
        negotiate_only: bool | None = None,
        # Pass-through to run
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Download from repo. Wraps `git pull <https://git-scm.com/docs/git-pull>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.pull()
        'Already up to date.'

        Fetch via ref:

        >>> git = Git(path=tmp_path)
        >>> git.run(['init'])
        'Initialized ...'
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.pull(reftag=f'file://{git_remote_repo}')
        ''
        >>> git.path.exists()
        True
        """
        required_flags: list[str] = []
        if repository:
            required_flags.insert(0, repository)
        if reftag:
            required_flags.insert(0, reftag)
        local_flags: list[str] = []

        #
        # Pull-related arguments
        #
        if rebase is not None:
            if isinstance(rebase, str):
                local_flags.append(f"--rebase={rebase}")
            else:
                local_flags.append("--rebase")
        if no_rebase:
            local_flags.append("--no-rebase")
        if strategy is not None:
            if isinstance(strategy, str):
                local_flags.append(f"--strategy={strategy}")
            else:
                local_flags.append("--strategy")
        if strategy_option is not None:
            local_flags.append(f"--strategy-option={strategy_option}")
        if gpg_sign is not None:
            if isinstance(gpg_sign, str):
                local_flags.append(f"--gpg-sign={gpg_sign}")
            else:
                local_flags.append("--gpg-sign")
        if no_gpg_sign:
            local_flags.append("--no-gpg-sign")
        if cleanup:
            local_flags.append("--cleanup")
        if commit:
            local_flags.append("--commit")
        if no_commit:
            local_flags.append("--no-commit")
        if fast_forward:
            local_flags.append("--fast-forward")
        if fast_forward_only:
            local_flags.append("--fast-forward-only")
        if no_fast_forward:
            local_flags.append("--no-fast-forward")
        if edit:
            local_flags.append("--edit")
        if no_edit:
            local_flags.append("--no-edit")
        if sign_off:
            local_flags.append("--sign_off")
        if no_sign_off:
            local_flags.append("--no-sign_off")
        if stat:
            local_flags.append("--stat")
        if no_stat:
            local_flags.append("--no-stat")
        if squash:
            local_flags.append("--squash")
        if no_squash:
            local_flags.append("--no-squash")
        if verify:
            local_flags.append("--verify")
        if no_verify:
            local_flags.append("--no-verify")
        if verify_signatures:
            local_flags.append("--verify-signatures")
        if no_verify_signatures:
            local_flags.append("--no-verify-signatures")
        if summary:
            local_flags.append("--summary")
        if no_summary:
            local_flags.append("--no-summary")
        if autostash:
            local_flags.append("--autostash")
        if no_autostash:
            local_flags.append("--no-autostash")
        if allow_unrelated_histories:
            local_flags.append("--allow-unrelated-histories")
        #
        # Fetch-related arguments
        #
        if submodule_prefix is not None:
            local_flags.append(f"--submodule-prefix={submodule_prefix!r}")
        if (_filter := kwargs.pop("_filter", None)) is not None:
            local_flags.append(f"--filter={_filter}")
        if depth is not None:
            local_flags.extend(["--depth", depth])
        if branch is not None:
            local_flags.extend(["--branch", branch])
        if origin is not None:
            local_flags.extend(["--origin", origin])
        if upload_pack is not None:
            local_flags.extend(["--upload-pack", upload_pack])
        if shallow_since is not None:
            local_flags.append(f"--shallow-since={shallow_since}")
        if shallow_exclude is not None:
            local_flags.append(f"--shallow-exclude={shallow_exclude}")
        if server_option is not None:
            local_flags.append(f"--server-option={server_option}")
        if jobs is not None:
            local_flags.extend(["--jobs", jobs])
        if keep:
            local_flags.append("--keep")
        if force:
            local_flags.append("--force")
        if multiple:
            local_flags.append("--multiple")
        if quiet:
            local_flags.append("--quiet")
        if progress:
            local_flags.append("--progress")
        if verbose:
            local_flags.append("--verbose")
        if _all:
            local_flags.append("--all")
        if atomic:
            local_flags.append("--atomic")
        if unshallow:
            local_flags.append("--unshallow")
        if append:
            local_flags.append("--append")
        if update_shallow:
            local_flags.append("--update-shallow")
        if dry_run:
            local_flags.append("--dry-run")
        if no_write_fetch_head:
            local_flags.append("--no-write-fetch-head")
        if write_fetch_head:
            local_flags.append("--write-fetch-head")
        if auto_maintenance:
            local_flags.append("--auto-maintenance")
        if no_auto_maintenance:
            local_flags.append("--no-auto-maintenance")
        if write_commit_graph:
            local_flags.append("--write-commit-graph")
        if no_write_commit_graph:
            local_flags.append("--no-write-commit-graph")
        if prefetch:
            local_flags.append("--prefetch")
        if prune:
            local_flags.append("--prune")
        if prune_tags:
            local_flags.append("--prune-tags")
        if tags:
            local_flags.append("--tags")
        if no_tags:
            local_flags.append("--no-tags")
        if no_recurse_submodules:
            local_flags.append("--no-recurse-submodules")
        if set_upstream:
            local_flags.append("--set-upstream")
        if update_head_ok:
            local_flags.append("--update-head-ok")
        if show_forced_updates:
            local_flags.append("--show-forced-updates")
        if no_show_forced_updates:
            local_flags.append("--no-show-forced-updates")
        if negotiate_only:
            local_flags.append("--negotiate-only")
        return self.run(
            ["pull", *local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def init(
        self,
        *,
        template: str | pathlib.Path | None = None,
        separate_git_dir: StrOrBytesPath | None = None,
        object_format: t.Literal["sha1", "sha256"] | None = None,
        branch: str | None = None,
        initial_branch: str | None = None,
        shared: bool
        | t.Literal["false", "true", "umask", "group", "all", "world", "everybody"]
        | str  # Octal number string (e.g., "0660")
        | None = None,
        quiet: bool | None = None,
        bare: bool | None = None,
        ref_format: t.Literal["files", "reftable"] | None = None,
        default: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        make_parents: bool = True,
        **kwargs: t.Any,
    ) -> str:
        """Create empty repo. Wraps `git init <https://git-scm.com/docs/git-init>`_.

        Parameters
        ----------
        template : str | pathlib.Path, optional
            Directory from which templates will be used. The template directory
            contains files and directories that will be copied to the $GIT_DIR
            after it is created. The template directory will be one of the
            following (in order):
            - The argument given with the --template option
            - The contents of the $GIT_TEMPLATE_DIR environment variable
            - The init.templateDir configuration variable
            - The default template directory: /usr/share/git-core/templates
        separate_git_dir : :attr:`libvcs._internal.types.StrOrBytesPath`, optional
            Instead of placing the git repository in <directory>/.git/, place it in
            the specified path. The .git file at <directory>/.git will contain a
            gitfile that points to the separate git dir. This is useful when you
            want to store the git directory on a different disk or filesystem.
        object_format : "sha1" | "sha256", optional
            Specify the hash algorithm to use. The default is sha1. Note that
            sha256 is still experimental in git and requires git version >= 2.29.0.
            Once the repository is created with a specific hash algorithm, it cannot
            be changed.
        branch : str, optional
            Use the specified name for the initial branch. If not specified, fall
            back to the default name (currently "master", but may change based on
            init.defaultBranch configuration).
        initial_branch : str, optional
            Alias for branch parameter. Specify the name for the initial branch.
            This is provided for compatibility with newer git versions.
        shared : bool | str, optional
            Specify that the git repository is to be shared amongst several users.
            Valid values are:
            - false: Turn off sharing (default)
            - true: Same as group
            - umask: Use permissions specified by umask
            - group: Make the repository group-writable
            - all, world, everybody: Same as world, make repo readable by all users
            - An octal number string: Explicit mode specification (e.g., "0660")
        quiet : bool, optional
            Only print error and warning messages; all other output will be
            suppressed. Useful for scripting.
        bare : bool, optional
            Create a bare repository. If GIT_DIR environment is not set, it is set
            to the current working directory. Bare repositories have no working
            tree and are typically used as central repositories.
        ref_format : "files" | "reftable", optional
            Specify the reference storage format. Requires git version >= 2.37.0.
            - files: Classic format with packed-refs and loose refs (default)
            - reftable: New format that is more efficient for large repositories
        default : bool, optional
            Use default permissions for directories and files. This is the same as
            running git init without any options.
        check_returncode : bool, optional
            If True, check the return code of the git command and raise a
            CalledProcessError if it is non-zero.
        make_parents : bool, default: True
            If True, create the target directory if it doesn't exist. If False,
            raise an error if the directory doesn't exist.

        Returns
        -------
        str
            The output of the git init command.

        Raises
        ------
        CalledProcessError
            If the git command fails and check_returncode is True.
        ValueError
            If invalid parameters are provided.
        FileNotFoundError
            If make_parents is False and the target directory doesn't exist.

        Examples
        --------
        >>> git = Git(path=tmp_path)
        >>> git.init()
        'Initialized empty Git repository in ...'

        Create with a specific initial branch name:

        >>> new_repo = tmp_path / 'branch_example'
        >>> new_repo.mkdir()
        >>> git = Git(path=new_repo)
        >>> git.init(branch='main')
        'Initialized empty Git repository in ...'

        Create a bare repository:

        >>> bare_repo = tmp_path / 'bare_example'
        >>> bare_repo.mkdir()
        >>> git = Git(path=bare_repo)
        >>> git.init(bare=True)
        'Initialized empty Git repository in ...'

        Create with a separate git directory:

        >>> repo_path = tmp_path / 'repo'
        >>> git_dir = tmp_path / 'git_dir'
        >>> repo_path.mkdir()
        >>> git_dir.mkdir()
        >>> git = Git(path=repo_path)
        >>> git.init(separate_git_dir=str(git_dir.absolute()))
        'Initialized empty Git repository in ...'

        Create with shared permissions:

        >>> shared_repo = tmp_path / 'shared_example'
        >>> shared_repo.mkdir()
        >>> git = Git(path=shared_repo)
        >>> git.init(shared='group')
        'Initialized empty shared Git repository in ...'

        Create with octal permissions:

        >>> shared_repo = tmp_path / 'shared_octal_example'
        >>> shared_repo.mkdir()
        >>> git = Git(path=shared_repo)
        >>> git.init(shared='0660')
        'Initialized empty shared Git repository in ...'

        Create with a template directory:

        >>> template_repo = tmp_path / 'template_example'
        >>> template_repo.mkdir()
        >>> git = Git(path=template_repo)
        >>> git.init(template=str(tmp_path))
        'Initialized empty Git repository in ...'

        Create with SHA-256 object format (requires git >= 2.29.0):

        >>> sha256_repo = tmp_path / 'sha256_example'
        >>> sha256_repo.mkdir()
        >>> git = Git(path=sha256_repo)
        >>> git.init(object_format='sha256')  # doctest: +SKIP
        'Initialized empty Git repository in ...'
        """
        local_flags: list[str] = []
        required_flags: list[str] = [str(self.path)]

        if template is not None:
            if not isinstance(template, (str, pathlib.Path)):
                msg = "template must be a string or Path"
                raise TypeError(msg)
            template_path = pathlib.Path(template)
            if not template_path.is_dir():
                msg = f"template directory does not exist: {template}"
                raise ValueError(msg)
            local_flags.append(f"--template={template}")

        if separate_git_dir is not None:
            if isinstance(separate_git_dir, pathlib.Path):
                separate_git_dir = str(separate_git_dir.absolute())
            local_flags.append(f"--separate-git-dir={separate_git_dir!s}")

        if object_format is not None:
            if object_format not in {"sha1", "sha256"}:
                msg = "object_format must be either 'sha1' or 'sha256'"
                raise ValueError(msg)
            local_flags.append(f"--object-format={object_format}")

        if branch is not None and initial_branch is not None:
            msg = "Cannot specify both branch and initial_branch"
            raise ValueError(msg)

        branch_name = branch or initial_branch
        if branch_name is not None:
            if any(c.isspace() for c in branch_name):
                msg = "Branch name cannot contain whitespace"
                raise ValueError(msg)
            local_flags.extend(["--initial-branch", branch_name])

        if shared is not None:
            valid_shared_values = {
                "false",
                "true",
                "umask",
                "group",
                "all",
                "world",
                "everybody",
            }
            if isinstance(shared, bool):
                local_flags.append("--shared")
            else:
                shared_str = str(shared).lower()
                # Check if it's a valid string value or an octal number
                if not (
                    shared_str in valid_shared_values
                    or (
                        shared_str.isdigit()
                        and len(shared_str) <= 4
                        and all(c in string.octdigits for c in shared_str)
                        and int(shared_str, 8) <= 0o777  # Validate octal range
                    )
                ):
                    msg = (
                        f"Invalid shared value. Must be one of {valid_shared_values} "
                        "or a valid octal number between 0000 and 0777"
                    )
                    raise ValueError(msg)
                local_flags.append(f"--shared={shared}")

        if quiet is True:
            local_flags.append("--quiet")
        if bare is True:
            local_flags.append("--bare")
        if ref_format is not None:
            local_flags.append(f"--ref-format={ref_format}")
        if default is True:
            local_flags.append("--default")

        # libvcs special behavior
        if make_parents and not self.path.exists():
            self.path.mkdir(parents=True)
        elif not self.path.exists():
            msg = f"Directory does not exist: {self.path}"
            raise FileNotFoundError(msg)

        return self.run(
            ["init", *local_flags, "--", *required_flags],
            check_returncode=check_returncode,
        )

    def help(
        self,
        *,
        _all: bool | None = None,
        verbose: bool | None = None,
        no_external_commands: bool | None = None,
        no_aliases: bool | None = None,
        config: bool | None = None,
        guides: bool | None = None,
        info: bool | None = None,
        man: bool | None = None,
        web: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Help info. Wraps `git help <https://git-scm.com/docs/git-help>`_.

        Parameters
        ----------
        _all : bool
            Prints everything.

        no_external_commands : bool
            For use with ``all``, excludes external commands.

        no_aliases : bool
            For use with ``all``, excludes aliases.

        verbose : bool
            For us with ``all``, on by default.

        config : bool
            List all config vars.

        guides : bool
            List concept guides.

        info : bool
            Display man page in info format.

        man : bool
            Man page.

        web : bool
            Man page in HTML.

        Examples
        --------
        >>> git = Git(path=tmp_path)

        >>> git.help()
        "usage: git [...--version] [...--help] [-C <path>]..."

        >>> git.help(_all=True)
        "See 'git help <command>' to read about a specific subcommand..."

        >>> git.help(info=True)
        "usage: git [...--version] [...--help] [-C <path>] [-c <name>=<value>]..."

        >>> git.help(man=True)
        "usage: git [...--version] [...--help] [-C <path>] [-c <name>=<value>]..."
        """
        local_flags: list[str] = []

        if verbose is True:
            local_flags.append("--verbose")
        if _all is True:
            local_flags.append("--all")
        if no_external_commands is True:
            local_flags.append("--no-external-commands")
        if no_aliases is True:
            local_flags.append("--no-aliases")
        if config is True:
            local_flags.append("--config")
        if guides is True:
            local_flags.append("--guides")
        if info is True:
            local_flags.append("--info")
        if man is True:
            local_flags.append("--man")
        if web is True:
            local_flags.append("--web")

        return self.run(["help", *local_flags], check_returncode=check_returncode)

    def reset(
        self,
        *,
        quiet: bool | None = None,
        refresh: bool | None = None,
        no_refresh: bool | None = None,
        pathspec_from_file: StrOrBytesPath | None = None,
        pathspec: StrOrBytesPath | list[StrOrBytesPath] | None = None,
        soft: bool | None = None,
        mixed: bool | None = None,
        hard: bool | None = None,
        merge: bool | None = None,
        keep: bool | None = None,
        commit: str | None = None,
        recurse_submodules: bool | None = None,
        no_recurse_submodules: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Reset HEAD. Wraps `git help <https://git-scm.com/docs/git-help>`_.

        Parameters
        ----------
        quiet : bool
        no_refresh : bool
        refresh : bool
        pathspec_from_file : :attr:`libvcs._internal.types.StrOrBytesPath`
        pathspec_file_nul : bool
        pathspec : :attr:`libvcs._internal.types.StrOrBytesPath` or list
            :attr:`libvcs._internal.types.StrOrBytesPath`
        soft : bool
        mixed : bool
        hard : bool
        merge : bool
        keep : bool
        commit : str

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.reset()
        ''

        >>> git.reset(soft=True, commit='HEAD~0')
        ''
        """
        local_flags: list[str] = []

        if quiet is True:
            local_flags.append("--quiet")
        if no_refresh is True:
            local_flags.append("--no-refresh")
        if refresh is True:
            local_flags.append("--refresh")
        if pathspec_from_file is not None:
            local_flags.append(f"--pathspec_from_file={pathspec_from_file!r}")

        # HEAD to commit form
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

        if commit is not None:
            local_flags.append(commit)

        if recurse_submodules:
            local_flags.append("--recurse-submodules")
        elif no_recurse_submodules:
            local_flags.append("--no-recurse-submodules")

        if pathspec is not None:
            if not isinstance(pathspec, list):
                pathspec = [pathspec]
        else:
            pathspec = []

        return self.run(
            ["reset", *local_flags, *(["--", *pathspec] if pathspec else [])],
            check_returncode=check_returncode,
        )

    def checkout(
        self,
        *,
        quiet: bool | None = None,
        progress: bool | None = None,
        no_progress: bool | None = None,
        pathspec_from_file: StrOrBytesPath | None = None,
        pathspec: StrOrBytesPath | list[StrOrBytesPath] | None = None,
        force: bool | None = None,
        ours: bool | None = None,
        theirs: bool | None = None,
        no_track: bool | None = None,
        guess: bool | None = None,
        no_guess: bool | None = None,
        _list: bool | None = None,
        detach: bool | None = None,
        merge: bool | None = None,
        ignore_skip_worktree_bits: bool | None = None,
        patch: bool | None = None,
        orphan: str | None = None,
        conflict: str | None = None,
        overwrite_ignore: bool | None = None,
        no_overwrite_ignore: bool | None = None,
        recurse_submodules: bool | None = None,
        no_recurse_submodules: bool | None = None,
        overlay: bool | None = None,
        no_overlay: bool | None = None,
        commit: str | None = None,
        branch: str | None = None,
        new_branch: str | None = None,
        start_point: str | None = None,
        treeish: str | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Switch branches or checks out files.

        Wraps `git checkout <https://git-scm.com/docs/git-checkout>`_ (`git co`).

        Parameters
        ----------
        quiet : bool
        progress : bool
        no_progress : bool
        pathspec_from_file : :attr:`libvcs._internal.types.StrOrBytesPath`
        pathspec : :attr:`libvcs._internal.types.StrOrBytesPath` or list
            :attr:`libvcs._internal.types.StrOrBytesPath`
        force : bool
        ours : bool
        theirs : bool
        no_track : bool
        guess : bool
        no_guess : bool
        ignore_skip_worktree_bits : bool
        merge : bool
        _list : bool
        detach : bool
        patch : bool
        orphan : bool
        conflict : str
        overwrite_ignore : bool
        no_overwrite_ignore : bool
        commit : str
        branch : str
        new_branch : str
        start_point : str
        treeish : str

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.checkout()
        "Your branch is up to date with 'origin/master'."

        >>> git.checkout(branch='origin/master', pathspec='.')
        ''
        """
        local_flags: list[str] = []

        if quiet is True:
            local_flags.append("--quiet")
        if progress is True:
            local_flags.append("--progress")
        elif no_progress is True:
            local_flags.append("--no-progress")

        if force is True:
            local_flags.append("--force")

        if ours is True:
            local_flags.append("--ours")

        if theirs is True:
            local_flags.append("--theirs")

        if detach is True:
            local_flags.append("--detach")

        if orphan is not None:
            local_flags.append("--orphan")

        if conflict is not None:
            local_flags.append(f"--conflict={conflict}")

        if commit is not None:
            local_flags.append(commit)

        if branch is not None:
            local_flags.append(branch)

        if new_branch is not None:
            local_flags.append(new_branch)

        if start_point is not None:
            local_flags.append(start_point)

        if treeish is not None:
            local_flags.append(treeish)

        if recurse_submodules:
            local_flags.append("--recurse-submodules")
        elif no_recurse_submodules:
            local_flags.append("--no-recurse-submodules")

        if pathspec is not None:
            if not isinstance(pathspec, list):
                pathspec = [pathspec]
        else:
            pathspec = []

        return self.run(
            ["checkout", *local_flags, *(["--", *pathspec] if pathspec else [])],
            check_returncode=check_returncode,
        )

    def status(
        self,
        *,
        verbose: bool | None = None,
        long: bool | None = None,
        short: bool | None = None,
        branch: bool | None = None,
        z: bool | None = None,
        column: bool | str | None = None,
        no_column: bool | None = None,
        ahead_behind: bool | None = None,
        no_ahead_behind: bool | None = None,
        renames: bool | None = None,
        no_renames: bool | None = None,
        find_renames: bool | str | None = None,
        porcelain: bool | str | None = None,
        untracked_files: t.Literal["no", "normal", "all"] | None = None,
        ignored: t.Literal["traditional", "no", "matching"] | None = None,
        ignored_submodules: t.Literal["untracked", "dirty", "all"] | None = None,
        pathspec: StrOrBytesPath | list[StrOrBytesPath] | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Return status of working tree.

        Wraps `git status <https://git-scm.com/docs/git-status>`_.

        `git ls-files` has similar params (e.g. `z`)

        Parameters
        ----------
        verbose : bool
        long : bool
        short : bool
        branch : bool
        z : bool
        column : bool
        no_column : bool
        ahead_behind : bool
        no_ahead_behind : bool
        find_renames : bool
        no_find_renames : bool
        porcelain : str, bool
        untracked_files : "no", "normal", "all"
        ignored : "traditional", "no", "matching"
        ignored_submodules : "untracked", "dirty", "all"
        pathspec : :attr:`libvcs._internal.types.StrOrBytesPath` or list
            :attr:`libvcs._internal.types.StrOrBytesPath`

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.status()
        "On branch master..."

        >>> pathlib.Path(example_git_repo.path / 'new_file.txt').touch()

        >>> git.status(porcelain=True)
        '?? new_file.txt'

        >>> git.status(porcelain='1')
        '?? new_file.txt'

        >>> git.status(porcelain='2')
        '? new_file.txt'

        >>> git.status(C=example_git_repo.path / '.git', porcelain='2')
        '? new_file.txt'

        >>> git.status(porcelain=True, untracked_files="no")
        ''
        """
        local_flags: list[str] = []

        if verbose is True:
            local_flags.append("--verbose")

        if long is True:
            local_flags.append("--long")

        if short is True:
            local_flags.append("--short")

        if branch is True:
            local_flags.append("--branch")

        if z is True:
            local_flags.append("--z")

        if untracked_files is not None and isinstance(untracked_files, str):
            local_flags.append(f"--untracked-files={untracked_files}")

        if ignored is not None and isinstance(column, str):
            local_flags.append(f"--ignored={ignored}")

        if ignored_submodules is not None:
            if isinstance(column, str):
                local_flags.append(f"--ignored-submodules={ignored_submodules}")
            else:
                local_flags.append("--ignored-submodules")

        if column is not None:
            if isinstance(column, str):
                local_flags.append(f"--column={column}")
            else:
                local_flags.append("--column")
        elif no_column is not None:
            local_flags.append("--no-column")

        if porcelain is not None:
            if isinstance(porcelain, str):
                local_flags.append(f"--porcelain={porcelain}")
            else:
                local_flags.append("--porcelain")

        if find_renames is True:
            if isinstance(find_renames, str):
                local_flags.append(f"--find-renames={find_renames}")
            else:
                local_flags.append("--find-renames")

        if pathspec is not None:
            if not isinstance(pathspec, list):
                pathspec = [pathspec]
        else:
            pathspec = []

        return self.run(
            ["status", *local_flags, *(["--", *pathspec] if pathspec else [])],
            check_returncode=check_returncode,
        )

    def config(
        self,
        *,
        replace_all: bool | None = None,
        get: str | None = None,
        get_all: bool | None = None,
        get_regexp: str | None = None,
        get_urlmatch: tuple[str, str] | None = None,
        system: bool | None = None,
        local: bool | None = None,
        worktree: bool | None = None,
        file: StrOrBytesPath | None = None,
        blob: str | None = None,
        remove_section: bool | None = None,
        rename_section: bool | None = None,
        unset: bool | None = None,
        unset_all: bool | None = None,
        _list: bool | None = None,
        fixed_value: bool | None = None,
        no_type: bool | None = None,
        null: bool | None = None,
        name_only: bool | None = None,
        show_origin: bool | None = None,
        show_scope: bool | None = None,
        get_color: str | bool | None = None,
        get_colorbool: str | bool | None = None,
        default: bool | None = None,
        _type: t.Literal["bool", "int", "bool-or-int", "path", "expiry-date", "color"]
        | None = None,
        edit: bool | None = None,
        no_includes: bool | None = None,
        includes: bool | None = None,
        add: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Get and set repo configuration.

        `git config <https://git-scm.com/docs/git-config>`_.

        Parameters
        ----------
        replace_all : Optional[bool]
        get : Optional[bool]
        get_all : Optional[bool]
        get_regexp : Optional[bool]
        get_urlmatch : Optional[tuple[str, str]]
        system : Optional[bool]
        local : Optional[bool]
        worktree : Optional[bool]
        file : Optional[StrOrBytesPath]
        blob : Optional[str]
        remove_section : Optional[bool]
        rename_section : Optional[bool]
        unset : Optional[bool]
        unset_all : Optional[bool]
        _list : Optional[bool]
        fixed_value : Optional[bool]
        no_type : Optional[bool]
        null : Optional[bool]
        name_only : Optional[bool]
        show_origin : Optional[bool]
        show_scope : Optional[bool]
        get_color : Optional[t.Union[str, bool]]
        get_colorbool : Optional[t.Union[str, bool]]
        default : Optional[str]
        _type : "bool", "int", "bool-or-int", "path", "expiry-date", "color"
        edit : Optional[bool]
        no_includes : Optional[bool]
        includes : Optional[bool]
        add : Optional[bool]

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.config()
        '...: ...'

        >>> git.config(_list=True)
        '...user.email=...'

        >>> git.config(get='color.diff')
        'auto'
        """
        local_flags: list[str] = []

        if replace_all is True:
            local_flags.append("--replace-all")

        if get is not None and isinstance(get, str):
            local_flags.extend(["--get", get])

        if get_regexp is not None and isinstance(get_regexp, str):
            local_flags.extend(["--get-regexp", get_regexp])

        if get_all is not None and isinstance(get_all, str):
            local_flags.extend(["--get-all", get_all])

        if get_urlmatch is not None and isinstance(get_urlmatch, tuple):
            local_flags.extend(["--get-urlmatch=", *get_urlmatch])

        if unset is not None and isinstance(unset, str):
            local_flags.extend(["--unset", unset])

        if unset_all is not None and isinstance(unset_all, str):
            local_flags.extend(["--unset-all", unset_all])

        if _list is True:
            local_flags.append("--list")

        if fixed_value is True:
            local_flags.append("--fixed-value")

        if no_type is True:
            local_flags.append("--no-type")

        if null is True:
            local_flags.append("--null")

        if name_only is True:
            local_flags.append("--name-only")

        if show_origin is True:
            local_flags.append("--show-origin")

        if show_scope is True:
            local_flags.append("--show-scope")

        if edit is True:
            local_flags.append("--edit")

        if system is True:
            local_flags.append("--system")

        if local is True:
            local_flags.append("--local")

        if worktree is True:
            local_flags.append("--worktree")

        if remove_section is True:
            local_flags.append("--remove-section")

        if rename_section is True:
            local_flags.append("--rename-section")

        if _type is not None and isinstance(_type, str):
            local_flags.extend(["--type", _type])

        if blob is not None and isinstance(blob, str):
            local_flags.extend(["--blob", blob])

        if file is not None:
            local_flags.extend(["--file", str(file)])

        if default is True:
            local_flags.append("--default")

        if includes is True:
            local_flags.append("--includes")

        if no_includes is True:
            local_flags.append("--no-includes")

        if add is True:
            local_flags.append("--add")

        if get_colorbool is not None:
            if isinstance(get_colorbool, str):
                local_flags.extend(["--get-colorbool", get_colorbool])
            else:
                local_flags.append("--get-colorbool")

        if get_color is not None:
            if isinstance(get_color, str):
                local_flags.extend(["--get-color", get_color])
            else:
                local_flags.append("--get-color")

        return self.run(
            ["config", *local_flags],
            check_returncode=check_returncode,
        )

    def version(
        self,
        *,
        build_options: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Version. Wraps `git version <https://git-scm.com/docs/git-version>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.version()
        'git version ...'

        >>> git.version(build_options=True)
        'git version ...'
        """
        local_flags: list[str] = []

        if build_options is True:
            local_flags.append("--build-options")

        return self.run(
            ["version", *local_flags],
            check_returncode=check_returncode,
        )

    def rev_parse(
        self,
        *,
        parseopt: bool | None = None,
        sq_quote: bool | None = None,
        keep_dashdash: bool | None = None,
        stop_at_non_option: bool | None = None,
        stuck_long: bool | None = None,
        verify: bool | None = None,
        args: str | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """rev-parse. Wraps `git rev-parse <https://git-scm.com/docs/rev-parse>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.rev_parse()
        ''

        >>> git.rev_parse(parseopt=True)
        'usage: git rev-parse --parseopt...'

        >>> git.rev_parse(verify=True, args='HEAD')
        '...'
        """
        local_flags: list[str] = []

        if parseopt is True:
            local_flags.append("--parseopt")

            if keep_dashdash is True:
                local_flags.append("--keep-dashdash")
            if stop_at_non_option is True:
                local_flags.append("--stop-at-non-option")
            if stuck_long is True:
                local_flags.append("--stuck-long")
        if sq_quote is True:
            local_flags.append("--sq-quote")
        if verify is True:
            local_flags.append("--verify")

        if parseopt is True:
            if args is not None:
                local_flags.extend(["--", args])
        elif args is not None:
            local_flags.append(args)

        return self.run(
            ["rev-parse", *local_flags],
            check_returncode=check_returncode,
        )

    def rev_list(
        self,
        *,
        commit: list[str] | str | None,
        path: list[StrPath] | StrPath | None = None,
        #
        # Limiting
        #
        max_count: int | None = None,
        skip: int | None = None,
        since: str | None = None,
        after: str | None = None,
        until: str | None = None,
        before: str | None = None,
        max_age: str | None = None,
        min_age: str | None = None,
        author: str | None = None,
        committer: str | None = None,
        grep: str | None = None,
        all_match: bool | None = None,
        invert_grep: bool | None = None,
        regexp_ignore_case: bool | None = None,
        basic_regexp: bool | None = None,
        extended_regexp: bool | None = None,
        fixed_strings: bool | None = None,
        perl_regexp: bool | None = None,
        remove_empty: bool | None = None,
        merges: bool | None = None,
        no_merges: bool | None = None,
        no_min_parents: bool | None = None,
        min_parents: int | None = None,
        no_max_parents: bool | None = None,
        max_parents: int | None = None,
        first_parent: bool | None = None,
        exclude_first_parent_only: bool | None = None,
        _not: bool | None = None,
        _all: bool | None = None,
        branches: str | bool | None = None,
        tags: str | bool | None = None,
        remotes: str | bool | None = None,
        exclude: bool | None = None,
        reflog: bool | None = None,
        alternative_refs: bool | None = None,
        single_worktree: bool | None = None,
        ignore_missing: bool | None = None,
        stdin: bool | None = None,
        disk_usage: bool | str | None = None,
        cherry_mark: bool | None = None,
        cherry_pick: bool | None = None,
        left_only: bool | None = None,
        right_only: bool | None = None,
        cherry: bool | None = None,
        walk_reflogs: bool | None = None,
        merge: bool | None = None,
        boundary: bool | None = None,
        use_bitmap_index: bool | None = None,
        progress: str | bool | None = None,
        # Formatting
        #
        # --parents
        # --children
        # --objects | --objects-edge
        # --disk-usage[=human]
        # --unpacked
        # --header | --pretty
        # --[no-]object-names
        # --abbrev=<n> | --no-abbrev
        # --abbrev-commit
        # --left-right
        # --count
        header: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = True,
        log_in_real_time: bool = False,
        **kwargs: t.Any,
    ) -> str:
        """rev-list. Wraps `git rev-list <https://git-scm.com/docs/rev-list>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.rev_list(commit="HEAD")
        '...'

        >>> git.run(['commit', '--allow-empty', '--message=Moo'])
        '[master ...] Moo'

        >>> git.rev_list(commit="HEAD", max_count=1)
        '...'

        >>> git.rev_list(commit="HEAD", path=".", max_count=1, header=True)
        '...'

        >>> git.rev_list(commit="origin..HEAD", max_count=1, _all=True, header=True)
        '...'

        >>> git.rev_list(commit="origin..HEAD", max_count=1, header=True)
        '...'
        """
        required_flags: list[str] = []
        path_flags: list[str] = []
        local_flags: list[str] = []

        if isinstance(commit, str):
            required_flags.append(commit)
        if isinstance(commit, list):
            required_flags.extend(commit)

        if isinstance(path, str):
            path_flags.append(path)
        if isinstance(path, list):
            path_flags.extend(str(pathlib.Path(p).absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            path_flags.append(str(pathlib.Path(path).absolute()))

        for kwarg, kwarg_shell_flag in [
            (branches, "--branches"),
            (tags, "--tags"),
            (remotes, "--remotes"),
            (disk_usage, "--disk-usage"),
            (progress, "--progress"),
        ]:
            if kwarg is not None:
                if isinstance(kwarg, str):
                    local_flags.extend([kwarg_shell_flag, kwarg])
                elif kwarg:
                    local_flags.append(kwarg_shell_flag)

        for datetime_kwarg, datetime_shell_flag in [  # 1.year.ago
            (since, "--since"),
            (after, "--after"),
            (until, "--until"),
            (before, "--before"),
            (max_age, "--max-age"),
            (min_age, "--min-age"),
        ]:
            if datetime_kwarg is not None and isinstance(datetime, str):
                local_flags.extend([datetime_shell_flag, datetime_kwarg])

        for int_flag, int_shell_flag in [
            (max_count, "--max-count"),
            (skip, "--skip"),
            (min_parents, "--min-parents"),
            (max_parents, "--max-parents"),
        ]:
            if int_flag is not None:
                local_flags.extend([int_shell_flag, str(int_flag)])

        for flag, shell_flag in [
            # Limiting output
            (all, "--all"),
            (author, "--author"),
            (committer, "--committer"),
            (grep, "--grep"),
            (all_match, "--all-match"),
            (invert_grep, "--invert-grep"),
            (regexp_ignore_case, "--regexp-ignore-case"),
            (basic_regexp, "--basic-regexp"),
            (extended_regexp, "--extended-regexp"),
            (fixed_strings, "--fixed-strings"),
            (perl_regexp, "--perl-regexp"),
            (remove_empty, "--remove-empty"),
            (merges, "--merges"),
            (no_merges, "--no-merges"),
            (no_min_parents, "--no-min-parents"),
            (no_max_parents, "--no-max-parents"),
            (first_parent, "--first-parent"),
            (exclude_first_parent_only, "--exclude-first-parent-only"),
            (_not, "--not"),
            (all, "--all"),
            (exclude, "--exclude"),
            (reflog, "--reflog"),
            (alternative_refs, "--alternative-refs"),
            (single_worktree, "--single-worktree"),
            (ignore_missing, "--ignore-missing"),
            (stdin, "--stdin"),
            (cherry_mark, "--cherry-mark"),
            (cherry_pick, "--cherry-pick"),
            (left_only, "--left-only"),
            (right_only, "--right-only"),
            (cherry, "--cherry"),
            (walk_reflogs, "--walk-reflogs"),
            (merge, "--merge"),
            (boundary, "--boundary"),
            (use_bitmap_index, "--use-bitmap-index"),
            # Formatting outputs
            (header, "--header"),
        ]:
            if flag is not None and flag:
                local_flags.append(shell_flag)

        return self.run(
            [
                "rev-list",
                *local_flags,
                *required_flags,
                *(["--", *path_flags] if path_flags else []),
            ],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def symbolic_ref(
        self,
        *,
        name: str,
        ref: str | None = None,
        message: str | None = None,
        short: bool | None = None,
        delete: bool | None = None,
        quiet: bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Return symbolic-ref.

        Wraps `git symbolic-ref <https://git-scm.com/docs/symbolic-ref>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.symbolic_ref(name="test")
        'fatal: ref test is not a symbolic ref'

        >>> git.symbolic_ref(name="test")
        'fatal: ref test is not a symbolic ref'
        """
        required_flags: list[str] = [name]
        local_flags: list[str] = []

        if message is not None and isinstance(message, str):
            local_flags.extend(["-m", message])

        if delete is True:
            local_flags.append("--delete")
        if short is True:
            local_flags.append("--short")
        if quiet is True:
            local_flags.append("--quiet")

        return self.run(
            ["symbolic-ref", *required_flags, *local_flags],
            check_returncode=check_returncode,
        )

    def show_ref(
        self,
        *,
        pattern: list[str] | str | None = None,
        quiet: bool | None = None,
        verify: bool | None = None,
        head: bool | None = None,
        dereference: bool | None = None,
        tags: bool | None = None,
        _hash: str | bool | None = None,
        abbrev: str | bool | None = None,
        # libvcs special behavior
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        r"""show-ref. Wraps `git show-ref <https://git-scm.com/docs/git-show-ref>`_.

        Examples
        --------
        >>> git = Git(path=example_git_repo.path)

        >>> git.show_ref()
        '...'

        >>> git.show_ref(pattern='master')
        '...'

        >>> git.show_ref(pattern='master', head=True)
        '...'

        >>> git.show_ref(pattern='HEAD', verify=True)
        '... HEAD'

        >>> git.show_ref(pattern='master', dereference=True)
        '... refs/heads/master\n... refs/remotes/origin/master'

        >>> git.show_ref(pattern='HEAD', tags=True)
        ''
        """
        local_flags: list[str] = []
        pattern_flags: list[str] = []

        if pattern is not None:
            if isinstance(pattern, str):
                pattern_flags.append(pattern)
            elif isinstance(pattern, list):
                pattern_flags.extend(pattern)

        for kwarg, kwarg_shell_flag in [
            (_hash, "--hash"),
            (abbrev, "--abbrev"),
        ]:
            if kwarg is not None:
                if isinstance(kwarg, str):
                    local_flags.extend([kwarg_shell_flag, kwarg])
                elif kwarg:
                    local_flags.append(kwarg_shell_flag)

        for flag, shell_flag in [
            (quiet, "--quiet"),
            (verify, "--verify"),
            (head, "--head"),
            (dereference, "--dereference"),
            (tags, "--tags"),
        ]:
            if flag is not None and flag:
                local_flags.append(shell_flag)

        return self.run(
            [
                "show-ref",
                *local_flags,
                *(["--", *pattern_flags] if pattern_flags else []),
            ],
            check_returncode=check_returncode,
        )


GitSubmoduleCmdCommandLiteral = t.Literal[
    "status",
    "init",
    "deinit",
    "update",
    "set-branch",
    "set-url",
    "summary",
    "foreach",
    "sync",
    "absorbgitdirs",
]


class GitSubmoduleCmd:
    """Run submodule commands in a git repository."""

    def __init__(self, *, path: StrPath, cmd: Git | None = None) -> None:
        """Lite, typed, pythonic wrapper for git-submodule(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitSubmoduleCmd(path=tmp_path)
        <GitSubmoduleCmd path=...>

        >>> GitSubmoduleCmd(path=tmp_path).run(quiet=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitSubmoduleCmd(path=example_git_repo.path).run(quiet=True)
        ''
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of a git submodule command object."""
        return f"<GitSubmoduleCmd path={self.path}>"

    def run(
        self,
        command: GitSubmoduleCmdCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        quiet: bool | None = None,
        cached: bool | None = None,  # Only when no command entered and status
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git submodule.

        Wraps `git submodule <https://git-scm.com/docs/git-submodule>`_.

        Examples
        --------
        >>> GitSubmoduleCmd(path=example_git_repo.path).run()
        ''
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if quiet is True:
            local_flags.append("--quiet")
        if cached is True:
            local_flags.append("--cached")

        return self.cmd.run(
            ["submodule", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def init(
        self,
        *,
        path: list[StrPath] | StrPath | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git submodule init.

        Examples
        --------
        >>> GitSubmoduleCmd(path=example_git_repo.path).init()
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if isinstance(path, list):
            required_flags.extend(str(pathlib.Path(p).absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            required_flags.append(str(pathlib.Path(path).absolute()))

        return self.run(
            "init",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def update(
        self,
        *,
        path: list[StrPath] | StrPath | None = None,
        init: bool | None = None,
        force: bool | None = None,
        checkout: bool | None = None,
        rebase: bool | None = None,
        merge: bool | None = None,
        recursive: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Git submodule update.

        Examples
        --------
        >>> GitSubmoduleCmd(path=example_git_repo.path).update()
        ''
        >>> GitSubmoduleCmd(path=example_git_repo.path).update(init=True)
        ''
        >>> GitSubmoduleCmd(
        ...     path=example_git_repo.path
        ... ).update(init=True, recursive=True)
        ''
        >>> GitSubmoduleCmd(path=example_git_repo.path).update(force=True)
        ''
        >>> GitSubmoduleCmd(path=example_git_repo.path).update(checkout=True)
        ''
        >>> GitSubmoduleCmd(path=example_git_repo.path).update(rebase=True)
        ''
        >>> GitSubmoduleCmd(path=example_git_repo.path).update(merge=True)
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if isinstance(path, list):
            required_flags.extend(str(pathlib.Path(p).absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            required_flags.append(str(pathlib.Path(path).absolute()))

        if init is True:
            local_flags.append("--init")
        if force is True:
            local_flags.append("--force")

        if checkout is True:
            local_flags.append("--checkout")
        elif rebase is True:
            local_flags.append("--rebase")
        elif merge is True:
            local_flags.append("--merge")
        if (_filter := kwargs.pop("_filter", None)) is not None:
            local_flags.append(f"--filter={_filter}")

        return self.run(
            "update",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


GitRemoteCommandLiteral = t.Literal[
    "add",
    "rename",
    "remove",
    "set-branches",
    "set-head",
    "set-branch",
    "get-url",
    "set-url",
    "set-url --add",
    "set-url --delete",
    "prune",
    "show",
    "update",
]


class GitRemoteCmd:
    """Run commands directly for a git remote on a git repository."""

    remote_name: str
    fetch_url: str | None
    push_url: str | None

    def __init__(
        self,
        *,
        path: StrPath,
        remote_name: str,
        fetch_url: str | None = None,
        push_url: str | None = None,
        cmd: Git | None = None,
    ) -> None:
        r"""Lite, typed, pythonic wrapper for git-remote(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.
        remote_name :
            Name of remote

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... )
        <GitRemoteCmd path=... remote_name=...>

        >>> GitRemoteCmd(
        ...     path=tmp_path,
        ...     remote_name='origin',
        ... ).run(verbose=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... ).run(verbose=True)
        'origin\tfile:///...'
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

        self.remote_name = remote_name
        self.fetch_url = fetch_url
        self.push_url = push_url

    def __repr__(self) -> str:
        """Representation of a git remote for a git repository."""
        return f"<GitRemoteCmd path={self.path} remote_name={self.remote_name}>"

    def run(
        self,
        command: GitRemoteCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        verbose: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        r"""Run command against a git remote.

        Wraps `git remote <https://git-scm.com/docs/git-remote>`_.

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='master',
        ... ).run()
        'origin'
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='master',
        ... ).run(verbose=True)
        'origin\tfile:///...'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if verbose is True:
            local_flags.append("--verbose")

        return self.cmd.run(
            ["remote", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def rename(
        self,
        *,
        old: str,
        new: str,
        progress: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote rename.

        Examples
        --------
        >>> git_remote_repo = create_git_remote_repo()
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... ).rename(old='origin', new='new_name')
        ''
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... ).run()
        'new_name'
        """
        local_flags: list[str] = []
        required_flags: list[str] = [old, new]

        if progress is not None:
            if progress:
                local_flags.append("--progress")
            else:
                local_flags.append("--no-progress")
        return self.run(
            "rename",
            local_flags=local_flags + required_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def remove(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote remove.

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... ).remove()
        ''
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin',
        ... ).run()
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = [self.remote_name]

        return self.run(
            "remove",
            local_flags=local_flags + required_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def show(
        self,
        *,
        verbose: bool | None = None,
        no_query_remotes: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote show.

        Examples
        --------
        >>> print(
        ...     GitRemoteCmd(
        ...         path=example_git_repo.path,
        ...         remote_name='origin',
        ...     ).show()
        ... )
        * remote origin
        Fetch URL: ...
        Push  URL: ...
        HEAD branch: master
        Remote branch:
        master tracked...
        """
        local_flags: list[str] = []
        required_flags: list[str] = [self.remote_name]

        if verbose is not None:
            local_flags.append("--verbose")

        if no_query_remotes is not None or no_query_remotes:
            local_flags.append("-n")

        return self.run(
            "show",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def prune(
        self,
        *,
        dry_run: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote prune.

        Examples
        --------
        >>> git_remote_repo = create_git_remote_repo()
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).prune()
        ''

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).prune(dry_run=True)
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = [self.remote_name]

        if dry_run:
            local_flags.append("--dry-run")

        return self.run(
            "prune",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def get_url(
        self,
        *,
        push: bool | None = None,
        _all: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote get-url.

        Examples
        --------
        >>> git_remote_repo = create_git_remote_repo()
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).get_url()
        'file:///...'

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).get_url(push=True)
        'file:///...'

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).get_url(_all=True)
        'file:///...'
        """
        local_flags: list[str] = []
        required_flags: list[str] = [self.remote_name]

        if push:
            local_flags.append("--push")
        if _all:
            local_flags.append("--all")

        return self.run(
            "get-url",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def set_url(
        self,
        *,
        url: str,
        old_url: str | None = None,
        push: bool | None = None,
        add: bool | None = None,
        delete: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote set-url.

        Examples
        --------
        >>> git_remote_repo = create_git_remote_repo()
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_url(
        ...     url='http://localhost'
        ... )
        ''

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_url(
        ...     url='http://localhost',
        ...     push=True
        ... )
        ''

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_url(
        ...     url='http://localhost',
        ...     add=True
        ... )
        ''

        >>> current_url = GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).get_url()
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_url(
        ...     url=current_url,
        ...     delete=True
        ... )
        'fatal: Will not delete all non-push URLs'

        """
        local_flags: list[str] = []
        required_flags: list[str] = [self.remote_name, url]
        if old_url is not None:
            required_flags.append(old_url)

        if push:
            local_flags.append("--push")
        if add:
            local_flags.append("--add")
        if delete:
            local_flags.append("--delete")

        return self.run(
            "set-url",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def set_branches(
        self,
        *branches: str,
        add: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote set-branches.

        Configure remote tracking branches for the remote.

        Parameters
        ----------
        *branches :
            Branch names to track.
        add :
            Add to existing tracked branches instead of replacing.

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_branches('master')
        ''

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_branches('master', 'develop', add=True)
        ''
        """
        local_flags: list[str] = []

        if add:
            local_flags.append("--add")

        local_flags.append(self.remote_name)
        local_flags.extend(branches)

        return self.run(
            "set-branches",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def set_head(
        self,
        branch: str | None = None,
        *,
        auto: bool = False,
        delete: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote set-head.

        Set or delete the default branch (HEAD) for the remote.

        Parameters
        ----------
        branch :
            Branch name to set as HEAD. Required unless auto or delete is True.
        auto :
            Query the remote to determine HEAD automatically.
        delete :
            Delete the remote HEAD reference.

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_head(auto=True)
        'origin/HEAD set to master'

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).set_head('master')
        ''
        """
        local_flags: list[str] = [self.remote_name]

        if auto:
            local_flags.append("-a")
        elif delete:
            local_flags.append("-d")
        elif branch is not None:
            local_flags.append(branch)

        return self.run(
            "set-head",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def update(
        self,
        *,
        prune: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote update.

        Fetch updates for the remote.

        Parameters
        ----------
        prune :
            Prune remote-tracking branches no longer on remote.

        Examples
        --------
        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).update()
        'Fetching origin...'

        >>> GitRemoteCmd(
        ...     path=example_git_repo.path,
        ...     remote_name='origin'
        ... ).update(prune=True)
        'Fetching origin...'
        """
        local_flags: list[str] = []

        if prune:
            local_flags.append("-p")

        local_flags.append(self.remote_name)

        return self.run(
            "update",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


GitRemoteManagerLiteral = t.Literal[
    "--verbose",
    "add",
    "rename",
    "remove",
    "set-branches",
    "set-head",
    "set-branch",
    "get-url",
    "set-url",
    "set-url --add",
    "set-url --delete",
    "prune",
    "show",
    "update",
]


class GitRemoteManager:
    """Run commands directly related to git remotes of a git repo."""

    remote_name: str

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: Git | None = None,
    ) -> None:
        """Wrap some of git-remote(1), git-checkout(1), manager.

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitRemoteManager(path=tmp_path)
        <GitRemoteManager path=...>

        >>> GitRemoteManager(path=tmp_path).run(quiet=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitRemoteManager(
        ...     path=example_git_repo.path
        ... ).run()
        'origin'
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of git remote manager object."""
        return f"<GitRemoteManager path={self.path}>"

    def run(
        self,
        command: GitRemoteManagerLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's remotes.

        Wraps `git remote <https://git-scm.com/docs/git-remote>`_.

        Examples
        --------
        >>> GitRemoteManager(path=example_git_repo.path).run()
        'origin'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        return self.cmd.run(
            ["remote", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def add(
        self,
        *,
        name: str,
        url: str,
        fetch: bool | None = None,
        track: str | None = None,
        master: str | None = None,
        mirror: t.Literal["push", "fetch"] | bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote add.

        Examples
        --------
        >>> git_remote_repo = create_git_remote_repo()
        >>> GitRemoteManager(path=example_git_repo.path).add(
        ...     name='my_remote',
        ...     url=f'file://{git_remote_repo}'
        ... )
        ''
        """
        local_flags: list[str] = []
        required_flags: list[str] = [name, url]

        if mirror is not None:
            if isinstance(mirror, str):
                assert any(f for f in ["push", "fetch"])
                local_flags.extend(["--mirror", mirror])
            if isinstance(mirror, bool) and mirror:
                local_flags.append("--mirror")
        return self.run(
            "add",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def show(
        self,
        *,
        name: str | None = None,
        verbose: bool | None = None,
        no_query_remotes: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git remote show.

        Examples
        --------
        >>> GitRemoteManager(path=example_git_repo.path).show()
        'origin'

        For the example below, add a remote:
        >>> GitRemoteManager(path=example_git_repo.path).add(
        ...     name='my_remote', url=f'file:///dev/null'
        ... )
        ''

        Retrieve a list of remote names:
        >>> GitRemoteManager(path=example_git_repo.path).show().splitlines()
        ['my_remote', 'origin']
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if name is not None:
            required_flags.append(name)

        if verbose is not None:
            local_flags.append("--verbose")

        if no_query_remotes is not None or no_query_remotes:
            local_flags.append("-n")

        return self.run(
            "show",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def _ls(self) -> str:
        r"""List remotes (raw output).

        Examples
        --------
        >>> GitRemoteManager(path=example_git_repo.path)._ls()
        'origin\tfile:///... (fetch)\norigin\tfile:///... (push)'
        """
        return self.run(
            "--verbose",
        )

    def ls(self) -> QueryList[GitRemoteCmd]:
        """List remotes.

        Examples
        --------
        >>> GitRemoteManager(path=example_git_repo.path).ls()
        [<GitRemoteCmd path=... remote_name=origin>]

        For the example below, add a remote:
        >>> GitRemoteManager(path=example_git_repo.path).add(
        ...     name='my_remote', url=f'file:///dev/null'
        ... )
        ''

        >>> GitRemoteManager(path=example_git_repo.path).ls()
        [<GitRemoteCmd path=... remote_name=my_remote>,
         <GitRemoteCmd path=... remote_name=origin>]
        """
        remote_str = self._ls()
        remote_pattern = re.compile(
            r"""
            (?P<name>\S+)           # Remote name: one or more non-whitespace characters
            \s+                     # One or more whitespace characters
            (?P<url>\S+)            # URL: one or more non-whitespace characters
            \s+                     # One or more whitespace characters
            \((?P<cmd_type>fetch|push)\)  # 'fetch' or 'push' in parentheses
        """,
            re.VERBOSE | re.MULTILINE,
        )

        remotes: dict[str, dict[str, str | None]] = {}

        for match_obj in remote_pattern.finditer(remote_str):
            name = match_obj.group("name")
            url = match_obj.group("url")
            cmd_type = match_obj.group("cmd_type")

            if name not in remotes:
                remotes[name] = {}

            remotes[name][cmd_type] = url

        remote_cmds: list[GitRemoteCmd] = []
        for name, urls in remotes.items():
            fetch_url = urls.get("fetch")
            push_url = urls.get("push")
            remote_cmds.append(
                GitRemoteCmd(
                    path=self.path,
                    remote_name=name,
                    fetch_url=fetch_url,
                    push_url=push_url,
                ),
            )

        return QueryList(remote_cmds)

    def get(self, *args: t.Any, **kwargs: t.Any) -> GitRemoteCmd | None:
        """Get remote via filter lookup.

        Examples
        --------
        >>> GitRemoteManager(
        ...     path=example_git_repo.path
        ... ).get(remote_name='origin')
        <GitRemoteCmd path=... remote_name=origin>

        >>> GitRemoteManager(
        ...     path=example_git_repo.path
        ... ).get(remote_name='unknown')
        Traceback (most recent call last):
            exec(compile(example.source, filename, "single",
            ...
            return self.ls().get(*args, **kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "..._internal/query_list.py", line ..., in get
            raise ObjectDoesNotExist
        libvcs._internal.query_list.ObjectDoesNotExist
        """
        return self.ls().get(*args, **kwargs)

    def filter(self, *args: t.Any, **kwargs: t.Any) -> list[GitRemoteCmd]:
        """Get remotes via filter lookup.

        Examples
        --------
        >>> GitRemoteManager(
        ...     path=example_git_repo.path
        ... ).filter(remote_name__contains='origin')
        [<GitRemoteCmd path=... remote_name=origin>]

        >>> GitRemoteManager(
        ...     path=example_git_repo.path
        ... ).filter(remote_name__contains='unknown')
        []
        """
        return self.ls().filter(*args, **kwargs)


GitStashCommandLiteral = t.Literal[
    "list",
    "show",
    "save",
    "drop",
    "branch",
    "pop",
    "apply",
    "push",
    "clear",
    "create",
    "store",
]


class GitStashEntryCmd:
    """Run commands directly for a git stash entry on a git repository."""

    index: int
    branch: str | None
    message: str

    def __init__(
        self,
        *,
        path: StrPath,
        index: int,
        branch: str | None = None,
        message: str = "",
        cmd: Git | None = None,
    ) -> None:
        r"""Lite, typed, pythonic wrapper for git-stash(1) per-entry operations.

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.
        index :
            Stash index (0 = most recent)
        branch :
            Branch the stash was created on
        message :
            Stash message

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ...     branch='master',
        ...     message='WIP',
        ... )
        <GitStashEntryCmd path=... index=0>
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

        self.index = index
        self.branch = branch
        self.message = message

    def __repr__(self) -> str:
        """Representation of a git stash entry."""
        return f"<GitStashEntryCmd path={self.path} index={self.index}>"

    @property
    def stash_ref(self) -> str:
        """Return the stash reference string."""
        return f"stash@{{{self.index}}}"

    def run(
        self,
        command: GitStashCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        r"""Run command against a git stash entry.

        Wraps `git stash <https://git-scm.com/docs/git-stash>`_.
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        return self.cmd.run(
            ["stash", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def show(
        self,
        *,
        stat: bool | None = None,
        patch: bool | None = None,
        include_untracked: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash show for this stash entry.

        Parameters
        ----------
        stat :
            Show diffstat (--stat)
        patch :
            Show patch (-p)
        include_untracked :
            Include untracked files (-u)

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ... ).show()
        'error: stash@{0} is not a valid reference'
        """
        local_flags: list[str] = []

        if stat is True:
            local_flags.append("--stat")
        if patch is True:
            local_flags.append("-p")
        if include_untracked is True:
            local_flags.append("-u")

        local_flags.append(self.stash_ref)

        return self.run(
            "show",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def apply(
        self,
        *,
        index: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash apply for this stash entry.

        Apply the stash without removing it from the stash list.

        Parameters
        ----------
        index :
            Try to reinstate not only the working tree but also the index (--index)
        quiet :
            Suppress output (-q)

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ... ).apply()
        'error: stash@{0} is not a valid reference'
        """
        local_flags: list[str] = []

        if index is True:
            local_flags.append("--index")
        if quiet is True:
            local_flags.append("-q")

        local_flags.append(self.stash_ref)

        return self.run(
            "apply",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def pop(
        self,
        *,
        index: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash pop for this stash entry.

        Apply the stash and remove it from the stash list.

        Parameters
        ----------
        index :
            Try to reinstate not only the working tree but also the index (--index)
        quiet :
            Suppress output (-q)

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ... ).pop()
        'error: stash@{0} is not a valid reference'
        """
        local_flags: list[str] = []

        if index is True:
            local_flags.append("--index")
        if quiet is True:
            local_flags.append("-q")

        local_flags.append(self.stash_ref)

        return self.run(
            "pop",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def drop(
        self,
        *,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash drop for this stash entry.

        Remove this stash from the stash list.

        Parameters
        ----------
        quiet :
            Suppress output (-q)

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ... ).drop()
        'error: stash@{0} is not a valid reference'
        """
        local_flags: list[str] = []

        if quiet is True:
            local_flags.append("-q")

        local_flags.append(self.stash_ref)

        return self.run(
            "drop",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def create_branch(
        self,
        branch_name: str,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash branch for this stash entry.

        Create a new branch from this stash entry and apply the stash.

        Parameters
        ----------
        branch_name :
            Name of the branch to create

        Examples
        --------
        >>> GitStashEntryCmd(
        ...     path=example_git_repo.path,
        ...     index=0,
        ... ).create_branch('new-branch')
        'error: stash@{0} is not a valid reference'
        """
        local_flags: list[str] = [branch_name, self.stash_ref]

        return self.run(
            "branch",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


class GitStashCmd:
    """Run commands directly against a git stash storage for a git repo."""

    def __init__(self, *, path: StrPath, cmd: Git | None = None) -> None:
        """Lite, typed, pythonic wrapper for git-stash(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitStashCmd(path=tmp_path)
        <GitStashCmd path=...>

        >>> GitStashCmd(path=tmp_path).run(quiet=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitStashCmd(path=example_git_repo.path).run(quiet=True)
        ''
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of git stash storage command object."""
        return f"<GitStashCmd path={self.path}>"

    def run(
        self,
        command: GitStashCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        quiet: bool | None = None,
        cached: bool | None = None,  # Only when no command entered and status
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's stash storage.

        Wraps `git stash <https://git-scm.com/docs/git-stash>`_.

        Examples
        --------
        >>> GitStashCmd(path=example_git_repo.path).run()
        'No local changes to save'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if quiet is True:
            local_flags.append("--quiet")
        if cached is True:
            local_flags.append("--cached")

        return self.cmd.run(
            ["stash", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def ls(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash list.

        Examples
        --------
        >>> GitStashCmd(path=example_git_repo.path).ls()
        ''
        """
        return self.run(
            "list",
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def push(
        self,
        *,
        path: list[StrPath] | StrPath | None = None,
        patch: bool | None = None,
        staged: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Git stash update.

        TODO: Fill-in

        Examples
        --------
        >>> GitStashCmd(path=example_git_repo.path).push()
        'No local changes to save'

        >>> GitStashCmd(path=example_git_repo.path).push(path='.')
        'No local changes to save'
        """
        local_flags: list[str] = []
        required_flags: list[str] = []

        if isinstance(path, list):
            required_flags.extend(str(pathlib.Path(p).absolute()) for p in path)
        elif isinstance(path, pathlib.Path):
            required_flags.append(str(pathlib.Path(path).absolute()))

        if patch is True:
            local_flags.append("--patch")
        if staged is True:
            local_flags.append("--staged")

        return self.run(
            "push",
            local_flags=[*local_flags, "--", *required_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def pop(
        self,
        *,
        stash: int | None = None,
        index: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Git stash pop.

        Examples
        --------
        >>> GitStashCmd(path=example_git_repo.path).pop()
        'No stash entries found.'

        >>> GitStashCmd(path=example_git_repo.path).pop(stash=0)
        'error: refs/stash@{0} is not a valid reference'

        >>> GitStashCmd(path=example_git_repo.path).pop(stash=1, index=True)
        'error: refs/stash@{1} is not a valid reference'

        >>> GitStashCmd(path=example_git_repo.path).pop(stash=1, quiet=True)
        'error: refs/stash@{1} is not a valid reference'

        >>> GitStashCmd(path=example_git_repo.path).push(path='.')
        'No local changes to save'
        """
        local_flags: list[str] = []
        stash_flags: list[str] = []

        if stash is not None:
            stash_flags.extend(["--", str(stash)])

        if index is True:
            local_flags.append("--index")
        if quiet is True:
            local_flags.append("--quiet")

        return self.run(
            "pop",
            local_flags=local_flags + stash_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def save(
        self,
        *,
        message: str | None = None,
        staged: int | None = None,
        keep_index: int | None = None,
        patch: bool | None = None,
        include_untracked: bool | None = None,
        _all: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Git stash save.

        Examples
        --------
        >>> GitStashCmd(path=example_git_repo.path).save()
        'No local changes to save'

        >>> GitStashCmd(path=example_git_repo.path).save(message="Message")
        'No local changes to save'
        """
        local_flags: list[str] = []
        stash_flags: list[str] = []

        if _all is True:
            local_flags.append("--all")
        if staged is True:
            local_flags.append("--staged")
        if patch is True:
            local_flags.append("--patch")
        if include_untracked is True:
            local_flags.append("--include-untracked")
        if keep_index is True:
            local_flags.append("--keep-index")
        if quiet is True:
            local_flags.append("--quiet")

        if message is not None:
            local_flags.extend(["--message", message])

        return self.run(
            "save",
            local_flags=local_flags + stash_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


class GitStashManager:
    """Run commands directly related to git stashes of a git repo."""

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: Git | None = None,
    ) -> None:
        """Wrap some of git-stash(1), manager.

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitStashManager(path=tmp_path)
        <GitStashManager path=...>

        >>> GitStashManager(path=tmp_path).run()
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitStashManager(
        ...     path=example_git_repo.path
        ... ).run()
        'No local changes to save'
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of git stash manager object."""
        return f"<GitStashManager path={self.path}>"

    def run(
        self,
        command: GitStashCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's stash storage.

        Wraps `git stash <https://git-scm.com/docs/git-stash>`_.

        Examples
        --------
        >>> GitStashManager(path=example_git_repo.path).run()
        'No local changes to save'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if quiet is True:
            local_flags.append("--quiet")

        return self.cmd.run(
            ["stash", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def push(
        self,
        *,
        message: str | None = None,
        path: list[StrPath] | StrPath | None = None,
        patch: bool | None = None,
        staged: bool | None = None,
        keep_index: bool | None = None,
        include_untracked: bool | None = None,
        _all: bool | None = None,
        quiet: bool | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash push.

        Save local modifications to a new stash entry.

        Parameters
        ----------
        message :
            Stash message
        path :
            Limit stash to specific paths
        patch :
            Interactive patch selection (-p)
        staged :
            Stash only staged changes (-S)
        keep_index :
            Keep index intact (-k)
        include_untracked :
            Include untracked files (-u)
        _all :
            Include ignored files (-a)
        quiet :
            Suppress output (-q)

        Examples
        --------
        >>> GitStashManager(path=example_git_repo.path).push()
        'No local changes to save'

        >>> GitStashManager(path=example_git_repo.path).push(message='WIP')
        'No local changes to save'
        """
        local_flags: list[str] = []
        path_flags: list[str] = []

        if message is not None:
            local_flags.extend(["-m", message])
        if patch is True:
            local_flags.append("-p")
        if staged is True:
            local_flags.append("-S")
        if keep_index is True:
            local_flags.append("-k")
        if include_untracked is True:
            local_flags.append("-u")
        if _all is True:
            local_flags.append("-a")
        if quiet is True:
            local_flags.append("-q")

        if path is not None:
            if isinstance(path, list):
                path_flags.extend(str(pathlib.Path(p).absolute()) for p in path)
            else:
                path_flags.append(str(pathlib.Path(path).absolute()))

        if path_flags:
            local_flags.extend(["--", *path_flags])

        return self.run(
            "push",
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def clear(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git stash clear.

        Remove all stash entries.

        Examples
        --------
        >>> GitStashManager(path=example_git_repo.path).clear()
        ''
        """
        return self.run(
            "clear",
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def _ls(self) -> list[str]:
        r"""List stashes (raw output).

        Examples
        --------
        >>> GitStashManager(path=example_git_repo.path)._ls()
        []
        """
        result = self.run("list")
        if not result:
            return []
        return result.splitlines()

    def ls(self) -> QueryList[GitStashEntryCmd]:
        """List stashes.

        Returns a QueryList of GitStashEntryCmd objects.

        Parses stash list format:
        - ``stash@{0}: On master: message``
        - ``stash@{0}: WIP on master: commit``

        Examples
        --------
        >>> GitStashManager(path=example_git_repo.path).ls()
        []
        """
        stash_lines = self._ls()

        # Parse stash list output
        # Format: stash@{N}: On <branch>: <message>
        # Or: stash@{N}: WIP on <branch>: <commit_msg>
        stash_pattern = re.compile(
            r"""
            stash@\{(?P<index>\d+)\}:\s+
            (?:
                On\s+(?P<branch1>[^:]+):\s+(?P<message1>.+)
                |
                WIP\s+on\s+(?P<branch2>[^:]+):\s+(?P<message2>.+)
            )
        """,
            re.VERBOSE,
        )

        stash_entries: list[GitStashEntryCmd] = []
        for line in stash_lines:
            match = stash_pattern.match(line)
            if match:
                index = int(match.group("index"))
                branch = match.group("branch1") or match.group("branch2")
                message = match.group("message1") or match.group("message2") or ""
                stash_entries.append(
                    GitStashEntryCmd(
                        path=self.path,
                        index=index,
                        branch=branch,
                        message=message,
                    ),
                )
            else:
                # Fallback: try to parse index at minimum
                index_match = re.match(r"stash@\{(\d+)\}", line)
                if index_match:
                    stash_entries.append(
                        GitStashEntryCmd(
                            path=self.path,
                            index=int(index_match.group(1)),
                            message=line,
                        ),
                    )

        return QueryList(stash_entries)

    def get(self, *args: t.Any, **kwargs: t.Any) -> GitStashEntryCmd | None:
        """Get stash entry via filter lookup.

        Examples
        --------
        >>> GitStashManager(
        ...     path=example_git_repo.path
        ... ).get(index=0)
        Traceback (most recent call last):
            exec(compile(example.source, filename, "single",
            ...
            return self.ls().get(*args, **kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "..._internal/query_list.py", line ..., in get
            raise ObjectDoesNotExist
        libvcs._internal.query_list.ObjectDoesNotExist
        """
        return self.ls().get(*args, **kwargs)

    def filter(self, *args: t.Any, **kwargs: t.Any) -> list[GitStashEntryCmd]:
        """Get stash entries via filter lookup.

        Examples
        --------
        >>> GitStashManager(
        ...     path=example_git_repo.path
        ... ).filter(branch__contains='master')
        []
        """
        return self.ls().filter(*args, **kwargs)


GitBranchCommandLiteral = t.Literal[
    # "create",  # checkout -b
    # "checkout",  # checkout
    "--list",
    "move",  # branch -m, or branch -M with force
    "copy",  # branch -c, or branch -C with force
    "delete",  # branch -d, or branch -D /ith force
    "set_upstream",
    "unset_upstream",
    "track",
    "no_track",
    "edit_description",
]


class GitBranchCmd:
    """Run commands directly against a git branch for a git repo."""

    branch_name: str

    def __init__(
        self,
        *,
        path: StrPath,
        branch_name: str,
        cmd: Git | None = None,
    ) -> None:
        """Lite, typed, pythonic wrapper for git-branch(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.
        branch_name:
            Name of branch.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=tmp_path,
        ...     branch_name='master'
        ... )
        <GitBranchCmd path=... branch_name=master>

        >>> GitBranchCmd(
        ...     path=tmp_path,
        ...     branch_name='master'
        ... ).run(quiet=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).run(quiet=True)
        '* master'
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

        self.branch_name = branch_name

    def __repr__(self) -> str:
        """Representation of git branch command object."""
        return f"<GitBranchCmd path={self.path} branch_name={self.branch_name}>"

    def run(
        self,
        command: GitBranchCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        quiet: bool | None = None,
        cached: bool | None = None,  # Only when no command entered and status
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's branch.

        Wraps `git branch <https://git-scm.com/docs/git-branch>`_.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).run()
        '* master'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if quiet is True:
            local_flags.append("--quiet")
        if cached is True:
            local_flags.append("--cached")

        return self.cmd.run(
            ["branch", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def checkout(self) -> str:
        """Git branch checkout.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).checkout()
        "Your branch is up to date with 'origin/master'."
        """
        return self.cmd.run(
            [
                "checkout",
                *[self.branch_name],
            ],
        )

    def create(self) -> str:
        """Create a git branch.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).create()
        "fatal: a branch named 'master' already exists"
        """
        return self.cmd.run(
            [
                "checkout",
                *["-b", self.branch_name],
            ],
            # Pass-through to run()
            check_returncode=False,
        )

    def delete(
        self,
        *,
        force: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Delete this git branch.

        Parameters
        ----------
        force :
            Use ``-D`` instead of ``-d`` to force deletion.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='nonexistent'
        ... ).delete()
        "error: branch 'nonexistent' not found"
        """
        flag = "-D" if force else "-d"
        return self.cmd.run(
            ["branch", flag, self.branch_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def rename(
        self,
        new_name: str,
        *,
        force: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Rename this git branch.

        Parameters
        ----------
        new_name :
            New name for the branch.
        force :
            Use ``-M`` instead of ``-m`` to force rename.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).rename('main')
        ''
        """
        flag = "-M" if force else "-m"
        return self.cmd.run(
            ["branch", flag, self.branch_name, new_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def copy(
        self,
        new_name: str,
        *,
        force: bool = False,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Copy this git branch.

        Parameters
        ----------
        new_name :
            Name for the copied branch.
        force :
            Use ``-C`` instead of ``-c`` to force copy.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).copy('master-copy')
        ''
        """
        flag = "-C" if force else "-c"
        return self.cmd.run(
            ["branch", flag, self.branch_name, new_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def set_upstream(
        self,
        upstream: str,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Set the upstream (tracking) branch.

        Parameters
        ----------
        upstream :
            The upstream branch in format ``remote/branch`` (e.g., ``origin/main``).

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).set_upstream('origin/master')
        "branch 'master' set up to track 'origin/master'."
        """
        return self.cmd.run(
            ["branch", f"--set-upstream-to={upstream}", self.branch_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def unset_upstream(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Remove the upstream (tracking) information.

        Examples
        --------
        >>> GitBranchCmd(
        ...     path=example_git_repo.path,
        ...     branch_name='master'
        ... ).unset_upstream()
        ''
        """
        return self.cmd.run(
            ["branch", "--unset-upstream", self.branch_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


class GitBranchManager:
    """Run commands directly related to git branches of a git repo."""

    branch_name: str

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: Git | None = None,
    ) -> None:
        """Wrap some of git-branch(1), git-checkout(1), manager.

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitBranchManager(path=tmp_path)
        <GitBranchManager path=...>

        >>> GitBranchManager(path=tmp_path).run(quiet=True)
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitBranchManager(
        ...     path=example_git_repo.path).run(quiet=True)
        '* master'
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of git branch manager object."""
        return f"<GitBranchManager path={self.path}>"

    def run(
        self,
        command: GitBranchCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        quiet: bool | None = None,
        cached: bool | None = None,  # Only when no command entered and status
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's branches.

        Wraps `git branch <https://git-scm.com/docs/git-branch>`_.

        Examples
        --------
        >>> GitBranchManager(path=example_git_repo.path).run()
        '* master'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        if quiet is True:
            local_flags.append("--quiet")
        if cached is True:
            local_flags.append("--cached")

        return self.cmd.run(
            ["branch", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def checkout(self, *, branch: str) -> str:
        """Git branch checkout.

        Examples
        --------
        >>> GitBranchManager(path=example_git_repo.path).checkout(branch='master')
        "Your branch is up to date with 'origin/master'."
        """
        return self.cmd.run(
            [
                "checkout",
                *[branch],
            ],
        )

    def create(self, *, branch: str) -> str:
        """Create a git branch.

        Examples
        --------
        >>> GitBranchManager(path=example_git_repo.path).create(branch='master')
        "fatal: a branch named 'master' already exists"
        """
        return self.cmd.run(
            [
                "checkout",
                *["-b", branch],
            ],
            # Pass-through to run()
            check_returncode=False,
        )

    def _ls(self) -> list[str]:
        """List branches.

        Examples
        --------
        >>> GitBranchManager(path=example_git_repo.path)._ls()
        ['* master']
        """
        return self.run(
            "--list",
        ).splitlines()

    def ls(self) -> QueryList[GitBranchCmd]:
        """List branches.

        Examples
        --------
        >>> GitBranchManager(path=example_git_repo.path).ls()
        [<GitBranchCmd path=... branch_name=master>]
        """
        return QueryList(
            [
                GitBranchCmd(path=self.path, branch_name=branch_name.lstrip("* "))
                for branch_name in self._ls()
            ],
        )

    def get(self, *args: t.Any, **kwargs: t.Any) -> GitBranchCmd | None:
        """Get branch via filter lookup.

        Examples
        --------
        >>> GitBranchManager(
        ...     path=example_git_repo.path
        ... ).get(branch_name='master')
        <GitBranchCmd path=... branch_name=master>

        >>> GitBranchManager(
        ...     path=example_git_repo.path
        ... ).get(branch_name='unknown')
        Traceback (most recent call last):
            exec(compile(example.source, filename, "single",
            ...
            return self.ls().get(*args, **kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "..._internal/query_list.py", line ..., in get
            raise ObjectDoesNotExist
        libvcs._internal.query_list.ObjectDoesNotExist
        """
        return self.ls().get(*args, **kwargs)

    def filter(self, *args: t.Any, **kwargs: t.Any) -> list[GitBranchCmd]:
        """Get branches via filter lookup.

        Examples
        --------
        >>> GitBranchManager(
        ...     path=example_git_repo.path
        ... ).filter(branch_name__contains='master')
        [<GitBranchCmd path=... branch_name=master>]

        >>> GitBranchManager(
        ...     path=example_git_repo.path
        ... ).filter(branch_name__contains='unknown')
        []
        """
        return self.ls().filter(*args, **kwargs)


GitTagCommandLiteral = t.Literal[
    "list",
    "create",
    "delete",
    "verify",
]


class GitTagCmd:
    """Run commands directly for a git tag on a git repository."""

    tag_name: str

    def __init__(
        self,
        *,
        path: StrPath,
        tag_name: str,
        cmd: Git | None = None,
    ) -> None:
        r"""Lite, typed, pythonic wrapper for git-tag(1).

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.
        tag_name :
            Name of tag

        Examples
        --------
        >>> GitTagCmd(
        ...     path=example_git_repo.path,
        ...     tag_name='v1.0.0',
        ... )
        <GitTagCmd path=... tag_name=v1.0.0>
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

        self.tag_name = tag_name

    def __repr__(self) -> str:
        """Representation of a git tag for a git repository."""
        return f"<GitTagCmd path={self.path} tag_name={self.tag_name}>"

    def run(
        self,
        command: GitTagCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        r"""Run command against a git tag.

        Wraps `git tag <https://git-scm.com/docs/git-tag>`_.

        Examples
        --------
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='test-tag', message='Test tag'
        ... )
        ''
        >>> GitTagCmd(
        ...     path=example_git_repo.path,
        ...     tag_name='test-tag',
        ... ).run()
        'test-tag'
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        return self.cmd.run(
            ["tag", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def delete(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git tag delete.

        Examples
        --------
        Create a tag first:

        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='delete-me', message='Tag to delete'
        ... )
        ''

        Now delete it:

        >>> GitTagCmd(
        ...     path=example_git_repo.path,
        ...     tag_name='delete-me',
        ... ).delete()
        "Deleted tag 'delete-me'..."
        """
        local_flags: list[str] = ["-d", self.tag_name]

        return self.run(
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def verify(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git tag verify.

        Verify a GPG-signed tag.

        Examples
        --------
        First create a lightweight tag:

        >>> GitTagManager(path=example_git_repo.path).create(name='verify-tag')
        ''

        Try to verify it (lightweight tags can't be verified):

        >>> GitTagCmd(
        ...     path=example_git_repo.path,
        ...     tag_name='verify-tag',
        ... ).verify()
        'error: verify-tag: cannot verify a non-tag object...'
        """
        local_flags: list[str] = ["-v", self.tag_name]

        return self.run(
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def show(
        self,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Show tag details using git show.

        Examples
        --------
        Create an annotated tag first:

        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='show-tag', message='Show this tag'
        ... )
        ''

        Show the tag:

        >>> print(GitTagCmd(
        ...     path=example_git_repo.path,
        ...     tag_name='show-tag',
        ... ).show())
        tag show-tag
        Tagger: ...
        <BLANKLINE>
        Show this tag
        ...
        """
        return self.cmd.run(
            ["show", self.tag_name],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )


class GitTagManager:
    """Run commands directly related to git tags of a git repo."""

    def __init__(
        self,
        *,
        path: StrPath,
        cmd: Git | None = None,
    ) -> None:
        """Wrap some of git-tag(1), manager.

        Parameters
        ----------
        path :
            Operates as PATH in the corresponding git subcommand.

        Examples
        --------
        >>> GitTagManager(path=tmp_path)
        <GitTagManager path=...>

        >>> GitTagManager(path=tmp_path).run()
        'fatal: not a git repository (or any of the parent directories): .git'

        >>> GitTagManager(
        ...     path=example_git_repo.path
        ... ).run()
        ''
        """
        #: Directory to check out
        self.path: pathlib.Path
        if isinstance(path, pathlib.Path):
            self.path = path
        else:
            self.path = pathlib.Path(path)

        self.cmd = cmd if isinstance(cmd, Git) else Git(path=self.path)

    def __repr__(self) -> str:
        """Representation of git tag manager object."""
        return f"<GitTagManager path={self.path}>"

    def run(
        self,
        command: GitTagCommandLiteral | None = None,
        local_flags: list[str] | None = None,
        *,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Run a command against a git repository's tags.

        Wraps `git tag <https://git-scm.com/docs/git-tag>`_.

        Examples
        --------
        >>> GitTagManager(path=example_git_repo.path).run()
        ''
        """
        local_flags = local_flags if isinstance(local_flags, list) else []
        if command is not None:
            local_flags.insert(0, command)

        return self.cmd.run(
            ["tag", *local_flags],
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def create(
        self,
        *,
        name: str,
        ref: str | None = None,
        message: str | None = None,
        annotate: bool | None = None,
        sign: bool | None = None,
        local_user: str | None = None,
        force: bool | None = None,
        file: StrPath | None = None,
        # Pass-through to run()
        log_in_real_time: bool = False,
        check_returncode: bool | None = None,
    ) -> str:
        """Git tag create.

        Parameters
        ----------
        name :
            Name of the tag to create
        ref :
            Git reference (commit, branch) to tag. Defaults to HEAD.
        message :
            Tag message (implies annotated tag)
        annotate :
            Create an annotated tag
        sign :
            Create a GPG-signed tag
        local_user :
            Use specific GPG key for signing
        force :
            Replace existing tag
        file :
            Read message from file

        Examples
        --------
        Create a lightweight tag:

        >>> GitTagManager(path=example_git_repo.path).create(name='lightweight-tag')
        ''

        Create an annotated tag:

        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='annotated-tag', message='This is an annotated tag'
        ... )
        ''

        Create a tag on a specific commit:

        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='ref-tag', ref='HEAD', message='Tag at HEAD'
        ... )
        ''
        """
        local_flags: list[str] = []

        if annotate is True:
            local_flags.append("-a")
        if sign is True:
            local_flags.append("-s")
        if local_user is not None:
            local_flags.extend(["-u", local_user])
        if force is True:
            local_flags.append("-f")
        if message is not None:
            local_flags.extend(["-m", message])
        if file is not None:
            local_flags.extend(["-F", str(file)])

        local_flags.append(name)

        if ref is not None:
            local_flags.append(ref)

        return self.run(
            local_flags=local_flags,
            check_returncode=check_returncode,
            log_in_real_time=log_in_real_time,
        )

    def _ls(
        self,
        *,
        pattern: str | None = None,
        sort: str | None = None,
        contains: str | None = None,
        no_contains: str | None = None,
        merged: str | None = None,
        no_merged: str | None = None,
        lines: int | None = None,
    ) -> list[str]:
        r"""List tags (raw output).

        Examples
        --------
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='list-tag-1', message='First tag'
        ... )
        ''
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='list-tag-2', message='Second tag'
        ... )
        ''
        >>> 'list-tag-1' in GitTagManager(path=example_git_repo.path)._ls()
        True
        """
        local_flags: list[str] = ["-l"]

        if sort is not None:
            local_flags.append(f"--sort={sort}")
        if contains is not None:
            local_flags.extend(["--contains", contains])
        if no_contains is not None:
            local_flags.extend(["--no-contains", no_contains])
        if merged is not None:
            local_flags.extend(["--merged", merged])
        if no_merged is not None:
            local_flags.extend(["--no-merged", no_merged])
        if lines is not None:
            local_flags.append(f"-n{lines}")
        if pattern is not None:
            local_flags.append(pattern)

        result = self.run(local_flags=local_flags)
        if not result:
            return []
        return result.splitlines()

    def ls(
        self,
        *,
        pattern: str | None = None,
        sort: str | None = None,
        contains: str | None = None,
        no_contains: str | None = None,
        merged: str | None = None,
        no_merged: str | None = None,
    ) -> QueryList[GitTagCmd]:
        """List tags.

        Parameters
        ----------
        pattern :
            List tags matching pattern (shell wildcard)
        sort :
            Sort by key (e.g., 'version:refname', '-creatordate')
        contains :
            Only tags containing the specified commit
        no_contains :
            Only tags not containing the specified commit
        merged :
            Only tags merged into the specified commit
        no_merged :
            Only tags not merged into the specified commit

        Examples
        --------
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='ls-tag', message='Listing tag'
        ... )
        ''
        >>> tags = GitTagManager(path=example_git_repo.path).ls()
        >>> any(t.tag_name == 'ls-tag' for t in tags)
        True
        """
        tag_names = self._ls(
            pattern=pattern,
            sort=sort,
            contains=contains,
            no_contains=no_contains,
            merged=merged,
            no_merged=no_merged,
        )

        return QueryList(
            [GitTagCmd(path=self.path, tag_name=tag_name) for tag_name in tag_names],
        )

    def get(self, *args: t.Any, **kwargs: t.Any) -> GitTagCmd | None:
        """Get tag via filter lookup.

        Examples
        --------
        Create a tag first:

        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='get-tag', message='Get this tag'
        ... )
        ''

        >>> GitTagManager(
        ...     path=example_git_repo.path
        ... ).get(tag_name='get-tag')
        <GitTagCmd path=... tag_name=get-tag>

        >>> GitTagManager(
        ...     path=example_git_repo.path
        ... ).get(tag_name='unknown')
        Traceback (most recent call last):
            exec(compile(example.source, filename, "single",
            ...
            return self.ls().get(*args, **kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          File "..._internal/query_list.py", line ..., in get
            raise ObjectDoesNotExist
        libvcs._internal.query_list.ObjectDoesNotExist
        """
        return self.ls().get(*args, **kwargs)

    def filter(self, *args: t.Any, **kwargs: t.Any) -> list[GitTagCmd]:
        """Get tags via filter lookup.

        Examples
        --------
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='filter-tag-a', message='Filter tag A'
        ... )
        ''
        >>> GitTagManager(path=example_git_repo.path).create(
        ...     name='filter-tag-b', message='Filter tag B'
        ... )
        ''

        >>> len(GitTagManager(
        ...     path=example_git_repo.path
        ... ).filter(tag_name__contains='filter-tag')) >= 2
        True

        >>> GitTagManager(
        ...     path=example_git_repo.path
        ... ).filter(tag_name__contains='unknown')
        []
        """
        return self.ls().filter(*args, **kwargs)
