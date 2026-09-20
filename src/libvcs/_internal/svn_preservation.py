"""SVN working-copy inspection, sealed copies, and guarded absence restoration."""

from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import xml.etree.ElementTree as et
from collections.abc import Iterator

from libvcs import exc
from libvcs._internal import preservation
from libvcs._internal.subprocess import SubprocessCommand
from libvcs.sync.base import RecoveryToken, SyncConflict

Record = preservation.Record


class WorkingCopy:
    """Inspect native SVN bytes and bound full-copy recovery to format 31 on POSIX."""

    def __init__(self, path: pathlib.Path, *, timeout: float | None = None) -> None:
        self.path = preservation.safe_path(path)
        self.timeout = timeout

    def read(self, args: list[str]) -> bytes:
        """Keep XML stdout and diagnostic stderr separate without lossy decoding."""
        command = SubprocessCommand(["svn", "--non-interactive", *args], cwd=self.path)
        output = command.run(capture_output=True, check=False, timeout=self.timeout)
        if output.returncode:
            raise exc.CommandError(
                cmd=args,
                returncode=output.returncode,
                output=os.fsdecode(output.stderr),
            )
        return output.stdout

    def xml(self, args: list[str]) -> et.Element:
        return et.fromstring(self.read(args))

    def native(self) -> dict[str, str]:
        """Read local status, history metadata, and binary-safe property XML."""
        result = {}
        for name, args in {
            "status": [
                "status",
                "--xml",
                "--verbose",
                "--no-ignore",
                "--ignore-externals",
            ],
            "info": ["info", "--xml", "--depth", "infinity"],
            "properties": ["proplist", "--xml", "--verbose", "--recursive"],
        }.items():
            document = self.xml([*args, "--", "."])
            _validate_xml(name, document)
            for entry in document.iter():
                if entry.tag == "wcroot-abspath":
                    entry.text = "__WC__"
                path = entry.get("path")
                if path and pathlib.Path(path).is_absolute():
                    entry.set(
                        "path", pathlib.Path(path).relative_to(self.path).as_posix()
                    )
            result[name] = et.canonicalize(et.tostring(document, encoding="unicode"))
        return result

    def path_for(self, name: str) -> pathlib.Path:
        path = pathlib.PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name in ("", "."):
            msg = "unsafe SVN working-copy path"
            raise ValueError(msg)
        name.encode("utf-8", errors="strict")
        result = self.path / path
        preservation.safe_path(result.parent)
        return result

    def check_administration(self) -> None:
        """Reject links that would leave native recovery dependent on outside files."""
        administration = preservation.safe_path(self.path / ".svn")
        for directory, dirs, files in os.walk(administration, followlinks=False):
            if any(
                (pathlib.Path(directory) / name).is_symlink()
                for name in [*dirs, *files]
            ):
                msg = "linked SVN administrative storage is unsupported"
                raise ValueError(msg)

    @contextlib.contextmanager
    def reservation(self) -> Iterator[None]:
        """Reserve a validated format-31 database without waiting for native writers."""
        if os.name != "posix":
            msg = "SVN preservation requires POSIX"
            raise ValueError(msg)
        self.check_administration()
        database_path = preservation.safe_path(self.path / ".svn" / "wc.db")
        if not database_path.is_file():
            msg = "unsupported SVN working-copy database"
            raise ValueError(msg)
        with contextlib.closing(
            sqlite3.connect(database_path.as_uri() + "?mode=rw", uri=True, timeout=0)
        ) as database:
            if database.execute("PRAGMA user_version").fetchone() != (31,):
                msg = "unsupported SVN working-copy schema (requires format 31)"
                raise ValueError(msg)
            required = {
                "WC_LOCK": {"wc_id", "local_dir_relpath", "locked_levels"},
                "WORK_QUEUE": {"id", "work"},
                "NODES": {"wc_id", "local_relpath", "op_depth", "presence", "kind"},
            }
            for table, columns in required.items():
                actual = {
                    row[1] for row in database.execute(f"PRAGMA table_info({table})")
                }
                if not columns <= actual:
                    msg = "unsupported SVN working-copy table schema"
                    raise ValueError(msg)
            if database.execute("PRAGMA journal_mode").fetchone() != ("delete",):
                msg = "unsupported SVN working-copy journal mode"
                raise ValueError(msg)
            database.execute("BEGIN IMMEDIATE")
            try:
                if (
                    database.execute("SELECT 1 FROM WC_LOCK LIMIT 1").fetchone()
                    or database.execute("SELECT 1 FROM WORK_QUEUE LIMIT 1").fetchone()
                ):
                    msg = "native SVN working-copy operation is busy"
                    raise ValueError(msg)
                yield
            finally:
                database.rollback()

    def precondition(self) -> dict[str, str]:
        info = self.xml(["info", "--xml", "--", "."])
        if info.findtext("entry/wc-info/wcroot-abspath") != str(self.path):
            msg = "SVN synchronization requires the true working-copy root"
            raise ValueError(msg)
        with self.reservation():
            native = self.native()
            for item in et.fromstring(native["properties"]).iter("property"):
                if item.get("name") == "svn:externals" and (item.text or "").strip():
                    msg = "SVN externals are outside the preservation scope"
                    raise ValueError(msg)
            for item in et.fromstring(native["status"]).iter("wc-status"):
                if (
                    item.get("item") == "external"
                    or item.get("file-external") == "true"
                ):
                    msg = "SVN file externals are outside the preservation scope"
                    raise ValueError(msg)
                if item.get("wc-locked") == "true":
                    msg = "native SVN working-copy operation is busy"
                    raise ValueError(msg)
            for directory, dirs, files in os.walk(self.path, followlinks=False):
                if pathlib.Path(directory) != self.path and any(
                    name in dirs or name in files for name in (".svn", ".git", ".hg")
                ):
                    msg = "nested repository prevents SVN synchronization"
                    raise ValueError(msg)
                dirs[:] = [name for name in dirs if name not in (".svn", ".git", ".hg")]
            tree(self.path)
            if conflicts(native):
                msg = "SVN working copy already has unresolved conflicts"
                raise ValueError(msg)
            return native


