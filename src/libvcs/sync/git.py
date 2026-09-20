"""Tool to manage a local git clone from an external git repository.

.. todo::

    From https://github.com/saltstack/salt (Apache License):

    - :meth:`~libvcs.sync.git.GitSync.remote`
    - :meth:`~libvcs.sync.git.GitSync.set_remote`

    From pip (MIT License):

    - :meth:`~libvcs.sync.git.GitSync.set_remote`
    - :func:`~libvcs.sync.git.convert_pip_url`
    - :meth:`~libvcs.sync.git.GitSync.get_revision`
    - :meth:`~libvcs.sync.git.GitSync.get_git_version`
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import pathlib
import re
import typing as t
from urllib import parse as urlparse

from libvcs import exc
from libvcs._internal import preservation
from libvcs._internal.run import ProgressCallbackProtocol
from libvcs._internal.subprocess import SubprocessCommand
from libvcs._internal.types import StrPath
from libvcs.cmd.git import Git
from libvcs.cmd.git_filter import Auto, GitFilterInput, filter_specs
from libvcs.sync.base import (
    BaseSync,
    RecoveryToken,
    SyncConflict,
    SyncPolicy,
    SyncResult,
    SyncTarget,
    VCSLocation,
    WorkingCopyPosition,
    convert_pip_url as base_convert_pip_url,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class GitOptions:
    """Backend-specific options for Git synchronization."""

    depth: int | None = None
    filter: GitFilterInput | None = None
    tls_verify: bool = True

    def __post_init__(self) -> None:
        """Validate and snapshot Git options without running Git."""
        if self.depth is not None and (
            isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth < 1
        ):
            msg = "depth must be a positive integer or None"
            raise ValueError(msg)
        if not isinstance(self.tls_verify, bool):
            msg = "tls_verify must be a boolean"
            raise TypeError(msg)
        specs = filter_specs(self.filter)
        if specs == ("auto",):
            canonical_filter: GitFilterInput | None = Auto()
        else:
            canonical_filter = specs or None
        object.__setattr__(self, "filter", canonical_filter)


class GitStatusParsingException(exc.LibVCSException):
    """Raised when git status output is not in the expected format."""

    def __init__(self, git_status_output: str, *args: object) -> None:
        super().__init__(
            "Could not find match for git-status(1)" + f"Output: {git_status_output}",
        )


class GitRemoteOriginMissing(exc.LibVCSException):
    """Raised when git origin remote was not found."""

    def __init__(self, remotes: list[str], *args: object) -> None:
        super().__init__(f"Missing origin. Remotes: {', '.join(remotes)}")


class GitRemoteSetError(exc.LibVCSException):
    """Raised when a git remote could not be set."""

    def __init__(self, remote_name: str) -> None:
        super().__init__(f"Remote {remote_name} not found after setting")


class GitNoBranchFound(exc.LibVCSException):
    """Raised with git branch could not be found."""

    def __init__(self, *args: object) -> None:
        super().__init__("No branch found for git repository")


class GitRemoteRefNotFound(exc.CommandError):
    """Raised when a git remote ref (tag, branch) could not be found."""

    _message: str

    def __init__(self, git_tag: str, ref_output: str, *args: object) -> None:
        self._message = (
            f"Could not fetch remote in refs/remotes/{git_tag}. Output: {ref_output}"
        )
        super().__init__(self._message)

    def __str__(self) -> str:
        """Return descriptive message without requiring cmd attribute."""
        return self._message


@dataclasses.dataclass
class GitRemote:
    """Structure containing git working copy information.

    Attributes
    ----------
    name : str
        Remote name as git records it, e.g. ``origin``.
    fetch_url : str
        URL git fetches from for this remote.
    push_url : str
        URL git pushes to for this remote. Same as ``fetch_url`` unless a
        separate push URL is configured.
    """

    name: str
    fetch_url: str
    push_url: str


GitSyncRemoteDict = dict[str, GitRemote]
GitRemotesArgs = None | GitSyncRemoteDict | dict[str, str]


@dataclasses.dataclass
class GitStatus:
    """Git status information.

    Fields hold the ``# branch.*`` headers of ``git status -sb
    --porcelain=2`` as strings, unconverted. Each is ``None`` when the header
    is absent from the output :meth:`GitStatus.from_stdout` parsed.

    Attributes
    ----------
    branch_oid : str | None
        Commit SHA of ``HEAD``. ``None`` on an unborn branch, where git
        reports ``(initial)`` instead of a SHA.
    branch_head : str | None
        Checked-out branch name, or ``(detached)`` when ``HEAD`` points at a
        commit rather than a branch.
    branch_upstream : str | None
        Upstream branch ``HEAD`` tracks, e.g. ``origin/master``. ``None``
        when the branch has no upstream configured.
    branch_ab : str | None
        Ahead/behind counts as git prints them, e.g. ``+0 -0``. ``None``
        without an upstream to compare against.
    branch_ahead : str | None
        Commit count ahead of the upstream, taken from ``branch_ab``.
    branch_behind : str | None
        Commit count behind the upstream, taken from ``branch_ab``.
    """

    branch_oid: str | None = None
    branch_head: str | None = None
    branch_upstream: str | None = None
    branch_ab: str | None = None
    branch_ahead: str | None = None
    branch_behind: str | None = None

    @classmethod
    def from_stdout(cls, value: str) -> GitStatus:
        """Return ``git status -sb --porcelain=2`` extracted to a dict.

        Returns
        -------
        Dictionary of git repo's status
        """
        pattern = re.compile(
            r"""[\n\r]?
            (
                #
                \W+
                branch.oid\W+
                (?P<branch_oid>
                    [a-f0-9]{40}
                )
            )?
            (
                #
                \W+
                branch.head
                [\W]+
                (?P<branch_head>
                    .*
                )

            )?
            (
                #
                \W+
                branch.upstream
                [\W]+
                (?P<branch_upstream>
                    .*
                )
            )?
            (
                #
                \W+
                branch.ab
                [\W]+
                (?P<branch_ab>
                    \+(?P<branch_ahead>\d+)
                    \W{1}
                    \-(?P<branch_behind>\d+)
                )
            )?
            """,
            re.VERBOSE | re.MULTILINE,
        )
        matches = pattern.search(value)

        if matches is None:
            raise GitStatusParsingException(git_status_output=value)
        return cls(**matches.groupdict())


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Convert pip-style URL to a VCSLocation.

    Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
    That's required because although they use SSH they sometimes doesn't
    work with a ssh:// scheme (e.g. Github). But we need a scheme for
    parsing. Hence we remove it again afterwards and return it as a stub.
    The manpage for git-clone(1) refers to this as the "scp-like styntax".
    """
    if "://" not in pip_url:
        assert "file:" not in pip_url
        pip_url = pip_url.replace("git+", "git+ssh://")
        url, rev = base_convert_pip_url(pip_url)
        url = url.replace("ssh://", "")
    elif "github.com:" in pip_url:
        msg = (
            "Repo {} is malformatted, please use the convention {} for "
            "ssh / private GitHub repositories.".format(
                pip_url,
                "git+https://github.com/username/repo.git",
            )
        )
        raise exc.LibVCSException(
            msg,
        )
    else:
        url, rev = base_convert_pip_url(pip_url)

    return VCSLocation(url=url, rev=rev)


