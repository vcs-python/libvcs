"""Private recovery records and nonblocking ownership for native VCS adapters."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import tempfile
import typing as t
import uuid
from collections.abc import Iterator

from libvcs.sync.base import RecoveryToken, SyncConflict, SyncResult

Record = dict[str, t.Any]
TERMINAL = frozenset({"completed", "conflicted", "failed"})
PHASES = TERMINAL | {"capturing", "sealed", "updating", "inspecting"}


def safe_path(path: pathlib.Path) -> pathlib.Path:
    """Reject symlink ancestors rather than silently changing the ownership scope."""
    path = pathlib.Path(os.path.abspath(path))  # noqa: PTH100 - reject before resolving symlinks
    for part in (path, *path.parents):
        if part.is_symlink():
            msg = f"unsafe symlink in recovery path: {part}"
            raise ValueError(msg)
    return path


def identity(path: pathlib.Path) -> list[int]:
    """Bind records to a filesystem object independently of its pathname."""
    info = path.stat()
    return [info.st_dev, info.st_ino]


def flush_directory(path: pathlib.Path) -> None:
    """Flush a directory after publishing an owned record or material."""
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_record(path: pathlib.Path, record: Record) -> None:
    """Publish complete JSON with file and directory flush ordering."""
    safe_path(path)
    fd, temporary = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    staging = pathlib.Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        staging.replace(path)
        flush_directory(path.parent)
    finally:
        staging.unlink(missing_ok=True)


def inventory(root: pathlib.Path) -> dict[str, Record]:
    """Inventory files, symlinks, modes, and directories without following links."""
    safe_path(root)
    result: dict[str, Record] = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted([*dirs, *files]):
            path = pathlib.Path(directory) / name
            relative = path.relative_to(root).as_posix()
            relative.encode("utf-8", errors="strict")
            info = path.lstat()
            item: Record = {"mode": stat.S_IMODE(info.st_mode)}
            if stat.S_ISLNK(info.st_mode):
                item.update(kind="symlink", target=str(path.readlink()))
            elif stat.S_ISDIR(info.st_mode):
                item.update(kind="directory")
            elif stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                item.update(kind="file", sha256=digest.hexdigest(), size=info.st_size)
            else:
                msg = f"unsupported recovery file type: {relative}"
                raise ValueError(msg)
            result[relative] = item
    return result


class RecoveryStore:
    """Keep retained operations beside a checkout, with shared native ownership."""

    def __init__(
        self, source: pathlib.Path, backend: str, repository: pathlib.Path
    ) -> None:
        self.source = safe_path(source)
        self.backend = backend
        self.repository = safe_path(repository)
        key = hashlib.sha256(os.fsencode(self.source)).hexdigest()[:24]
        self.root = safe_path(self.source.parent / ".libvcs-recovery" / key)
        if self.root.is_relative_to(self.source):
            msg = "recovery store overlaps source"
            raise ValueError(msg)
        self.lock_path = self.repository / ".libvcs-preserve.lock"

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        """Own the native namespace without waiting for another transaction."""
        if os.name != "posix":
            msg = "recovery requires POSIX ownership locks"
            raise NotImplementedError(msg)
        import fcntl

        safe_path(self.lock_path)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                msg = "repository recovery ownership is busy"
                raise RuntimeError(msg) from error
            yield
        finally:
            os.close(fd)

    def create(
        self, *, original: Record, target: Record
    ) -> tuple[RecoveryToken, Record]:
        """Publish unique capture intent before the backend saves or cleans anything."""
        for directory in (self.root.parent, self.root):
            safe_path(directory)
            directory.mkdir(mode=0o700, exist_ok=True)
            if directory.stat().st_mode & 0o077:
                msg = "recovery store must be private (mode 0700)"
                raise ValueError(msg)
        operation_id = uuid.uuid4().hex
        location = self.root / operation_id
        location.mkdir(mode=0o700)
        token = RecoveryToken(operation_id, self.backend, str(location))
        record: Record = {
            "version": 1,
            "id": operation_id,
            "backend": self.backend,
            "source": str(self.source),
            "source_identity": identity(self.source),
            "repository": str(self.repository),
            "repository_identity": identity(self.repository),
            "original": original,
            "target": target,
            "marker": f"libvcs:{operation_id}",
            "phase": "capturing",
            "native": {},
            "result": {},
        }
        self.write(token, record)
        flush_directory(self.root)
        return token, record

    def token_path(self, token: RecoveryToken) -> pathlib.Path:
        """Validate token scope before reading, recovering, or releasing material."""
        if token.backend != self.backend:
            msg = "recovery token backend does not match"
            raise ValueError(msg)
        if re.fullmatch(r"[0-9a-f]{32}", token.id) is None:
            msg = "invalid recovery token id"
            raise ValueError(msg)
        expected = self.root / token.id
        if token.location != str(expected):
            msg = "recovery token location does not match this checkout"
            raise ValueError(msg)
        safe_path(expected)
        return expected

    def read(self, token: RecoveryToken) -> Record:
        """Read a versioned record, rejecting mismatched native and filesystem scope."""
        path = self.token_path(token) / "operation.json"
        safe_path(path)
        value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            msg = "invalid recovery record"
            raise ValueError(msg)  # noqa: TRY004 - persisted schema validation
        record: Record = value
        expected = {
            "version": 1,
            "id": token.id,
            "backend": self.backend,
            "source": str(self.source),
            "repository": str(self.repository),
            "repository_identity": identity(self.repository),
            "marker": f"libvcs:{token.id}",
        }
        if any(record.get(key) != value for key, value in expected.items()):
            msg = "recovery record identity does not match"
            raise ValueError(msg)
        phase = record.get("phase")
        if (
            not isinstance(phase, str)
            or phase not in PHASES
            or any(
                not isinstance(record.get(key), dict)
                for key in ("original", "target", "native", "result")
            )
        ):
            msg = "invalid recovery record phase or payload"
            raise ValueError(msg)
        self._validate_result(record["result"])
        return record

    @staticmethod
    def _validate_result(data: Record) -> None:
        for key, allowed in (
            ("update_state", {"not-started", "completed", "failed", "unknown"}),
            (
                "preservation_state",
                {"not-needed", "saved", "restored", "conflicted", "failed", "unknown"},
            ),
        ):
            value = data.get(key, "unknown")
            if not isinstance(value, str) or value not in allowed:
                msg = "invalid persisted recovery result state"
                raise ValueError(msg)
        for key, fields in (
            ("errors", {"step", "message"}),
            ("conflicts", {"path", "reason"}),
        ):
            values = data.get(key, [])
            if not isinstance(values, list) or any(
                not isinstance(value, dict)
                or set(value) != fields
                or any(not isinstance(value[field], str) for field in fields)
                for value in values
            ):
                msg = "invalid persisted recovery result details"
                raise ValueError(msg)

    def validate_source(self, record: Record) -> None:
        """Refuse ownership inferred from a replaced checkout's old pathname."""
        safe_path(self.source)
        if record.get("source_identity") != identity(self.source):
            msg = "recovery source identity changed"
            raise ValueError(msg)

    def write(self, token: RecoveryToken, record: Record) -> None:
        """Replace only the mutable operation envelope."""
        atomic_record(self.token_path(token) / "operation.json", record)

    def phase(self, token: RecoveryToken, record: Record, phase: str) -> None:
        """Persist a phase before starting its next native mutation."""
        if not isinstance(phase, str) or phase not in PHASES:
            msg = "invalid recovery phase"
            raise ValueError(msg)
        record["phase"] = phase
        self.write(token, record)

    def finish(self, token: RecoveryToken, record: Record, result: SyncResult) -> None:
        """Publish known outcomes without serializing live exception instances."""
        record["result"] = {
            "update_state": result.update_state,
            "preservation_state": result.preservation_state,
            "errors": [
                {"step": error.step, "message": error.message}
                for error in result.errors
            ],
            "conflicts": [dataclasses.asdict(item) for item in result.conflicts],
        }
        phase = (
            "conflicted" if result.conflicts else "completed" if result.ok else "failed"
        )
        self.phase(token, record, phase)

    def snapshot(self, token: RecoveryToken, record: Record) -> SyncResult:
        """Expose interrupted records as uncertain outcomes, never as successes."""
        result = SyncResult(recovery=token)
        data = record["result"]
        self._validate_result(data)
        update = data.get("update_state", "unknown")
        preservation = data.get("preservation_state", "unknown")
        result.update_state = update
        result.preservation_state = preservation
        for error in data.get("errors", []):
            result.add_error(error["step"], error["message"])
        result.conflicts = tuple(
            SyncConflict(**item) for item in data.get("conflicts", [])
        )
        if record["phase"] not in TERMINAL:
            result.add_error(
                "interrupted", f"recovery operation stopped during {record['phase']}"
            )
        elif result.ok and (
            result.conflicts
            or update in {"failed", "unknown"}
            or preservation in {"failed", "unknown", "conflicted"}
        ):
            result.add_error(
                "recovery", "retained operation did not complete successfully"
            )
        return result

    def discover(self) -> tuple[SyncResult, ...]:
        """List damaged and unfinished operation directories as visible errors."""
        if not self.root.exists():
            return ()
        safe_path(self.root)
        results = []
        for path in sorted(self.root.iterdir()):
            token = RecoveryToken(path.name, self.backend, str(path))
            try:
                results.append(self.snapshot(token, self.read(token)))
            except (OSError, ValueError, KeyError, TypeError) as error:
                result = SyncResult(
                    recovery=token, update_state="unknown", preservation_state="unknown"
                )
                result.add_error("recovery-record", str(error), error)
                results.append(result)
        return tuple(results)

    def destination(self, value: str | os.PathLike[str]) -> pathlib.Path:
        """Require a new destination outside source and retained material."""
        destination = safe_path(pathlib.Path(value))
        for scope in (self.source, self.root, self.repository):
            if destination.is_relative_to(scope) or scope.is_relative_to(destination):
                msg = "recovery destination overlaps source or retained material"
                raise ValueError(msg)
        if destination.exists():
            msg = "recovery destination already exists"
            raise ValueError(msg)
        if not destination.parent.is_dir():
            msg = "recovery destination parent must exist"
            raise ValueError(msg)
        return destination

    def remove(self, token: RecoveryToken) -> None:
        """Remove a validated owned envelope after its native material is released."""
        self.read(token)
        shutil.rmtree(self.token_path(token))
        flush_directory(self.root)