def _validate_xml(name: str, document: et.Element) -> None:
    if (
        document.tag != name
        or (name == "info" and document.find("entry") is None)
        or (name == "status" and document.find("target/entry/wc-status") is None)
    ):
        msg = "unsupported or incomplete SVN inspection XML"
        raise ValueError(msg)


def validate_record(record: Record) -> None:
    """Validate persisted native payload shape before any recovery operation."""
    native = record["native"]
    if (
        not isinstance(native.get("tree"), dict)
        or not isinstance(native.get("metadata"), dict)
        or set(native["metadata"]) != {"status", "info", "properties"}
        or any(not isinstance(value, str) for value in native["metadata"].values())
    ):
        msg = "invalid or incomplete SVN recovery material record"
        raise ValueError(msg)
    for name, value in native["metadata"].items():
        _validate_xml(name, et.fromstring(value))


def tree(root: pathlib.Path) -> dict[str, Record]:
    """Include root permissions and every physical entry, including administration."""
    result = preservation.inventory(root)
    result["."] = {"kind": "directory", "mode": stat.S_IMODE(root.stat().st_mode)}
    return result


def flush_tree(root: pathlib.Path) -> None:
    for directory, _, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = pathlib.Path(directory) / name
            if not path.is_symlink():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        preservation.flush_directory(pathlib.Path(directory))


def statuses(native: Record) -> dict[str, Record]:
    return {
        entry.attrib["path"]: dict(status.attrib)
        for entry in et.fromstring(native["status"]).iter("entry")
        if (status := entry.find("wc-status")) is not None
    }


