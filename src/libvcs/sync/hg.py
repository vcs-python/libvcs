"""Tool to manage a local hg (Mercurial) working copy from a repository.

.. todo::

   The following is from pypa/pip (MIT license):

   - :meth:`~libvcs.sync.base.BaseSync.from_pip_url`
   - :meth:`~libvcs.sync.hg.HgSync.get_revision`
"""  # E5

from __future__ import annotations

import configparser
import dataclasses
import json
import logging
import os
import pathlib
import re
import shutil
import typing as t

from libvcs import exc
from libvcs._internal import preservation
from libvcs._internal.run import ProgressCallbackProtocol
from libvcs._internal.subprocess import SubprocessCommand
from libvcs._internal.types import StrPath
from libvcs.cmd.hg import Hg

from .base import (
    BaseSync,
    RecoveryToken,
    SyncConflict,
    SyncPolicy,
    SyncResult,
    SyncTarget,
    WorkingCopyPosition,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class HgOptions:
    """Backend-specific options for Mercurial synchronization."""

    ssh: str | None = None
    remote_cmd: str | None = None
    pull: bool = False
    stream: bool = False
    tls_verify: bool = True

    def __post_init__(self) -> None:
        """Validate Mercurial option types without running Mercurial."""
        for name in ("ssh", "remote_cmd"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                msg = f"{name} must be a string or None"
                raise TypeError(msg)
            if value is not None and "\0" in value:
                msg = f"{name} must not contain NUL"
                raise ValueError(msg)
        for name in ("pull", "stream", "tls_verify"):
            if not isinstance(getattr(self, name), bool):
                msg = f"{name} must be a boolean"
                raise TypeError(msg)


class HgSync(BaseSync):
    """Tool to manage a local hg (Mercurial) repository cloned from a remote one."""

    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")
    cmd: Hg
    options_type = HgOptions

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        options: HgOptions | None = None,
        progress_callback: ProgressCallbackProtocol | None = None,
        rev: str | None = None,
    ) -> None:
        """Local Mercurial repository.

        Parameters
        ----------
        url : str
            Mercurial repository URL.
        """
        if options is None:
            options = HgOptions()
        elif not isinstance(options, HgOptions):
            msg = "options must be an HgOptions instance"
            raise TypeError(msg)
        self.options = options
        super().__init__(
            url=url.removeprefix("hg+"),
            path=path,
            progress_callback=progress_callback,
            rev=rev,
        )

        self.cmd = Hg(path=path, progress_callback=self.progress_callback)

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Clone and update a Mercurial repository to this location."""
        if self.rev is not None:
            SyncTarget(rev=self.rev)
        self.cmd.clone(
            no_update=True,
            quiet=True,
            url=self.url,
            ssh=self.options.ssh,
            remote_cmd=self.options.remote_cmd,
            pull=self.options.pull,
            stream=self.options.stream,
            insecure=not self.options.tls_verify,
            check_returncode=True,
        )
        if self.rev is None:
            self.cmd.update(quiet=True, check_returncode=True)
        else:
            self.cmd.run(
                ["update", "--quiet", "--rev", self.rev], check_returncode=True
            )

    def get_revision(self) -> str:
        """Get latest revision of this mercurial repository."""
        return self.run(["parents", "--template={rev}"])

    def get_position(self) -> WorkingCopyPosition:
        """Read the parent and active bookmark or named branch without pulling."""
        revision, bookmark = self.cmd.run(
            ["log", "-r", ".", "-T", "{node}\\0{activebookmark}"],
        ).split("\0")
        if bookmark:
            return WorkingCopyPosition(revision, bookmark, "bookmark", follows=True)
        branch = self.cmd.run(["branch"]).strip()
        return WorkingCopyPosition(revision, branch, "branch", follows=True)

    def _read_hg(self, args: list[str], *, path: pathlib.Path | None = None) -> str:
        command = SubprocessCommand(
            ["hg", *args],
            cwd=path or self.path,
            env={**os.environ, "HGPLAIN": "1", "HGENCODING": "utf-8"},
        )
        completed = command.run(capture_output=True, check=False)
        if completed.returncode:
            raise exc.CommandError(
                cmd=["hg", *args],
                returncode=completed.returncode,
                output=os.fsdecode(completed.stderr),
            )
        return os.fsdecode(completed.stdout)

    def _node(self, selector: str) -> str:
        nodes = self._read_hg(
            ["log", "--rev", selector, "--template", "{node}\\0"]
        ).split("\0")
        nodes = [node for node in nodes if node]
        if len(nodes) != 1 or re.fullmatch(r"[0-9a-f]{40}", nodes[0]) is None:
            msg = "Mercurial target is unavailable or ambiguous"
            raise ValueError(msg)
        return nodes[0]

    def resolve_target(self, target: SyncTarget | None = None) -> WorkingCopyPosition:
        """Resolve available bookmarks, named branches, tags, or changesets locally."""
        if target is None and self.rev is not None:
            target = SyncTarget(rev=self.rev)
        if target is not None and target.remote is not None:
            msg = "Mercurial target remote qualifiers are not supported"
            raise ValueError(msg)
        current = self.get_position()
        if target is None:
            name = current.ref_name
            if current.ref_kind == "branch":
                name = self._read_hg(["log", "-r", ".", "-T", "{branch}"])
            target = SyncTarget(branch=name)
        if target.branch is not None:
            name = target.branch
            bookmarks = json.loads(self._read_hg(["bookmarks", "-Tjson"]))
            for bookmark in bookmarks:
                if bookmark["bookmark"] == name:
                    return WorkingCopyPosition(
                        bookmark["node"], name, "bookmark", follows=True
                    )
            quoted = name.replace("\\", "\\\\").replace("'", "\\'")
            node = self._node(f"heads(branch('{quoted}'))")
            return WorkingCopyPosition(node, name, "branch", follows=True)
        if target.tag is not None:
            for tag in json.loads(self._read_hg(["tags", "-Tjson"])):
                if tag["tag"] == target.tag:
                    return WorkingCopyPosition(
                        tag["node"], target.tag, "tag", follows=False
                    )
            msg = "Mercurial tag is unavailable"
            raise ValueError(msg)
        selector = target.commit if target.commit is not None else str(target.rev)
        if (
            target.rev is not None
            and not selector.isdecimal()
            and re.fullmatch(r"[0-9a-f]{6,40}", selector) is None
        ):
            for named in (SyncTarget(branch=selector), SyncTarget(tag=selector)):
                try:
                    return self.resolve_target(named)
                except (ValueError, exc.CommandError):  # noqa: PERF203 - native ref lookup
                    continue
        node = self._node(selector)
        return WorkingCopyPosition(node, node, "commit", follows=False)

    def _status(self, *, ignored: bool = False) -> dict[str, str]:
        flags = (
            ["--ignored"]
            if ignored
            else ["--modified", "--added", "--removed", "--deleted", "--unknown"]
        )
        entries = self._read_hg(["status", "-0", *flags]).split("\0")
        status = {}
        for entry in entries:
            if not entry:
                continue
            if len(entry) < 3 or entry[1] != " " or entry[0] not in "MAR!?I":
                msg = "invalid Mercurial status output"
                raise ValueError(msg)
            self._work_path(entry[2:])
            status[entry[2:]] = entry[0]
        return status

    def is_dirty(self) -> bool:
        """Read native schedules, modifications, missing paths, and unknown files."""
        return bool(self._status()) or self._read_hg(
            ["branch"]
        ).strip() != self._read_hg(["log", "-r", ".", "-T", "{branch}"])

    def _work_path(self, relative: str) -> pathlib.Path:
        name = pathlib.PurePosixPath(relative)
        if not relative or name.is_absolute() or ".." in name.parts:
            msg = "unsafe Mercurial working-copy path"
            raise ValueError(msg)
        path = self.path / name
        preservation.safe_path(path.parent)
        return path

    def _store(self) -> preservation.RecoveryStore:
        return preservation.RecoveryStore(self.path, "hg", self.path / ".hg")

    def _precondition(self) -> dict[str, str]:
        if pathlib.Path(self._read_hg(["root"]).strip()) != self.path.absolute():
            msg = "Mercurial synchronization requires the working-copy root"
            raise ValueError(msg)
        for name in (
            "wlock",
            "store/lock",
            "shelvedstate",
            "rebasestate",
            "histedit-state",
            "graftstate",
            "updatestate",
            "merge/state",
            "merge/state2",
            "sharedpath",
        ):
            path = self.path / ".hg" / name
            if path.exists() or path.is_symlink():
                msg = f"native Mercurial activity or unsupported layout: {name}"
                raise ValueError(msg)
        parents = self._read_hg(["parents", "--template", "{node}\\0"]).split("\0")
        if len([node for node in parents if node]) != 1:
            msg = "Mercurial preservation requires exactly one committed parent"
            raise ValueError(msg)
        if (self.path / ".hgsub").exists() or (self.path / ".hgsubstate").exists():
            msg = "Mercurial subrepositories are outside the preservation scope"
            raise ValueError(msg)
        for directory, dirs, files in os.walk(self.path, followlinks=False):
            if pathlib.Path(directory) != self.path and any(
                name in dirs or name in files for name in (".hg", ".git", ".svn")
            ):
                msg = "nested repository prevents Mercurial synchronization"
                raise ValueError(msg)
            dirs[:] = [name for name in dirs if name not in (".hg", ".git", ".svn")]
        return self._status()

    def _manifest(self, node: str) -> dict[str, preservation.Record]:
        return {
            entry["path"]: entry
            for entry in json.loads(
                self._read_hg(["manifest", "--rev", node, "--debug", "-Tjson"])
            )
        }

    def _ignored_collisions(self, original: str, target: str, *, dirty: bool) -> None:
        before, after = self._manifest(original), self._manifest(target)
        if ".hgsub" in after or ".hgsubstate" in after:
            msg = "target contains unsupported Mercurial subrepositories"
            raise ValueError(msg)
        writes = {name for name, item in after.items() if before.get(name) != item}
        if dirty:
            writes.update(before)
        for path in self._status(ignored=True):
            if any(
                path == name
                or path.startswith(name + "/")
                or name.startswith(path + "/")
                for name in writes
            ):
                msg = f"ignored path obstructs Mercurial update: {path}"
                raise ValueError(msg)

    @staticmethod
    def _shelf_name(token: RecoveryToken) -> str:
        return f"libvcs-{token.id}"

    def _record(
        self, store: preservation.RecoveryStore, token: RecoveryToken
    ) -> preservation.Record:
        record = store.read(token)
        original = record["original"]
        revision = original.get("revision")
        status = original.get("status")
        if (
            not isinstance(revision, str)
            or re.fullmatch(r"[0-9a-f]{40}", revision) is None
            or not isinstance(status, dict)
        ):
            msg = "invalid Mercurial recovery record identity or status"
            raise ValueError(msg)
        for name, value in status.items():
            if (
                not isinstance(name, str)
                or not isinstance(value, str)
                or value not in {"M", "A", "R", "!", "?"}
            ):
                msg = "invalid Mercurial recovery record status entry"
                raise ValueError(msg)
            self._work_path(name)
        for field in ("missing_added", "recreated"):
            values = original.get(field, {})
            if not isinstance(values, dict):
                msg = "invalid Mercurial recovery schedule"
                raise ValueError(msg)  # noqa: TRY004 - persisted record validation
            for name, value in values.items():
                if not isinstance(name, str) or not isinstance(value, str):
                    msg = "invalid Mercurial recovery schedule entry"
                    raise ValueError(msg)  # noqa: TRY004 - persisted record validation
                self._work_path(name)
                if field == "missing_added":
                    if status.get(name) != "!":
                        msg = "missing addition does not match native status"
                        raise ValueError(msg)
                    if value:
                        self._work_path(value)
                elif status.get(name) != "R" or not value.isdecimal():
                    msg = "recreated removal does not match native status"
                    raise ValueError(msg)
        for field in ("branch", "ref_name", "default"):
            if not isinstance(original.get(field), str) or "\0" in original[field]:
                msg = "invalid Mercurial recovery record metadata"
                raise ValueError(msg)
        if (
            original.get("ref_kind") not in ("branch", "bookmark")
            or type(original.get("pending_branch")) is not bool
        ):
            msg = "invalid Mercurial recovery record branch metadata"
            raise ValueError(msg)
        return record

    def _shelf_files(
        self, token: RecoveryToken, record: preservation.Record
    ) -> pathlib.Path:
        directory = self.path / ".hg" / "shelved"
        name = self._shelf_name(token)
        for suffix in (".hg", ".patch"):
            path = preservation.safe_path(directory / (name + suffix))
            if not path.is_file():
                msg = "retained Mercurial shelf is incomplete or unavailable"
                raise ValueError(msg)
        patch = (directory / (name + ".patch")).read_bytes()
        if ("\n" + record["marker"] + "\n").encode() not in patch or (
            "# Parent  " + record["original"]["revision"]
        ).encode() not in patch:
            msg = "Mercurial shelf does not match capture identity"
            raise ValueError(msg)
        return directory

    def _needs_shelf(self, record: preservation.Record) -> bool:
        return any(
            value != "!" and name not in record["original"].get("recreated", {})
            for name, value in record["original"]["status"].items()
        )

    def _capture_recreated(
        self,
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
    ) -> None:
        recreated = record["original"]["recreated"]
        if not recreated:
            return
        material = store.token_path(token) / "recreated"
        material.mkdir(mode=0o700)
        for name, item in recreated.items():
            source = self._work_path(name)
            destination = material / item
            shutil.copy2(source, destination, follow_symlinks=False)
            if not destination.is_symlink():
                with destination.open("rb") as stream:
                    os.fsync(stream.fileno())
        record["native"]["recreated_inventory"] = preservation.inventory(material)
        preservation.flush_directory(material)
        store.write(token, record)

    def _restore_recreated(
        self,
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
    ) -> tuple[SyncConflict, ...]:
        recreated = record["original"].get("recreated", {})
        if not recreated:
            return ()
        self._material(store, token, record)
        conflicts = []
        status = self._status()
        before = self._manifest(record["original"]["revision"])
        after = self._manifest(self._node("."))
        for name, item in recreated.items():
            path = self._work_path(name)
            if before.get(name) != after.get(name) or status.get(name) is not None:
                conflicts.append(SyncConflict(name, "tree"))
                continue
            self.cmd.run(["remove", "--", name], check_returncode=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                store.token_path(token) / "recreated" / item,
                path,
                follow_symlinks=False,
            )
        return tuple(conflicts)

    def _seal(
        self,
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
    ) -> None:
        material = store.token_path(token) / "material"
        material.mkdir(mode=0o700, exist_ok=False)
        if self._needs_shelf(record):
            source = self._shelf_files(token, record)
            for suffix in (".hg", ".patch", ".shelve"):
                path = preservation.safe_path(
                    source / (self._shelf_name(token) + suffix)
                )
                if not path.exists():
                    continue
                destination = material / path.name
                shutil.copy2(path, destination)
                with destination.open("rb") as stream:
                    os.fsync(stream.fileno())
        preservation.flush_directory(material)
        record["native"]["inventory"] = preservation.inventory(material)
        store.phase(token, record, "sealed")

    def _material(
        self,
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
    ) -> pathlib.Path | None:
        if record["original"].get("recreated"):
            recreated = preservation.safe_path(store.token_path(token) / "recreated")
            if not recreated.is_dir() or preservation.inventory(recreated) != record[
                "native"
            ].get("recreated_inventory"):
                msg = "retained recreated Mercurial files are incomplete or corrupt"
                raise ValueError(msg)
        if "inventory" in record["native"]:
            material = preservation.safe_path(store.token_path(token) / "material")
            if (
                not material.is_dir()
                or preservation.inventory(material) != record["native"]["inventory"]
            ):
                msg = "retained Mercurial shelf checksum mismatch"
                raise ValueError(msg)
            return material
        if self._needs_shelf(record):
            return self._shelf_files(token, record)
        return None

    def _unshelve(self, token: RecoveryToken, *, backup: pathlib.Path) -> None:
        self.cmd.run(
            [
                "--config",
                f"ui.origbackuppath={backup}",
                "--config",
                "merge.checkignored=abort",
                "--config",
                "ui.interactive=false",
                "unshelve",
                "--keep",
                "--name",
                self._shelf_name(token),
                "--tool",
                "internal:merge",
            ],
            check_returncode=True,
        )

    def _conflicts(self) -> tuple[SyncConflict, ...]:
        entries = json.loads(self._read_hg(["resolve", "--list", "-Tjson"]))
        return tuple(
            SyncConflict(entry["path"], "text")
            for entry in entries
            if entry["mergestatus"] == "U"
        )

    def _restore_missing(
        self, original: preservation.Record, target: str
    ) -> tuple[SyncConflict, ...]:
        missing = [name for name, status in original["status"].items() if status == "!"]
        if not missing:
            return ()
        before = self._manifest(original["revision"])
        after = self._manifest(target)
        conflicts = []
        for name in missing:
            path = self._work_path(name)
            if before.get(name) != after.get(name):
                conflicts.append(SyncConflict(name, "missing-intent-upstream-changed"))
            elif name in original.get("missing_added", {}):
                if path.exists() or path.is_symlink():
                    conflicts.append(SyncConflict(name, "untracked-obstruction"))
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=False)
                try:
                    source = original["missing_added"][name]
                    args = (
                        ["copy", "--after", "--", source, name]
                        if source
                        else ["add", "--", name]
                    )
                    self.cmd.run(args, check_returncode=True)
                finally:
                    path.unlink()
            elif path.is_file() or path.is_symlink():
                path.unlink()
            elif path.exists():
                conflicts.append(SyncConflict(name, "tree"))
        return tuple(conflicts)

    @staticmethod
    def _finish(
        store: preservation.RecoveryStore,
        token: RecoveryToken,
        record: preservation.Record,
        result: SyncResult,
    ) -> None:
        try:
            store.finish(token, record, result)
        except (OSError, ValueError, TypeError) as error:
            result.add_error("publication", str(error), error)

    def list_recoveries(self) -> tuple[SyncResult, ...]:
        """List retained and interrupted shelves without replaying their operations."""
        store = self._store()
        with store.lock():
            results = store.discover()
            for result in results:
                assert result.recovery is not None
                if any(error.step == "recovery-record" for error in result.errors):
                    continue
                try:
                    self._material(
                        store, result.recovery, self._record(store, result.recovery)
                    )
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    KeyError,
                    exc.LibVCSException,
                ) as error:
                    result.add_error("recovery-material", str(error), error)
            return results

    def update_repo(
        self,
        *args: t.Any,
        target: SyncTarget | None = None,
        policy: SyncPolicy | None = None,
        **kwargs: t.Any,
    ) -> SyncResult:
        """Pull without updating, then apply explicit target and dirty policy.

        Preservation retains a checksummed native shelf and recovery token after
        success or failure. Callers must exclude external writers and editors.
        """
        result = SyncResult()
        policy = policy or SyncPolicy()
        step = "precondition"
        try:
            if target is None and self.rev is not None:
                target = SyncTarget(rev=self.rev)
            if not (self.path / ".hg").exists():
                step = "obtain"
                self.obtain()
            store = self._store()
            with store.lock():
                for retained in store.discover():
                    assert retained.recovery is not None
                    if any(
                        error.step == "recovery-record" for error in retained.errors
                    ):
                        return retained
                    try:
                        retained_record = self._record(store, retained.recovery)
                    except (OSError, ValueError, TypeError, KeyError) as error:
                        retained.add_error("recovery-record", str(error), error)
                        return retained
                    if retained_record["phase"] not in preservation.TERMINAL:
                        return retained
                status = self._precondition()
                original = self.get_position()
                branch = self._read_hg(["branch"]).strip()
                pending_branch = branch != self._read_hg(
                    ["log", "-r", ".", "-T", "{branch}"]
                )
                dirty = bool(status) or pending_branch
                step = "target"
                if policy.drift != "follow":
                    resolved = self.resolve_target(target)
                    if (
                        original.revision != resolved.revision
                        and policy.drift == "warn"
                    ):
                        logger.warning(
                            "configured Mercurial target drifted",
                            extra={
                                "vcs_event": "target_drift",
                                "vcs_type": "hg",
                                "vcs_repo_path": str(self.path),
                            },
                        )
                    return result
                if dirty and policy.dirty == "abort":
                    result.add_error(
                        "dirty", "Mercurial working copy has local changes"
                    )
                    return result
                step = "pull"
                self.cmd.pull(
                    update=False,
                    ssh=self.options.ssh,
                    remote_cmd=self.options.remote_cmd,
                    insecure=not self.options.tls_verify,
                    check_returncode=True,
                )
                step = "target"
                resolved = self.resolve_target(target)
                attachment_changed = resolved.follows and (
                    original.ref_kind != resolved.ref_kind
                    or original.ref_name != resolved.ref_name
                )
                if original.revision == resolved.revision and not attachment_changed:
                    return result
                self._ignored_collisions(
                    original.revision, resolved.revision, dirty=dirty
                )
                token: RecoveryToken | None = None
                record: preservation.Record | None = None
                if dirty and policy.dirty == "preserve":
                    step = "capture"
                    manifest = self._manifest(original.revision)
                    schedules = json.loads(
                        self._read_hg(["status", "--copies", "-Tjson"])
                    )
                    missing_added = {
                        item["path"]: item.get("source", "")
                        for item in schedules
                        if item["status"] == "!" and item["path"] not in manifest
                    }
                    recreated = {
                        name: str(index)
                        for index, (name, state) in enumerate(status.items())
                        if state == "R"
                        and (
                            self._work_path(name).exists()
                            or self._work_path(name).is_symlink()
                        )
                    }
                    original_data = dataclasses.asdict(original)
                    original_data.update(
                        status=status,
                        missing_added=missing_added,
                        recreated=recreated,
                        branch=branch,
                        pending_branch=pending_branch,
                        default=self.url,
                    )
                    token, record = store.create(
                        original=original_data, target=dataclasses.asdict(resolved)
                    )
                    result.recovery = token
                    result.preservation_state = "unknown"
                    try:
                        backup = store.token_path(token) / "backups"
                        self._capture_recreated(store, token, record)
                        if self._needs_shelf(record):
                            self.cmd.run(
                                [
                                    "--config",
                                    f"ui.origbackuppath={backup}",
                                    "--config",
                                    "merge.checkignored=abort",
                                    "shelve",
                                    "--unknown",
                                    "--name",
                                    self._shelf_name(token),
                                    "--message",
                                    record["marker"],
                                    *[
                                        argument
                                        for name in recreated
                                        for argument in ("--exclude", "path:" + name)
                                    ],
                                ],
                                check_returncode=True,
                            )
                        self._seal(store, token, record)
                        result.preservation_state = "saved"
                    except (
                        OSError,
                        ValueError,
                        TypeError,
                        KeyError,
                        exc.LibVCSException,
                    ) as error:
                        result.add_error("capture", str(error), error)
                        try:
                            if (
                                "inventory" not in record["native"]
                                and not (store.token_path(token) / "material").exists()
                            ):
                                self._seal(store, token, record)
                            self._material(store, token, record)
                            result.preservation_state = "saved"
                        except (
                            OSError,
                            ValueError,
                            TypeError,
                            KeyError,
                            exc.LibVCSException,
                        ) as inspection:
                            result.add_error(
                                "capture-inspection", str(inspection), inspection
                            )
                        self._finish(store, token, record, result)
                        return result
                step = "update"
                if token is not None and record is not None:
                    store.phase(token, record, "updating")
                try:
                    if token is not None and record is not None:
                        missing = [
                            name
                            for name, state in status.items()
                            if state == "!" or name in record["original"]["recreated"]
                        ]
                        if missing:
                            self.cmd.run(
                                [
                                    "revert",
                                    "--no-backup",
                                    "--rev",
                                    original.revision,
                                    "--",
                                    *missing,
                                ],
                                check_returncode=True,
                            )
                    if dirty and policy.dirty == "discard":
                        self.cmd.run(
                            [
                                "revert",
                                "--all",
                                "--no-backup",
                                "--rev",
                                original.revision,
                            ],
                            check_returncode=True,
                        )
                        for name, state in status.items():
                            if state in {"?", "A"}:
                                path = self._work_path(name)
                                if path.is_file() or path.is_symlink():
                                    path.unlink()
                    result.update_state = "unknown"
                    self.cmd.run(
                        [
                            "--config",
                            "merge.checkignored=abort",
                            "--config",
                            "ui.interactive=false",
                            "update",
                            "--rev",
                            resolved.revision,
                        ],
                        check_returncode=True,
                    )
                    result.update_state = "completed"
                    if resolved.ref_kind == "bookmark":
                        self.cmd.run(
                            ["bookmark", "--force", "--", resolved.ref_name],
                            check_returncode=True,
                        )
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    KeyError,
                    exc.LibVCSException,
                ) as error:
                    if result.update_state == "unknown":
                        result.update_state = "failed"
                    result.add_error("update", str(error), error)
                if token is not None and record is not None:
                    try:
                        store.phase(token, record, "inspecting")
                        if self._needs_shelf(record):
                            self._unshelve(
                                token, backup=store.token_path(token) / "backups"
                            )
                        result.conflicts = self._restore_recreated(store, token, record)
                        if record["original"]["pending_branch"]:
                            self.cmd.run(
                                [
                                    "branch",
                                    "--force",
                                    "--",
                                    record["original"]["branch"],
                                ],
                                check_returncode=True,
                            )
                        result.preservation_state = "restored"
                    except (
                        OSError,
                        ValueError,
                        TypeError,
                        KeyError,
                        exc.LibVCSException,
                    ) as error:
                        result.preservation_state = "failed"
                        result.add_error("restore", str(error), error)
                    try:
                        result.conflicts += self._conflicts()
                        if (
                            result.update_state == "completed"
                            and not result.conflicts
                            and result.preservation_state == "restored"
                        ):
                            result.conflicts += self._restore_missing(
                                record["original"], resolved.revision
                            )
                        if result.update_state != "completed" and any(
                            state == "!" and self._work_path(name).exists()
                            for name, state in record["original"]["status"].items()
                        ):
                            result.preservation_state = "failed"
                            result.add_error(
                                "restore",
                                "missing paths need separate recovery",
                            )
                        if result.conflicts:
                            result.preservation_state = "conflicted"
                            result.add_error(
                                "conflicts",
                                "Mercurial restoration has unresolved conflicts",
                            )
                        elif (self.path / ".hg" / "shelvedstate").exists():
                            result.preservation_state = "unknown"
                            result.add_error(
                                "inspection", "Mercurial unshelve remains incomplete"
                            )
                    except (
                        OSError,
                        ValueError,
                        TypeError,
                        KeyError,
                        exc.LibVCSException,
                    ) as error:
                        result.preservation_state = "unknown"
                        result.add_error("inspection", str(error), error)
                    self._finish(store, token, record, result)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            exc.LibVCSException,
        ) as error:
            result.add_error(step, str(error), error)
        return result

    def recover_changes(
        self, token: RecoveryToken, *, destination: StrPath
    ) -> SyncResult:
        """Restore original native state independently using retained local history."""
        result = SyncResult(recovery=token, preservation_state="unknown")
        try:
            store = self._store()
            with store.lock():
                record = self._record(store, token)
                store.validate_source(record)
                material = self._material(store, token, record)
                dest = store.destination(destination)
                original = record["original"]
                self._node(original["revision"])
                recovered = HgSync(url=str(store.source), path=dest)
                recovered.cmd.clone(
                    url=str(store.source),
                    pull=True,
                    no_update=True,
                    rev=original["revision"],
                    check_returncode=True,
                )
                recovered.cmd.run(
                    ["update", "--rev", original["revision"]], check_returncode=True
                )
                if self._needs_shelf(record):
                    assert material is not None
                    shelf_dir = dest / ".hg" / "shelved"
                    shelf_dir.mkdir(mode=0o700, exist_ok=True)
                    for suffix in (".hg", ".patch", ".shelve"):
                        path = preservation.safe_path(
                            material / (self._shelf_name(token) + suffix)
                        )
                        if path.exists():
                            shutil.copy2(path, shelf_dir / path.name)
                    recovered._unshelve(token, backup=dest / ".hg" / "libvcs-backups")
                conflicts = recovered._restore_recreated(store, token, record)
                conflicts += recovered._restore_missing(original, original["revision"])
                if (
                    conflicts
                    or recovered._conflicts()
                    or recovered._status() != original["status"]
                ):
                    msg = (
                        "Mercurial recovery did not restore the original native status"
                    )
                    raise ValueError(msg)  # noqa: TRY301 - return recovery failure with token
                recovered.cmd.run(
                    ["branch", "--force", "--", original["branch"]],
                    check_returncode=True,
                )
                if original["ref_kind"] == "bookmark":
                    recovered.cmd.run(
                        ["bookmark", "--force", "--", original["ref_name"]],
                        check_returncode=True,
                    )
                configuration = configparser.ConfigParser(interpolation=None)
                configuration["paths"] = {"default": original["default"]}
                with (dest / ".hg" / "hgrc").open("w") as stream:
                    configuration.write(stream)
                result.preservation_state = "restored"
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            exc.LibVCSException,
        ) as error:
            result.preservation_state = "failed"
            result.add_error("recovery", str(error), error)
        return result

    def release_changes(self, token: RecoveryToken) -> None:
        """Release verified owned shelf artifacts while preserving unrelated shelves."""
        store = self._store()
        with store.lock():
            record = self._record(store, token)
            store.validate_source(record)
            material = self._material(store, token, record)
            if self._needs_shelf(record):
                assert material is not None
                name = self._shelf_name(token)
                paths = []
                for suffix in (".hg", ".patch", ".shelve"):
                    source = preservation.safe_path(
                        self.path / ".hg" / "shelved" / (name + suffix)
                    )
                    if not source.exists():
                        continue
                    if source.read_bytes() != (material / source.name).read_bytes():
                        msg = "native Mercurial shelf ownership changed"
                        raise ValueError(msg)
                    paths.append(source)
                for path in paths:
                    path.unlink()
            store.remove(token)