class GitSync(BaseSync):
    """Tool to manage a local git clone from an external git repository."""

    bin_name = "git"
    schemes = ("git+http", "git+https", "git+file")
    cmd: Git
    _remotes: GitSyncRemoteDict
    options_type = GitOptions

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        options: GitOptions | None = None,
        remotes: GitRemotesArgs = None,
        progress_callback: ProgressCallbackProtocol | None = None,
        rev: str | None = None,
    ) -> None:
        """Local git repository.

        Parameters
        ----------
        url : str
            URL of repo

        options : GitOptions, optional
            Git-specific clone and transport configuration.

        Examples
        --------
        .. code-block:: python

            import os
            from libvcs.sync.git import GitSync

            checkout = pathlib.Path(__name__) + '/' + 'my_libvcs'

            repo = GitSync(
               url="https://github.com/vcs-python/libvcs",
               path=checkout,
               remotes={
                   'gitlab': 'https://gitlab.com/vcs-python/libvcs'
               }
            )

        .. code-block:: python

            import os
            from libvcs.sync.git import GitSync

            checkout = pathlib.Path(__name__) + '/' + 'my_libvcs'

            repo = GitSync(
               url="https://github.com/vcs-python/libvcs",
               path=checkout,
               remotes={
                   'gitlab': {
                       'fetch_url': 'https://gitlab.com/vcs-python/libvcs',
                       'push_url': 'https://gitlab.com/vcs-python/libvcs',
                   },
               }
            )
        """
        if options is None:
            options = GitOptions()
        elif not isinstance(options, GitOptions):
            msg = "options must be a GitOptions instance"
            raise TypeError(msg)
        self.options = options

        self._remotes: GitSyncRemoteDict

        if remotes is None:
            self._remotes: GitSyncRemoteDict = {
                "origin": GitRemote(name="origin", fetch_url=url, push_url=url),
            }
        elif isinstance(remotes, dict):
            self._remotes = {}
            for remote_name, remote_url in remotes.items():
                if isinstance(remote_url, str):
                    self._remotes[remote_name] = GitRemote(
                        name=remote_name,
                        fetch_url=remote_url,
                        push_url=remote_url,
                    )
                elif isinstance(remote_url, dict):
                    self._remotes[remote_name] = GitRemote(
                        fetch_url=remote_url["fetch_url"],
                        push_url=remote_url["push_url"],
                        name=remote_name,
                    )
                elif isinstance(remote_url, GitRemote):
                    self._remotes[remote_name] = remote_url

        if url and "origin" not in self._remotes:
            self._remotes["origin"] = GitRemote(
                name="origin",
                fetch_url=url,
                push_url=url,
            )
        super().__init__(
            url=url,
            path=path,
            progress_callback=progress_callback,
            rev=rev,
        )

        self.cmd = Git(path=path, progress_callback=self.progress_callback)

        origin = (
            self._remotes.get("origin")
            if "origin" in self._remotes
            else next(iter(self._remotes.items()))[1]
        )
        if origin is None:
            raise GitRemoteOriginMissing(remotes=list(self._remotes.keys()))
        self.url = self.chomp_protocol(origin.fetch_url)

    @classmethod
    def from_pip_url(cls, pip_url: str, **kwargs: t.Any) -> GitSync:
        """Clone a git repository from a pip-style URL."""
        url, rev = convert_pip_url(pip_url)
        return cls(url=url, rev=rev, **kwargs)

    def get_revision(self) -> str:
        """Return current revision. Initial repositories return 'initial'."""
        try:
            return self.cmd.rev_parse(
                verify=True, args="HEAD", check_returncode=True
            ).strip()
        except exc.CommandError:
            return "initial"

    def set_remotes(self, overwrite: bool = False) -> None:
        """Apply remotes in local repository to match GitSync's configuration."""
        remotes = self._remotes
        if isinstance(remotes, dict):
            for remote_name, git_remote_repo in remotes.items():
                existing_remote = self.remote(remote_name)
                if isinstance(git_remote_repo, GitRemote):
                    if (
                        not existing_remote
                        or existing_remote.fetch_url != git_remote_repo.fetch_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.fetch_url,
                            overwrite=overwrite,
                        )
                        # refresh if we're setting it, so push can be checked
                        existing_remote = self.remote(remote_name)
                    if git_remote_repo.push_url and (
                        not existing_remote
                        or existing_remote.push_url != git_remote_repo.push_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.push_url,
                            push=True,
                            overwrite=overwrite,
                        )
                elif (
                    not existing_remote
                    or existing_remote.fetch_url != git_remote_repo.fetch_url
                ):
                    self.set_remote(
                        name=remote_name,
                        url=git_remote_repo.fetch_url,
                        overwrite=overwrite,
                    )

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Retrieve the repository, clone if doesn't exist."""
        self.ensure_dir()

        url = self.url

        self.log.info("Cloning.")
        self.cmd.clone(
            url=url,
            progress=True,
            depth=self.options.depth,
            _filter=self.options.filter,
            config={"http.sslVerify": False} if not self.options.tls_verify else None,
            log_in_real_time=True,
            check_returncode=True,
        )

        submodule_filter = self.options.filter
        if isinstance(self.options.filter, Auto):
            tracked = self.cmd.run(["ls-files", "--stage", "-z"], check_returncode=True)
            if any(entry.startswith("160000 ") for entry in tracked.split("\0")):
                msg = (
                    "git_filter: auto cannot be applied to repository submodules; "
                    "the parent clone remains at the destination"
                )
                raise ValueError(msg)
            submodule_filter = None

        self.log.info("Initializing submodules.")
        self.cmd.submodule.init(
            log_in_real_time=True,
        )
        self.cmd.submodule.update(
            init=True,
            recursive=True,
            depth=self.options.depth,
            _filter=submodule_filter,
            config=({"http.sslVerify": False} if not self.options.tls_verify else None),
            log_in_real_time=True,
        )

        self.set_remotes(overwrite=True)

    def _read_git(self, args: list[str], *, path: pathlib.Path | None = None) -> str:
        """Read native metadata without mixing diagnostics into machine output."""
        command = SubprocessCommand(
            ["git", "-c", "protocol.allow=never", *args],
            cwd=path or self.path,
            env={
                **{
                    key: value
                    for key, value in os.environ.items()
                    if key != "GIT_CONFIG"
                },
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        completed = command.run(capture_output=True, check=False)
        if completed.returncode:
            raise exc.CommandError(
                cmd=["git", *args],
                returncode=completed.returncode,
                output=os.fsdecode(completed.stderr),
            )
        return os.fsdecode(completed.stdout)

    def _oid(self, ref: str) -> str:
        return self._read_git(
            ["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"]
        ).strip()

    def resolve_target(self, target: SyncTarget | None = None) -> WorkingCopyPosition:
        """Resolve available local refs without fetching or changing the checkout."""
        if target is None and self.rev is not None:
            target = SyncTarget(rev=self.rev)
        current = self.get_position()
        if target is None:
            if not current.follows:
                return current
            try:
                oid = self._oid("@{upstream}")
            except exc.CommandError:
                oid = self._oid(f"refs/remotes/origin/{current.ref_name}")
            return dataclasses.replace(current, revision=oid)
        if target.branch is not None:
            branch = target.branch
            self._read_git(["check-ref-format", f"refs/heads/{branch}"])
            remote = target.remote or "origin"
            try:
                oid = self._oid(f"refs/remotes/{remote}/{branch}")
            except exc.CommandError:
                if target.remote is not None:
                    raise
                oid = self._oid(f"refs/heads/{branch}")
            return WorkingCopyPosition(oid, branch, "branch", follows=True)
        if target.tag is not None:
            return WorkingCopyPosition(
                self._oid(f"refs/tags/{target.tag}"), target.tag, "tag", follows=False
            )
        if target.commit is not None:
            oid = self._oid(target.commit)
            return WorkingCopyPosition(oid, oid, "commit", follows=False)
        rev = str(target.rev)
        for prefix, kind in (("refs/heads/", "branch"), ("refs/tags/", "tag")):
            try:
                self._oid(prefix + rev)
            except exc.CommandError:
                continue
            return self.resolve_target(
                SyncTarget(branch=rev, remote=target.remote)
                if kind == "branch"
                else SyncTarget(tag=rev)
            )
        if rev.startswith("origin/"):
            return self.resolve_target(
                SyncTarget(branch=rev.removeprefix("origin/"), remote="origin")
            )
        oid = self._oid(rev)
        return WorkingCopyPosition(oid, oid, "commit", follows=False)

    def _dirty_paths(self) -> tuple[str, ...]:
        entries = iter(
            self._read_git(
                ["status", "--porcelain=v2", "-z", "--untracked-files=all"]
            ).split("\0")
        )
        paths = []
        for entry in entries:
            if not entry:
                continue
            kind = entry[0]
            if kind in "12u":
                fields = entry.split(" ", {"1": 8, "2": 9, "u": 10}[kind])
                if len(fields) != {"1": 9, "2": 10, "u": 11}[kind]:
                    raise GitStatusParsingException(entry)
                if kind == "u" or fields[2] != "N...":
                    msg = "unmerged index or submodule changes are unsupported"
                    raise ValueError(msg)
                paths.append(fields[-1])
                if kind == "2":
                    original = next(entries, "")
                    if not original:
                        raise GitStatusParsingException(entry)
                    paths.append(original)
            elif kind == "?":
                paths.append(entry[2:])
            else:
                raise GitStatusParsingException(entry)
        return tuple(paths)

    def is_dirty(self) -> bool:
        """Read tracked and untracked changes; ignored output is not ordinary dirt."""
        return bool(self._dirty_paths())

    def _store(self) -> preservation.RecoveryStore:
        common = pathlib.Path(
            self._read_git(
                ["rev-parse", "--path-format=absolute", "--git-common-dir"]
            ).strip()
        )
        return preservation.RecoveryStore(self.path, "git", common)

    def _precondition(self) -> tuple[str, ...]:
        root = pathlib.Path(self._read_git(["rev-parse", "--show-toplevel"]).strip())
        if root != self.path.absolute():
            msg = "Git synchronization requires the working-copy root"
            raise ValueError(msg)
        for name in (
            "index.lock",
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "rebase-merge",
            "rebase-apply",
            "sequencer",
        ):
            path = pathlib.Path(
                self._read_git(["rev-parse", "--git-path", name]).strip()
            )
            if not path.is_absolute():
                path = self.path / path
            if path.exists():
                msg = f"native Git activity prevents synchronization: {name}"
                raise ValueError(msg)
        dirty = self._dirty_paths()
        tracked = self._read_git(["ls-files", "--stage", "-z"])
        submodules = {
            self.path / entry.split("\t", 1)[1]
            for entry in tracked.split("\0")
            if entry.startswith("160000 ")
        }
        if submodules and dirty:
            msg = "dirty submodule scope cannot be preserved"
            raise ValueError(msg)
        for directory, dirs, files in os.walk(self.path, followlinks=False):
            current = pathlib.Path(directory)
            if current in submodules:
                dirs[:] = []
                continue
            if current != self.path and any(
                name in dirs or name in files for name in (".git", ".hg", ".svn")
            ):
                msg = "nested repository prevents synchronization"
                raise ValueError(msg)
            dirs[:] = [name for name in dirs if name not in (".git", ".hg", ".svn")]
        return dirty

    def _guard_submodules(self, revision: str) -> None:
        """Guard initialized descendants before recursive checkout writes."""
        tree = self._read_git(["ls-tree", "-r", "-z", revision])
        for entry in tree.split("\0"):
            if not entry.startswith("160000 "):
                continue
            metadata, relative = entry.split("\t", 1)
            desired = metadata.split(" ")[2]
            path = preservation.safe_path(self.path / relative)
            if not (path / ".git").exists():
                continue
            child = GitSync(url=self.url, path=path, options=self.options)
            if child._precondition():
                msg = f"dirty submodule prevents recursive update: {relative}"
                raise ValueError(msg)
            try:
                child._oid(desired)
            except exc.CommandError:
                child.cmd.fetch(
                    _all=True,
                    config={"http.sslVerify": False}
                    if not self.options.tls_verify
                    else None,
                    check_returncode=True,
                )
                child._oid(desired)
            original = child.get_position()
            target = WorkingCopyPosition(desired, desired, "commit", follows=False)
            try:
                child._ignored_collisions(original, target, dirty=False)
                child._guard_submodules(desired)
            except ValueError as error:
                msg = f"submodule {relative}: {error}"
                raise ValueError(msg) from error

    def _sync_submodules(self) -> None:
        self._guard_submodules(self._oid("HEAD"))
        self.cmd.submodule.update(
            recursive=True,
            init=True,
            config={"http.sslVerify": False} if not self.options.tls_verify else None,
            log_in_real_time=True,
            check_returncode=True,
        )

    def _ignored_collisions(
        self, original: WorkingCopyPosition, target: WorkingCopyPosition, *, dirty: bool
    ) -> None:
        ignored = self._read_git(
            ["ls-files", "--others", "--ignored", "--exclude-standard", "-z"]
        ).split("\0")
        changed = self._read_git(
            [
                "diff",
                "--name-only",
                "--diff-filter=ACMRT",
                "--no-renames",
                "-z",
                original.revision,
                target.revision,
                "--",
            ]
        ).split("\0")
        if dirty:
            changed += self._read_git(
                ["ls-tree", "--name-only", "-r", "-z", original.revision]
            ).split("\0")
        for path in ignored:
            if path and any(
                name
                and (
                    path == name
                    or path.startswith(name + "/")
                    or name.startswith(path + "/")
                )
                for name in changed
            ):
                msg = f"ignored path obstructs target: {path}"
                raise ValueError(msg)

    def _owned_stash(self, token: RecoveryToken, record: preservation.Record) -> str:
        ref = f"refs/libvcs/preserve/{token.id}"
        saved = record["native"].get("oid")
        if saved:
            if self._oid(ref) != saved:
                msg = "owned Git preservation ref changed"
                raise ValueError(msg)
            candidates = [saved]
        else:
            entries = self._read_git(["stash", "list", "--format=%H%x00%gs%x00"]).split(
                "\0"
            )
            candidates = [
                entries[index].strip()
                for index in range(0, len(entries) - 1, 2)
                if entries[index + 1].endswith(": " + record["marker"])
            ]
        if len(candidates) != 1:
            msg = "owned Git stash is missing or ambiguous"
            raise ValueError(msg)
        oid = candidates[0]
        try:
            pinned = self._oid(ref)
        except exc.CommandError:
            pinned = None
        if pinned is not None and pinned != oid:
            msg = "owned Git preservation ref changed"
            raise ValueError(msg)
        subject = self._read_git(["show", "-s", "--format=%s", oid]).strip()
        if (
            not subject.endswith(": " + record["marker"])
            or self._oid(f"{oid}^1") != record["original"]["revision"]
        ):
            msg = "Git stash does not match capture identity"
            raise ValueError(msg)
        return str(oid)

    def _pin_stash(self, token: RecoveryToken, record: preservation.Record) -> str:
        oid = self._owned_stash(token, record)
        ref = f"refs/libvcs/preserve/{token.id}"
        try:
            existing = self._oid(ref)
        except exc.CommandError:
            self.cmd.run(
                ["update-ref", ref, oid, "0" * len(oid)], check_returncode=True
            )
        else:
            if existing != oid:
                msg = "owned preservation ref has a different object"
                raise ValueError(msg)
        record["native"] = {"oid": oid, "ref": ref}
        return oid

    def _conflicts(self, oid: str) -> tuple[SyncConflict, ...]:
        unmerged = self._read_git(["ls-files", "--unmerged", "-z"])
        paths: dict[str, str] = {}
        for entry in unmerged.split("\0"):
            if not entry:
                continue
            metadata, path = entry.split("\t", 1)
            blob = metadata.split(" ")[1]
            binary = "\0" in self._read_git(["cat-file", "blob", blob])
            paths[path] = "binary" if binary else paths.get(path, "text")
        try:
            unknown_tree = self._oid(f"{oid}^3")
        except exc.CommandError:
            pass
        else:
            unknown = self._read_git(
                ["ls-tree", "--name-only", "-r", "-z", unknown_tree]
            ).split("\0")
            tracked = set(self._read_git(["ls-files", "-z"]).split("\0"))
            paths.update(
                {
                    path: "untracked-obstruction"
                    for path in unknown
                    if path and path in tracked
                }
            )
        return tuple(
            SyncConflict(path, reason) for path, reason in sorted(paths.items())
        )

    def list_recoveries(self) -> tuple[SyncResult, ...]:
        """Find retained and interrupted saves without resuming an update."""
        store = self._store()
        with store.lock():
            results = store.discover()
            for result in results:
                assert result.recovery is not None
                if any(error.step == "recovery-record" for error in result.errors):
                    continue
                try:
                    self._owned_stash(result.recovery, store.read(result.recovery))
                except (
                    exc.LibVCSException,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                ) as error:
                    result.add_error("recovery-material", str(error), error)
            return results

    def update_repo(
        self,
        set_remotes: bool = False,
        *args: t.Any,
        target: SyncTarget | None = None,
        policy: SyncPolicy | None = None,
        **kwargs: t.Any,
    ) -> SyncResult:
        """Follow targets by fast-forward; abort on dirt unless explicitly permitted.

        Preserve retains an owned stash, even after indexed restoration. Recovery
        needs the retained local object database. Callers must exclude other VCS
        writers and editors throughout this operation.
        """
        result = SyncResult()
        policy = policy or SyncPolicy()
        step = "precondition"
        try:
            if target is None and self.rev is not None:
                target = SyncTarget(rev=self.rev)
            if not (self.path / ".git").exists():
                step = "obtain"
                self.obtain()
            store = self._store()
            with store.lock():
                active = store.repository / ".libvcs-preserve-active.json"
                if active.exists():
                    preservation.safe_path(active)
                    owner = json.loads(active.read_text())
                    owner_store = preservation.RecoveryStore(
                        pathlib.Path(owner["source"]), "git", store.repository
                    )
                    owner_token = RecoveryToken(**owner["token"])
                    result.recovery = owner_token
                    result.update_state = "unknown"
                    result.preservation_state = "unknown"
                    owner_record = owner_store.read(owner_token)
                    if owner_record["phase"] not in preservation.TERMINAL:
                        return owner_store.snapshot(owner_token, owner_record)
                    result = SyncResult()
                for retained in store.discover():
                    assert retained.recovery is not None
                    if any(
                        error.step == "recovery-record" for error in retained.errors
                    ):
                        return retained
                    retained_record = store.read(retained.recovery)
                    if retained_record["phase"] not in preservation.TERMINAL:
                        return retained
                dirty = self._precondition()
                original = self.get_position()
                step = "target"
                # Keep/warn only inspect metadata: these policies never fetch.
                if policy.drift != "follow":
                    resolved = self.resolve_target(target)
                    if original.revision != resolved.revision:
                        if policy.drift == "warn":
                            logger.warning(
                                "configured Git target drifted",
                                extra={
                                    "vcs_type": "git",
                                    "vcs_repo_path": str(self.path),
                                },
                            )
                        return result
                    return result
                if dirty and policy.dirty == "abort":
                    result.add_error("dirty", "working copy has local changes")
                    return result
                if set_remotes:
                    step = "set-remotes"
                    self.set_remotes(overwrite=True)
                step = "fetch"
                self.cmd.fetch(
                    all=True,
                    prune=True,
                    config={"http.sslVerify": False}
                    if not self.options.tls_verify
                    else None,
                    check_returncode=True,
                )
                step = "target"
                resolved = self.resolve_target(target)
                if not self._drifted(original, resolved):
                    if not dirty:
                        step = "submodule-update"
                        self._sync_submodules()
                    return result
                if resolved.follows:
                    branch_ref = f"refs/heads/{resolved.ref_name}"
                    try:
                        local = self._oid(branch_ref)
                    except exc.CommandError:
                        local = None
                    if local is not None:
                        if self._ancestor(resolved.revision, local):
                            resolved = dataclasses.replace(resolved, revision=local)
                        elif not self._ancestor(local, resolved.revision):
                            msg = "target diverges; fast-forward required"
                            raise ValueError(msg)  # noqa: TRY301 - return target error before capture
                target_tree = self._read_git(["ls-tree", "-r", "-z", resolved.revision])
                if dirty and any(
                    entry.startswith("160000 ") for entry in target_tree.split("\0")
                ):
                    msg = "target contains unsupported submodules"
                    raise ValueError(msg)  # noqa: TRY301 - reject before capture
                self._ignored_collisions(original, resolved, dirty=bool(dirty))
                if not dirty:
                    step = "submodule-preflight"
                    self._guard_submodules(resolved.revision)
                token: RecoveryToken | None = None
                record: preservation.Record | None = None
                if dirty and policy.dirty == "preserve":
                    step = "capture"
                    original_data = dataclasses.asdict(original)
                    original_data["status_paths"] = dirty
                    original_data["config"] = self._read_git(
                        ["config", "--local", "--list", "-z"]
                    )
                    token, record = store.create(
                        original=original_data, target=dataclasses.asdict(resolved)
                    )
                    result.recovery = token
                    result.preservation_state = "unknown"
                    try:
                        preservation.atomic_record(
                            active,
                            {
                                "source": str(store.source),
                                "token": dataclasses.asdict(token),
                            },
                        )
                        self.cmd.run(
                            [
                                "stash",
                                "push",
                                "--include-untracked",
                                "--message",
                                record["marker"],
                            ],
                            check_returncode=True,
                        )
                        self._pin_stash(token, record)
                        result.preservation_state = "saved"
                        store.phase(token, record, "sealed")
                    except (
                        exc.LibVCSException,
                        OSError,
                        ValueError,
                        RuntimeError,
                        KeyError,
                    ) as error:
                        result.add_error(step, str(error), error)
                        try:
                            self._pin_stash(token, record)
                            result.preservation_state = "saved"
                        except (
                            exc.LibVCSException,
                            OSError,
                            ValueError,
                            RuntimeError,
                            KeyError,
                        ) as inspection:
                            result.add_error(
                                "capture-inspection", str(inspection), inspection
                            )
                        self._finish_git(store, token, record, result)
                        return result
                try:
                    step = "update"
                    if token is not None and record is not None:
                        store.phase(token, record, "updating")
                    if dirty and policy.dirty == "discard":
                        self.cmd.run(["reset", "--hard", "HEAD"], check_returncode=True)
                        self.cmd.run(["clean", "-fd"], check_returncode=True)
                    step = "update"
                    result.update_state = "unknown"
                    if resolved.follows:
                        if (
                            original.ref_kind != "branch"
                            or original.ref_name != resolved.ref_name
                        ):
                            try:
                                self._oid(f"refs/heads/{resolved.ref_name}")
                            except exc.CommandError:
                                self.cmd.run(
                                    [
                                        "checkout",
                                        "--no-overwrite-ignore",
                                        "-b",
                                        resolved.ref_name,
                                        resolved.revision,
                                        "--",
                                    ],
                                    check_returncode=True,
                                )
                            else:
                                self.cmd.run(
                                    [
                                        "checkout",
                                        "--no-overwrite-ignore",
                                        resolved.ref_name,
                                        "--",
                                    ],
                                    check_returncode=True,
                                )
                        self.cmd.run(
                            [
                                "merge",
                                "--ff-only",
                                "--no-overwrite-ignore",
                                resolved.revision,
                            ],
                            check_returncode=True,
                        )
                    else:
                        self.cmd.run(
                            [
                                "checkout",
                                "--no-overwrite-ignore",
                                "--detach",
                                resolved.revision,
                            ],
                            check_returncode=True,
                        )
                    result.update_state = "completed"
                    if not dirty:
                        step = "submodule-update"
                        self._sync_submodules()
                except (
                    exc.LibVCSException,
                    OSError,
                    ValueError,
                    RuntimeError,
                    KeyError,
                ) as error:
                    if result.update_state == "unknown":
                        result.update_state = "failed"
                    result.add_error(step, str(error), error)
                if token is not None and record is not None:
                    try:
                        store.phase(token, record, "inspecting")
                        self.cmd.run(
                            ["stash", "apply", "--index", record["native"]["oid"]],
                            check_returncode=True,
                        )
                        result.preservation_state = "restored"
                    except (
                        exc.LibVCSException,
                        OSError,
                        ValueError,
                        RuntimeError,
                        KeyError,
                    ) as error:
                        result.preservation_state = "failed"
                        result.add_error("restore", str(error), error)
                    try:
                        result.conflicts = self._conflicts(record["native"]["oid"])
                        if result.conflicts:
                            result.preservation_state = "conflicted"
                            result.add_error(
                                "conflicts",
                                "indexed restoration has unresolved conflicts",
                            )
                    except (
                        exc.LibVCSException,
                        OSError,
                        ValueError,
                        RuntimeError,
                        KeyError,
                    ) as error:
                        result.preservation_state = "unknown"
                        result.add_error("inspection", str(error), error)
                    self._finish_git(store, token, record, result)
        except (
            exc.LibVCSException,
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            TypeError,
        ) as error:
            result.add_error(step, str(error), error)
        return result

    @staticmethod
    def _drifted(original: WorkingCopyPosition, target: WorkingCopyPosition) -> bool:
        return (
            original.revision != target.revision
            or (
                target.follows
                and (
                    original.ref_kind != "branch"
                    or original.ref_name != target.ref_name
                )
            )
            or (not target.follows and original.follows)
        )

    def _ancestor(self, older: str, newer: str) -> bool:
        try:
            self._read_git(["merge-base", "--is-ancestor", older, newer])
        except exc.CommandError as error:
            if error.returncode != 1:
                raise
            return False
        return True

    @staticmethod
    def _finish_git(
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
        result: SyncResult,
    ) -> None:
        try:
            store.finish(token, record, result)
        except (
            exc.LibVCSException,
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            TypeError,
        ) as error:
            result.add_error("publication", str(error), error)

    def recover_changes(
        self, token: RecoveryToken, *, destination: StrPath
    ) -> SyncResult:
        """Recover the original base and indexed changes using retained local objects.

        The destination is independent; missing source objects fail recovery without
        fetching from a remote. The token remains available for another recovery.
        """
        result = SyncResult(recovery=token, preservation_state="unknown")
        try:
            store = self._store()
            with store.lock():
                record = store.read(token)
                store.validate_source(record)
                dest = store.destination(destination)
                oid = self._owned_stash(token, record)
                # Verify the full object closure offline before any destination write.
                self._read_git(["rev-list", "--objects", "--missing=error", oid])
                self._read_git(["init", str(dest)], path=dest.parent)
                self._read_git(
                    [
                        "-c",
                        "protocol.file.allow=always",
                        "fetch",
                        "--no-tags",
                        str(store.repository),
                        oid,
                    ],
                    path=dest,
                )
                original = record["original"]
                checkout = ["checkout", "--no-overwrite-ignore"]
                if original["ref_kind"] == "branch":
                    checkout += ["-b", original["ref_name"]]
                else:
                    checkout += ["--detach"]
                self._read_git([*checkout, original["revision"]], path=dest)
                self._read_git(["stash", "apply", "--index", oid], path=dest)
                for item in original["config"].split("\0"):
                    key, separator, value = item.partition("\n")
                    if separator and (
                        key.startswith(("remote.", f"branch.{original['ref_name']}."))
                    ):
                        self._read_git(["config", "--add", key, value], path=dest)
                result.preservation_state = "restored"
        except (
            exc.LibVCSException,
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            TypeError,
        ) as error:
            result.preservation_state = "failed"
            result.add_error("recovery", str(error), error)
        return result

    def release_changes(self, token: RecoveryToken) -> None:
        """Release the exact owned ref and stash entry, retaining ambiguous material."""
        store = self._store()
        with store.lock():
            record = store.read(token)
            store.validate_source(record)
            oid = self._owned_stash(token, record)
            entries = self._read_git(["stash", "list", "--format=%H%x00%gs%x00"]).split(
                "\0"
            )
            matches = [
                index // 2
                for index in range(0, len(entries) - 1, 2)
                if entries[index].strip() == oid
                and entries[index + 1].endswith(": " + record["marker"])
            ]
            if len(matches) > 1:
                msg = "ambiguous owned stash entries"
                raise ValueError(msg)
            if matches:
                selector = f"stash@{{{matches[0]}}}"
                if self._oid(selector) != oid:
                    msg = "owned stash entry changed during release"
                    raise ValueError(msg)
                self.cmd.run(["stash", "drop", selector], check_returncode=True)
            try:
                pinned = self._oid(f"refs/libvcs/preserve/{token.id}")
            except exc.CommandError:
                pinned = None
            if pinned is not None:
                if pinned != oid:
                    msg = "owned preservation ref changed"
                    raise ValueError(msg)
                self.cmd.run(
                    ["update-ref", "-d", f"refs/libvcs/preserve/{token.id}", oid],
                    check_returncode=True,
                )
            active = store.repository / ".libvcs-preserve-active.json"
            if active.exists():
                preservation.safe_path(active)
                owner = json.loads(active.read_text())
                if owner.get("token") == dataclasses.asdict(token):
                    active.unlink()
                    preservation.flush_directory(store.repository)
            store.remove(token)

    def get_position(self) -> WorkingCopyPosition:
        """Read HEAD without fetching; detached commits do not follow updates."""
        revision = self.cmd.run(["rev-parse", "--verify", "HEAD"]).strip()
        try:
            branch = self.cmd.run(
                ["symbolic-ref", "--quiet", "HEAD"],
                check_returncode=True,
            ).strip()
        except exc.CommandError as error:
            if error.returncode != 1:
                raise
        else:
            return WorkingCopyPosition(
                revision,
                branch.removeprefix("refs/heads/"),
                "branch",
                follows=True,
            )
        return WorkingCopyPosition(revision, revision, "commit", follows=False)

    def remotes(self) -> GitSyncRemoteDict:
        """Return remotes like git remote -v.

        Parameters
        ----------
        flat : bool
            Return a dict of ``tuple`` instead of ``dict``, default `False`.

        Returns
        -------
        dict of git upstream / remote URLs
        """
        remotes = {}

        ret = self.cmd.remotes.ls()

        for r in ret:
            # FIXME: Cast to the GitRemote that sync uses, for now
            remote = self.remote(r.remote_name)
            if remote is not None:
                remotes[r.remote_name] = remote
        return remotes

    def remote(self, name: str, **kwargs: t.Any) -> GitRemote | None:
        """Get the fetch and push URL for a specified remote name.

        Parameters
        ----------
        name : str
            The remote name used to define the fetch and push URL

        Returns
        -------
        Remote name and url in tuple form

        Notes
        -----
        Uses ``git remote -v`` via the remote manager rather than
        ``git remote show -n``. ``git remote show`` also enumerates every
        remote-tracking ref, which pipes thousands of lines through the
        subprocess progress callback for repositories with large branch
        counts (e.g. ``openai/codex`` at 2,400+ refs) and can appear to
        hang. ``git remote -v`` is O(remotes) and cannot block on ref
        enumeration. The remote manager is uncached -- each call shells
        out -- so repeated calls in a loop will still spawn one
        subprocess apiece.

        Subprocess failures from the underlying ``git remote -v`` are
        suppressed and returned as ``None`` to preserve the resilience
        contract callers relied on with the previous ``git remote show``
        path (which wrapped the same call in ``try / except
        LibVCSException``).
        """
        try:
            remote_cmd = self.cmd.remotes.get(remote_name=name, default=None)
        except exc.LibVCSException:
            return None
        if remote_cmd is None:
            return None

        fetch_url = (remote_cmd.fetch_url or "").strip()
        if not fetch_url:
            return None

        # When no explicit ``remote.<name>.pushurl`` is set, git itself falls
        # back to the fetch URL -- mirror that so callers always see a URL.
        push_url = (remote_cmd.push_url or fetch_url).strip()

        return GitRemote(
            name=name,
            fetch_url=fetch_url,
            push_url=push_url,
        )

    def set_remote(
        self,
        name: str,
        url: str,
        push: bool = False,
        overwrite: bool = False,
    ) -> GitRemote:
        """Set remote with name and URL like git remote add.

        Parameters
        ----------
        name : str
            defines the remote name.

        url : str
            defines the remote URL
        """
        url = self.chomp_protocol(url)
        remote_cmd = self.cmd.remotes.get(remote_name=name, default=None)

        if remote_cmd is not None and overwrite:
            remote_cmd.set_url(url=url, push=push, check_returncode=True)
        else:
            self.cmd.remotes.add(name=name, url=url, check_returncode=True)

        remote = self.remote(name=name)
        if remote is None:
            raise GitRemoteSetError(remote_name=name)
        return remote

    @staticmethod
    def chomp_protocol(url: str) -> str:
        """Return clean VCS url from RFC-style url.

        Parameters
        ----------
        url : str
            PIP-style url

        Returns
        -------
        URL as VCS software would accept it
        """
        if "+" in url:
            url = url.split("+", 1)[1]
        scheme, netloc, path, query, _frag = urlparse.urlsplit(url)
        url = urlparse.urlunsplit((scheme, netloc, path, query, ""))
        if url.startswith("ssh://git@github.com/"):
            url = url.replace("ssh://", "git+ssh://")
        elif "://" not in url:
            assert "file:" not in url
            url = url.replace("git+", "git+ssh://")
            url = url.replace("ssh://", "")
        return url

    def get_git_version(self) -> str:
        """Return current version of git binary.

        Returns
        -------
        git version
        """
        VERSION_PFX = "git version "
        version = self.cmd.version()
        if version.startswith(VERSION_PFX):
            version = version[len(VERSION_PFX) :].split()[0]
        else:
            version = ""
        return ".".join(version.split(".")[:3])

    def status(self) -> GitStatus:
        """Retrieve status of project in dict format.

        Wraps ``git status --sb --porcelain=2``. Does not include changed files, yet.

        Returns
        -------
        Status of current checked out repository

        Examples
        --------
        >>> git_repo = GitSync(
        ...     url=f'file://{create_git_remote_repo()}',
        ...     path=tmp_path
        ... )
        >>> git_repo.obtain()
        >>> git_repo.status()
        GitStatus(\
branch_oid='...', branch_head='master', \
branch_upstream='origin/master', \
branch_ab='+0 -0', \
branch_ahead='0', \
branch_behind='0'\
)
        """
        return GitStatus.from_stdout(
            self.cmd.status(short=True, branch=True, porcelain="2"),
        )

    def get_current_remote_name(self) -> str:
        """Retrieve name of the remote / upstream of currently checked out branch.

        Returns
        -------
        If upstream the same, returns ``branch_name``.
        If upstream mismatches, returns ``remote_name/branch_name``.
        """
        match = self.status()

        if match.branch_upstream is None:  # no upstream set
            if match.branch_head is None:
                raise GitNoBranchFound
            return match.branch_head
        if match.branch_head is None:
            return match.branch_upstream

        return match.branch_upstream.replace("/" + match.branch_head, "")