def dirty(native: Record) -> bool:
    return any(
        item.get("item") not in {"normal", "none", "ignored", "external"}
        or item.get("props") not in {"normal", "none"}
        or item.get("tree-conflicted") == "true"
        for item in statuses(native).values()
    )


def conflicts(native: Record) -> tuple[SyncConflict, ...]:
    result = []
    for name, item in statuses(native).items():
        for key, value, reason in (
            ("item", "conflicted", "text"),
            ("props", "conflicted", "property"),
            ("tree-conflicted", "true", "tree"),
        ):
            if item.get(key) == value:
                result.append(SyncConflict(name, reason))
    return tuple(result)


def nodes(native: Record) -> dict[str, Record]:
    return {
        entry.attrib["path"]: {
            "kind": entry.get("kind"),
            "url": entry.findtext("url"),
            "last_changed": commit.get("revision")
            if (commit := entry.find("commit")) is not None
            else None,
            "schedule": entry.findtext("wc-info/schedule"),
        }
        for entry in et.fromstring(native["info"]).findall("entry")
    }


def scope(entries: Record, name: str) -> Record:
    return {
        key: value
        for key, value in entries.items()
        if key == name or key.startswith(name + "/")
    }


def property_scopes(native: Record) -> dict[str, str]:
    return {
        entry.attrib["path"]: et.canonicalize(et.tostring(entry, encoding="unicode"))
        for entry in et.fromstring(native["properties"]).findall("target")
    }


def restore_missing(wc: WorkingCopy, original: Record) -> tuple[SyncConflict, ...]:
    """Delete only verified unchanged owned paths during the live operation."""
    missing = [
        name
        for name, item in statuses(original).items()
        if item.get("item") == "missing"
    ]
    roots = [
        name
        for name in missing
        if not any(
            name.startswith(parent + "/") for parent in missing if name != parent
        )
    ]
    result = []
    for name in sorted(roots):
        try:
            _restore_one(wc, original, name)
        except ValueError:  # noqa: PERF203 - each missing scope has its own conflict
            result.append(SyncConflict(name, "missing-intent-upstream-changed"))
    return tuple(result)


def _restore_one(wc: WorkingCopy, original: Record, name: str) -> None:
    path = wc.path_for(name)
    current = wc.native()
    before, after = scope(nodes(original), name), scope(nodes(current), name)
    if (
        not before
        or before != after
        or any(
            not all(item.values()) or item["schedule"] != "normal"
            for item in before.values()
        )
    ):
        msg = "missing scope changed native identity"
        raise ValueError(msg)
    if scope(property_scopes(original), name) != scope(property_scopes(current), name):
        msg = "missing scope changed properties"
        raise ValueError(msg)
    if any(
        item.get("item") not in {"normal", "missing"}
        or item.get("props") not in {"none", "normal"}
        or item.get("tree-conflicted") == "true"
        for item in scope(statuses(current), name).values()
    ):
        msg = "missing scope contains changes or obstructions"
        raise ValueError(msg)
    physical = scope(tree(wc.path), name)
    if set(physical) - set(after):
        msg = "missing scope contains unexpected physical descendants"
        raise ValueError(msg)
    identities = {}
    for relative, item in physical.items():
        candidate = wc.path_for(relative)
        actual = candidate.lstat()
        identities[relative] = (
            actual.st_dev,
            actual.st_ino,
            actual.st_mode,
            actual.st_size,
            actual.st_mtime_ns,
        )
        if (item["kind"] == "directory" and after[relative]["kind"] != "dir") or (
            item["kind"] != "directory" and after[relative]["kind"] != "file"
        ):
            msg = "missing scope changed physical kind"
            raise ValueError(msg)
    for relative in sorted(
        physical,
        key=lambda value: len(pathlib.PurePosixPath(value).parts),
        reverse=True,
    ):
        candidate = wc.path_for(relative)
        actual = candidate.lstat()
        expected: tuple[int, ...] = identities[relative]
        observed: tuple[int, ...] = (
            actual.st_dev,
            actual.st_ino,
            actual.st_mode,
            actual.st_size,
            actual.st_mtime_ns,
        )
        if physical[relative]["kind"] == "directory":
            # Removing verified children changes the parent's mtime and size.
            observed, expected = observed[:3], expected[:3]
        if observed != expected:
            msg = "missing scope changed before deletion"
            raise ValueError(msg)
        if physical[relative]["kind"] == "directory":
            candidate.rmdir()
        else:
            candidate.unlink()
    if not physical and (path.exists() or path.is_symlink()):
        msg = "missing scope physical inventory is ambiguous"
        raise ValueError(msg)
    preservation.flush_directory(path.parent)


