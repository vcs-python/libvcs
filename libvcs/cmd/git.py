import pathlib
from typing import Any, Literal, Optional, Sequence, Union

from ..types import StrOrBytesPath, StrOrPath
from .core import run

_CMD = Union[StrOrBytesPath, Sequence[StrOrBytesPath]]


class Git:
    def __init__(self, dir: StrOrPath):
        """Lite, typed, pythonic wrapper for git(1).

        Parameters
        ----------
        dir :
            Operates as PATH in the corresonding git subcommand.

        Examples
        --------
        >>> Git(dir=tmp_path)
        <Git dir=...>
        """
        #: Directory to check out
        self.dir: pathlib.Path
        if isinstance(dir, pathlib.Path):
            self.dir = dir
        else:
            self.dir = pathlib.Path(dir)

    def __repr__(self):
        return f"<Git dir={self.dir}>"

    def run(
        self,
        args: _CMD,
        # Print-and-exit flags
        version: Optional[bool] = None,
        help: Optional[bool] = None,
        html_path: Optional[bool] = None,
        man_path: Optional[bool] = None,
        info_path: Optional[bool] = None,
        # Normal flags
        cwd: Optional[StrOrBytesPath] = None,
        git_dir: Optional[StrOrBytesPath] = None,
        work_tree: Optional[StrOrBytesPath] = None,
        namespace: Optional[StrOrBytesPath] = None,
        super_prefix: Optional[StrOrBytesPath] = None,
        exec_path: Optional[StrOrBytesPath] = None,
        bare: Optional[bool] = None,
        no_replace_objects: Optional[bool] = None,
        literal_pathspecs: Optional[bool] = None,
        global_pathspecs: Optional[bool] = None,
        noglob_pathspecs: Optional[bool] = None,
        icase_pathspecs: Optional[bool] = None,
        no_optional_locks: Optional[bool] = None,
        config: Optional[str] = None,
        config_env: Optional[str] = None,
        **kwargs,
    ):
        """
        Passing None to a subcommand option, the flag won't be passed unless otherwise
        stated.

        `git help` and `git help [cmd]`

        Wraps git's `Options <https://git-scm.com/docs/git#_options>`_.

        Parameters
        ----------
        cwd : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            ``-C <path>``, Defaults to :attr:`~.cwd`
        git_dir : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            ``--git-dir <path>``
        work_tree : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            ``--work-tree <path>``
        namespace : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            ``--namespace <path>``
        super_prefix : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
            ``--super-prefix <path>``
        exec_path : :attr:`libvcs.cmd.types.StrOrBytesPath`, optional
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
        help : bool
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
        >>> git = Git(dir=tmp_path)
        >>> git.run(['help'])  # doctest: +NORMALIZE_WHITESPACE
        "usage: git [--version] [--help] [-C <path>]..."
        """

        if isinstance(args, Sequence):
            cli_args = ["git", *args]
        else:
            cli_args = ["git", args]

        if "cwd" not in kwargs:
            kwargs["cwd"] = self.dir

        #
        # Print-and-exit
        #
        if version is True:
            cli_args.append("--version")
        if help is True:
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
        if cwd is not None:
            cli_args.append(f"-C {cwd}")
        if git_dir is not None:
            cli_args.append(f"--git-dir {git_dir}")
        if work_tree is not None:
            cli_args.append(f"--work-tree {work_tree}")
        if namespace is not None:
            cli_args.append(f"--namespace {namespace}")
        if super_prefix is not None:
            cli_args.append(f"--super-prefix {super_prefix}")
        if exec_path is not None:
            cli_args.append(f"--exec-path {exec_path}")
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

        return run(cmd=cli_args, **kwargs)

    def clone(
        self,
        url: str,
        separate_git_dir: Optional[StrOrBytesPath] = None,
        template: Optional[str] = None,
        depth: Optional[str] = None,
        branch: Optional[str] = None,
        origin: Optional[str] = None,
        upload_pack: Optional[str] = None,
        shallow_since: Optional[str] = None,
        shallow_exclude: Optional[str] = None,
        reference: Optional[str] = None,
        reference_if_able: Optional[str] = None,
        server_option: Optional[str] = None,
        jobs: Optional[str] = None,
        force: Optional[bool] = None,
        local: Optional[bool] = None,
        all: Optional[bool] = None,
        no_hardlinks: Optional[bool] = None,
        hardlinks: Optional[bool] = None,
        shared: Optional[bool] = None,
        progress: Optional[bool] = None,
        no_checkout: Optional[bool] = None,
        no_reject_shallow: Optional[bool] = None,
        reject_shallow: Optional[bool] = None,
        sparse: Optional[bool] = None,
        shallow_submodules: Optional[bool] = None,
        no_shallow_submodules: Optional[bool] = None,
        remote_submodules: Optional[bool] = None,
        no_remote_submodules: Optional[bool] = None,
        verbose: Optional[bool] = None,
        quiet: Optional[bool] = None,
        # Special behavior
        make_parents: Optional[bool] = True,
        **kwargs,
    ):
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
            Creates checkout directory (`:attr:`self.dir`) if it doesn't already exist.

        Examples
        --------
        >>> git = Git(dir=tmp_path)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.clone(url=f'file://{git_remote_repo}')
        ''
        >>> git.dir.exists()
        True
        """
        required_flags: list[str] = [url, str(self.dir)]
        local_flags: list[str] = []

        if template is not None:
            local_flags.append(f"--template={template}")
        if separate_git_dir is not None:
            local_flags.append(f"--separate-git-dir={separate_git_dir}")
        if (filter := kwargs.pop("filter", None)) is not None:
            local_flags.append(f"--filter={filter}")
        if depth is not None:
            local_flags.append(f"--depth {depth}")
        if branch is not None:
            local_flags.append(f"--branch {branch}")
        if origin is not None:
            local_flags.append(f"--origin {origin}")
        if upload_pack is not None:
            local_flags.append(f"--upload-pack {upload_pack}")
        if shallow_since is not None:
            local_flags.append(f"--shallow-since={shallow_since}")
        if shallow_exclude is not None:
            local_flags.append(f"--shallow-exclude={shallow_exclude}")
        if reference is not None:
            local_flags.append(f"--reference {reference}")
        if reference_if_able is not None:
            local_flags.append(f"--reference {reference_if_able}")
        if server_option is not None:
            local_flags.append(f"--server-option={server_option}")
        if jobs is not None:
            local_flags.append(f"--jobs {jobs}")
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
        if make_parents and not self.dir.exists():
            self.dir.mkdir(parents=True)
        return self.run(
            ["clone", *local_flags, "--", *required_flags], check_returncode=False
        )

    def fetch(
        self,
        reftag: Optional[Any] = None,
        deepen: Optional[str] = None,
        depth: Optional[str] = None,
        branch: Optional[str] = None,
        origin: Optional[str] = None,
        upload_pack: Optional[str] = None,
        shallow_since: Optional[str] = None,
        shallow_exclude: Optional[str] = None,
        negotiation_tip: Optional[str] = None,
        jobs: Optional[str] = None,
        server_option: Optional[str] = None,
        recurse_submodules: Optional[
            Union[bool, Literal["yes", "on-demand", "no"]]
        ] = None,
        recurse_submodules_default: Optional[
            Union[bool, Literal["yes", "on-demand"]]
        ] = None,
        submodule_prefix: Optional[StrOrBytesPath] = None,
        #
        all: Optional[bool] = None,
        force: Optional[bool] = None,
        keep: Optional[bool] = None,
        multiple: Optional[bool] = None,
        dry_run: Optional[bool] = None,
        append: Optional[bool] = None,
        atomic: Optional[bool] = None,
        ipv4: Optional[bool] = None,
        ipv6: Optional[bool] = None,
        progress: Optional[bool] = None,
        quiet: Optional[bool] = None,
        verbose: Optional[bool] = None,
        unshallow: Optional[bool] = None,
        update_shallow: Optional[bool] = None,
        negotiate_tip: Optional[bool] = None,
        no_write_fetch_head: Optional[bool] = None,
        write_fetch_head: Optional[bool] = None,
        no_auto_maintenance: Optional[bool] = None,
        auto_maintenance: Optional[bool] = None,
        no_write_commit_graph: Optional[bool] = None,
        write_commit_graph: Optional[bool] = None,
        prefetch: Optional[bool] = None,
        prune: Optional[bool] = None,
        prune_tags: Optional[bool] = None,
        no_tags: Optional[bool] = None,
        tags: Optional[bool] = None,
        no_recurse_submodules: Optional[bool] = None,
        set_upstream: Optional[bool] = None,
        update_head_ok: Optional[bool] = None,
        show_forced_updates: Optional[bool] = None,
        no_show_forced_updates: Optional[bool] = None,
        negotiate_only: Optional[bool] = None,
        **kwargs,
    ):
        """Download from repo. Wraps `git fetch <https://git-scm.com/docs/git-fetch>`_.

        Examples
        --------
        >>> git = Git(dir=git_local_clone.dir)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.fetch()
        ''
        >>> git = Git(dir=git_local_clone.dir)
        >>> git_remote_repo = create_git_remote_repo()
        >>> git.fetch(reftag=f'file://{git_remote_repo}')
        ''
        >>> git.dir.exists()
        True
        """
        required_flags: list[str] = []
        if reftag:
            required_flags.insert(0, reftag)
        local_flags: list[str] = []

        if submodule_prefix is not None:
            local_flags.append(f"--submodule-prefix={submodule_prefix}")
        if (filter := kwargs.pop("filter", None)) is not None:
            local_flags.append(f"--filter={filter}")
        if depth is not None:
            local_flags.append(f"--depth {depth}")
        if branch is not None:
            local_flags.append(f"--branch {branch}")
        if origin is not None:
            local_flags.append(f"--origin {origin}")
        if upload_pack is not None:
            local_flags.append(f"--upload-pack {upload_pack}")
        if shallow_since is not None:
            local_flags.append(f"--shallow-since={shallow_since}")
        if shallow_exclude is not None:
            local_flags.append(f"--shallow-exclude={shallow_exclude}")
        if server_option is not None:
            local_flags.append(f"--server-option={server_option}")
        if jobs is not None:
            local_flags.append(f"--jobs {jobs}")
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
        if all:
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
            ["fetch", *local_flags, "--", *required_flags], check_returncode=False
        )