def capture(
    wc: WorkingCopy,
    store: preservation.RecoveryStore,
    token: RecoveryToken,
    record: Record,
) -> None:
    """Publish an independently verified full copy before native update starts."""
    directory = store.token_path(token)
    staging = pathlib.Path(tempfile.mkdtemp(prefix=".material-", dir=directory))
    with wc.reservation():
        native = wc.native()
        original = tree(wc.path)
        shutil.copytree(wc.path, staging / "wc", symlinks=True)
        copied = WorkingCopy(staging / "wc", timeout=wc.timeout)
        if (
            tree(wc.path) != original
            or tree(copied.path) != original
            or copied.native() != native
            or wc.native() != native
        ):
            msg = "SVN working copy changed during capture"
            raise ValueError(msg)
        # Diff may require repository history for copies from outside this checkout.
        try:
            patch = wc.read(["diff", "--", "."])
            (staging / "changes.diff").write_bytes(patch)
        except (exc.CommandError, subprocess.SubprocessError) as error:
            record["diff_error"] = str(error)
        record["native"] = {"tree": original, "metadata": native}
        store.write(token, record)
        flush_tree(staging)
        if tree(wc.path) != original or tree(copied.path) != original:
            msg = "SVN working copy changed before publication"
            raise ValueError(msg)
        staging.replace(directory / "material")
        preservation.flush_directory(directory)
        store.phase(token, record, "sealed")


def material(
    wc: WorkingCopy,
    store: preservation.RecoveryStore,
    token: RecoveryToken,
    record: Record,
) -> pathlib.Path:
    validate_record(record)
    native = record["native"]
    root = preservation.safe_path(store.token_path(token) / "material" / "wc")
    if tree(root) != native["tree"]:
        msg = "sealed SVN working-copy checksum mismatch"
        raise ValueError(msg)
    retained = WorkingCopy(root, timeout=wc.timeout)
    retained.check_administration()
    if retained.native() != native["metadata"] or tree(root) != native["tree"]:
        msg = "sealed SVN native metadata mismatch"
        raise ValueError(msg)
    return root


def recover(
    wc: WorkingCopy,
    store: preservation.RecoveryStore,
    token: RecoveryToken,
    record: Record,
    destination: pathlib.Path,
) -> None:
    source = material(wc, store, token, record)
    staging = pathlib.Path(
        tempfile.mkdtemp(prefix=f".libvcs-recover-{token.id}-", dir=destination.parent)
    )
    try:
        shutil.copytree(source, staging / "wc", symlinks=True)
        copied = WorkingCopy(staging / "wc", timeout=wc.timeout)
        if (
            tree(copied.path) != record["native"]["tree"]
            or copied.native() != record["native"]["metadata"]
            or tree(copied.path) != record["native"]["tree"]
        ):
            msg = "recovered SVN working copy does not match sealed state"
            raise ValueError(msg)  # noqa: TRY301 - retain staging on verification failure
        flush_tree(staging)
        store.destination(destination)
        (staging / "wc").rename(destination)
        preservation.flush_directory(destination.parent)
        staging.rmdir()
    except Exception as error:
        msg = f"SVN recovery staging retained at {staging}: {error}"
        raise RuntimeError(msg) from error
