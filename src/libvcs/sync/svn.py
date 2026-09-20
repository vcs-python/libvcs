"""Tool to manage a local SVN (Subversion) working copy from a repository.

.. todo::

    The follow are from saltstack/salt (Apache license):

    - :meth:`~libvcs.sync.svn.SvnSync.get_revision_file`

    The following are pypa/pip (MIT license):

    - :meth:`~libvcs.sync.svn.SvnSync.get_revision`
"""

from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
import re
import sqlite3
import subprocess
import typing as t
import xml.etree.ElementTree as et

from libvcs import exc
from libvcs._internal import preservation, svn_preservation
from libvcs._internal.run import ProgressCallbackProtocol
from libvcs._internal.types import StrPath
from libvcs.cmd.svn import DepthLiteral, Svn

from .base import (
    BaseSync,
    RecoveryToken,
    SyncPolicy,
    SyncResult,
    SyncTarget,
    WorkingCopyPosition,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class SvnOptions:
    """Backend-specific options for Subversion synchronization."""

    username: str | None = None
    password: str | None = dataclasses.field(default=None, repr=False)
    depth: DepthLiteral = None
    trust_server_cert: bool = False
    ignore_externals: bool = False

    def __post_init__(self) -> None:
        """Validate Subversion option types without running Subversion."""
        for name in ("username", "password"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                msg = f"{name} must be a string or None"
                raise TypeError(msg)
            if value is not None and "\0" in value:
                msg = f"{name} must not contain NUL"
                raise ValueError(msg)
        if self.depth not in (None, "empty", "files", "immediates", "infinity"):
            msg = "depth must be empty, files, immediates, infinity, or None"
            raise ValueError(msg)
        for name in ("trust_server_cert", "ignore_externals"):
            if not isinstance(getattr(self, name), bool):
                msg = f"{name} must be a boolean"
                raise TypeError(msg)


class SvnUrlRevFormattingError(ValueError):
    """Raised when SVN Revision output is not in the expected format."""

    def __init__(self, data: str, *args: object) -> None:
        super().__init__(f"Badly formatted data: {data!r}")


class SvnSync(BaseSync):
    """Tool to manage a local SVN (Subversion) working copy from a SVN repository."""

    bin_name = "svn"
    schemes = ("svn", "svn+ssh", "svn+http", "svn+https", "svn+svn")
    cmd: Svn
    options_type = SvnOptions

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        options: SvnOptions | None = None,
        progress_callback: ProgressCallbackProtocol | None = None,
        rev: str | None = None,
    ) -> None:
        """Working copy of a SVN repository.

        Parameters
        ----------
        url : str
            URL in subversion repository

        options : SvnOptions, optional
            Subversion-specific checkout and transport configuration.
        """
        if options is None:
            options = SvnOptions()
        elif not isinstance(options, SvnOptions):
            msg = "options must be an SvnOptions instance"
            raise TypeError(msg)
        self.options = options
        super().__init__(
            url=url,
            path=path,
            progress_callback=progress_callback,
            rev=rev,
        )

        self.cmd = Svn(path=path, progress_callback=self.progress_callback)

    def _user_pw_args(self) -> list[t.Any]:
        args = []
        for param_name in ["svn_username", "svn_password"]:
            if hasattr(self, param_name):
                args.extend(["--" + param_name[4:], getattr(self, param_name)])
        return args

    def obtain(self, quiet: bool | None = None, *args: t.Any, **kwargs: t.Any) -> None:
        """Check out a working copy from a SVN repository."""
        url, rev = self.url, kwargs.pop("revision", self.rev)

        self.cmd.checkout(
            url=url,
            revision=rev,
            username=self.options.username,
            password=self.options.password,
            depth=self.options.depth,
            trust_server_cert=self.options.trust_server_cert,
            ignore_externals=self.options.ignore_externals,
            non_interactive=True,
            quiet=True,
            check_returncode=True,
            **kwargs,
        )

    def get_position(self) -> WorkingCopyPosition:
        """Read base revisions and switched subtrees without contacting the server."""
        wc = svn_preservation.WorkingCopy(self.path)
        info = wc.xml(["info", "--xml", "--", "."])
        root = info.find("entry")
        if root is None or root.findtext("url") is None:
            message = "missing working-copy entry"
            raise SvnUrlRevFormattingError(message)
        status = wc.xml(
            ["status", "--verbose", "--xml", "--ignore-externals", "--", "."]
        )
        revisions = {
            item.attrib["revision"]
            for item in status.iter("wc-status")
            if item.attrib.get("revision", "").isdecimal()
        }
        return WorkingCopyPosition(
            revision=root.attrib["revision"],
            ref_name=t.cast("str", root.findtext("url")),
            ref_kind="url",
            follows=self.rev in (None, "HEAD"),
            mixed=len(revisions) > 1,
            switched=any(
                item.get("switched") == "true" for item in status.iter("wc-status")
            ),
        )

    def _selection(self, target: SyncTarget | None) -> str:
        if target is None:
            target = SyncTarget(rev=self.rev or "HEAD")
        if target.rev is None or target.remote is not None:
            msg = "SVN targets require rev; other selectors and remote are unsupported"
            raise ValueError(msg)
        revision = str(target.rev)
        if revision != "HEAD" and not revision.isdecimal():
            msg = "SVN target revision must be a nonnegative number or HEAD"
            raise ValueError(msg)
        return revision

    def resolve_target(self, target: SyncTarget | None = None) -> WorkingCopyPosition:
        """Read explicit revision and URL facts without querying remote HEAD."""
        revision = self._selection(target)
        if revision == "HEAD":
            msg = "SVN remote HEAD is unavailable from local working-copy metadata"
            raise ValueError(msg)
        return WorkingCopyPosition(
            str(int(revision)), self.url.rstrip("/"), "url", follows=False
        )

    def is_dirty(self) -> bool:
        """Include schedules, property edits, missing paths, and unknown files."""
        return svn_preservation.dirty(svn_preservation.WorkingCopy(self.path).native())

    def _store(self) -> preservation.RecoveryStore:
        return preservation.RecoveryStore(
            self.path, "svn", self.path / ".svn", lock_in_store=True
        )

    def _remote_target(
        self, wc: svn_preservation.WorkingCopy, revision: str
    ) -> WorkingCopyPosition:
        args = ["info", "--xml", "--revision", revision]
        for name in ("username", "password"):
            value = getattr(self.options, name)
            if value is not None:
                args.extend(["--" + name, value])
        if self.options.trust_server_cert:
            args.append("--trust-server-cert")
        remote = wc.xml([*args, "--", self.url])
        local = wc.xml(["info", "--xml", "--", "."])
        if remote.findtext("entry/repository/uuid") != local.findtext(
            "entry/repository/uuid"
        ):
            msg = "SVN target belongs to a different repository"
            raise ValueError(msg)
        entry = remote.find("entry")
        if entry is None or entry.get("kind") != "dir" or entry.findtext("url") is None:
            msg = "SVN target is not an available directory"
            raise ValueError(msg)
        return WorkingCopyPosition(
            entry.attrib["revision"],
            t.cast("str", entry.findtext("url")),
            "url",
            follows=revision == "HEAD",
        )

    def get_revision_file(self, location: str) -> int:
        """Return revision for a file."""
        current_rev = self.cmd.info(location)

        INI_RE = re.compile(r"^([^:]+):\s+(\S.*)$", re.MULTILINE)

        info_list = INI_RE.findall(current_rev)
        return int(dict(info_list)["Revision"])

    def get_revision(self, location: str | None = None) -> int:
        """Return maximum revision for all files under a given location."""
        if not location:
            location = self.url

        if pathlib.Path(location).exists() and not pathlib.Path(location).is_dir():
            return self.get_revision_file(location)

        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, _files in os.walk(location):
            if ".svn" not in dirs:
                dirs[:] = []
                continue  # no sense walking uncontrolled subdirs
            dirs.remove(".svn")
            entries_fn = pathlib.Path(base) / ".svn" / "entries"
            if not entries_fn.exists():
                # FIXME: should we warn?
                continue

            dirurl, localrev = SvnSync._get_svn_url_rev(base)

            if base == location:
                assert dirurl is not None
                base = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return revision

    def update_repo(
        self,
        dest: str | None = None,
        *args: t.Any,
        target: SyncTarget | None = None,
        policy: SyncPolicy | None = None,
        **kwargs: t.Any,
    ) -> SyncResult:
        """Update or switch natively, retaining a full copy under explicit preservation.

        POSIX format-31 working copies are supported. Callers must exclude editors
        and other VCS writers. Sealed copies include administrative/pristine storage.
        """
        result = SyncResult()
        policy = policy or SyncPolicy()
        step = "target"
        try:
            revision = self._selection(target)
            if not (self.path / ".svn").exists():
                step = "precondition"
                if any(
                    (parent / ".svn").exists()
                    for parent in self.path.absolute().parents
                ):
                    msg = "SVN synchronization requires the true working-copy root"
                    raise ValueError(msg)  # noqa: TRY301 - return precondition failure
                step = "obtain"
                self.obtain(revision=revision)
            wc = svn_preservation.WorkingCopy(self.path, timeout=kwargs.get("timeout"))
            store = self._store()
            step = "precondition"
            with store.lock():
                for retained in store.discover():
                    assert retained.recovery is not None
                    if any(
                        error.step == "recovery-record" for error in retained.errors
                    ):
                        return retained
                    retained_record = store.read(retained.recovery)
                    if retained_record["phase"] not in preservation.TERMINAL:
                        return retained
                    try:
                        svn_preservation.validate_record(retained_record)
                    except (ValueError, TypeError, KeyError, et.ParseError) as error:
                        retained.add_error("recovery-record", str(error), error)
                        return retained
                native = wc.precondition()
                original = self.get_position()
                step = "target"
                if policy.drift != "follow":
                    resolved = self.resolve_target(target)
                    if policy.drift == "warn" and (
                        resolved.revision != original.revision
                        or resolved.ref_name != original.ref_name
                    ):
                        logger.warning(
                            "configured SVN target drifted",
                            extra={
                                "vcs_event": "target_drift",
                                "vcs_type": "svn",
                                "vcs_repo_path": str(self.path),
                            },
                        )
                    return result
                dirty = svn_preservation.dirty(native)
                if dirty and policy.dirty == "abort":
                    result.add_error("dirty", "SVN working copy has local changes")
                    return result
                resolved = self._remote_target(wc, revision)
                token: RecoveryToken | None = None
                record = None
                if dirty and policy.dirty == "preserve":
                    step = "capture"
                    token, record = store.create(
                        original=dataclasses.asdict(original),
                        target=dataclasses.asdict(resolved),
                    )
                    result.recovery = token
                    result.preservation_state = "unknown"
                    store.validate_source(record)
                    svn_preservation.capture(wc, store, token, record)
                    store.validate_source(record)
                    result.preservation_state = "saved"
                step = "update"
                if token is not None and record is not None:
                    store.phase(token, record, "updating")
                try:
                    if dirty and policy.dirty == "discard":
                        self._discard(wc, native, **kwargs)
                    command = (
                        "update" if original.ref_name == resolved.ref_name else "switch"
                    )
                    flags = [
                        command,
                        "--accept",
                        "postpone",
                        "--ignore-externals",
                        "--revision",
                        resolved.revision,
                        "--",
                    ]
                    if command == "switch":
                        flags.append(resolved.ref_name)
                    flags.append(".")
                    result.update_state = "unknown"
                    self.cmd.run(
                        flags,
                        username=self.options.username,
                        password=self.options.password,
                        trust_server_cert=self.options.trust_server_cert,
                        non_interactive=True,
                        check_returncode=True,
                        **kwargs,
                    )
                    result.update_state = "completed"
                except (OSError, ValueError, exc.LibVCSException) as error:
                    if result.update_state == "unknown":
                        result.update_state = "failed"
                    result.add_error("update", str(error), error)
                try:
                    if token is not None and record is not None:
                        store.phase(token, record, "inspecting")
                    current = wc.native()
                    result.conflicts = svn_preservation.conflicts(current)
                    if (
                        token is not None
                        and record is not None
                        and result.update_state == "completed"
                    ):
                        result.conflicts += svn_preservation.restore_missing(
                            wc, record["native"]["metadata"]
                        )
                        result.preservation_state = "restored"
                    if result.conflicts:
                        result.preservation_state = "conflicted"
                        result.add_error(
                            "conflicts", "SVN update has unresolved conflicts"
                        )
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    KeyError,
                    et.ParseError,
                    subprocess.SubprocessError,
                    exc.LibVCSException,
                ) as error:
                    result.preservation_state = "unknown"
                    result.add_error("inspection", str(error), error)
                if token is not None and record is not None:
                    try:
                        store.finish(token, record, result)
                    except (OSError, ValueError, TypeError) as error:
                        result.add_error("publication", str(error), error)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            sqlite3.Error,
            et.ParseError,
            subprocess.SubprocessError,
            exc.LibVCSException,
        ) as error:
            result.add_error(step, str(error), error)
        return result

    def _discard(
        self,
        wc: svn_preservation.WorkingCopy,
        native: preservation.Record,
        **kwargs: t.Any,
    ) -> None:
        remove = {
            name
            for name, item in svn_preservation.statuses(native).items()
            if item.get("item") in {"added", "unversioned"}
        }
        physical = svn_preservation.tree(wc.path)
        for name in remove:
            if set(svn_preservation.scope(physical, name)) - remove:
                msg = "SVN discard cannot remove unclassified or ignored descendants"
                raise ValueError(msg)
        self.cmd.run(
            ["revert", "--depth", "infinity", "--", "."],
            check_returncode=True,
            **kwargs,
        )
        for name in sorted(
            remove,
            key=lambda value: len(pathlib.PurePosixPath(value).parts),
            reverse=True,
        ):
            path = wc.path_for(name)
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()

    def list_recoveries(self) -> tuple[SyncResult, ...]:
        """List retained copies and report incomplete material with tokens."""
        store = self._store()
        wc = svn_preservation.WorkingCopy(self.path)
        with store.lock():
            results = store.discover(require_repository=False)
            for result in results:
                assert result.recovery is not None
                if any(error.step == "recovery-record" for error in result.errors):
                    continue
                try:
                    svn_preservation.material(
                        wc,
                        store,
                        result.recovery,
                        store.read(result.recovery, require_repository=False),
                    )
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    KeyError,
                    et.ParseError,
                    exc.LibVCSException,
                ) as error:
                    result.add_error("recovery-material", str(error), error)
            return results

    def recover_changes(
        self, token: RecoveryToken, *, destination: StrPath
    ) -> SyncResult:
        """Recover offline after the original checkout is deleted or replaced."""
        result = SyncResult(recovery=token, preservation_state="unknown")
        try:
            store = self._store()
            with store.lock():
                record = store.read(token, require_repository=False)
                svn_preservation.recover(
                    svn_preservation.WorkingCopy(self.path),
                    store,
                    token,
                    record,
                    store.destination(destination),
                )
                result.preservation_state = "restored"
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            et.ParseError,
            exc.LibVCSException,
        ) as error:
            result.preservation_state = "failed"
            result.add_error("recovery", str(error), error)
        return result

    def release_changes(self, token: RecoveryToken) -> None:
        """Release only a verified owned full working-copy copy."""
        store = self._store()
        with store.lock():
            record = store.read(token, require_repository=False)
            svn_preservation.material(
                svn_preservation.WorkingCopy(self.path), store, token, record
            )
            store.remove(token, require_repository=False)

    @classmethod
    def _get_svn_url_rev(cls, location: str) -> tuple[str | None, int]:
        svn_xml_url_re = re.compile(r'url="([^"]+)"')
        svn_rev_re = re.compile(r'committed-rev="(\d+)"')
        svn_info_xml_rev_re = re.compile(r'\s*revision="(\d+)"')
        svn_info_xml_url_re = re.compile(r"<url>(.*)</url>")

        entries_path = pathlib.Path(location) / ".svn" / "entries"
        if entries_path.exists():
            with entries_path.open() as f:
                data = f.read()
        else:  # subversion >= 1.7 does not have the 'entries' file
            data = ""

        url = None
        if data.startswith(("8", "9", "10")):
            entries = list(map(str.splitlines, data.split("\n\x0c\n")))
            del entries[0][0]  # get rid of the '8'
            url = entries[0][3]
            revs = [int(d[9]) for d in entries if len(d) > 9 and d[9]] + [0]
        elif data.startswith("<?xml"):
            match = svn_xml_url_re.search(data)
            if not match:
                raise SvnUrlRevFormattingError(data=data)
            url = match.group(1)  # get repository URL
            revs = [int(m.group(1)) for m in svn_rev_re.finditer(data)] + [0]
        else:
            try:
                # Note that using get_remote_call_options is not necessary here
                # because `svn info` is being run against a local directory.
                # We don't need to worry about making sure interactive mode
                # is being used to prompt for passwords, because passwords
                # are only potentially needed for remote server requests.
                xml = Svn(path=pathlib.Path(location).parent).info(
                    target=pathlib.Path(location),
                    xml=True,
                )
                match = svn_info_xml_url_re.search(xml)
                assert match is not None
                url = match.group(1)
                revs = [int(m.group(1)) for m in svn_info_xml_rev_re.finditer(xml)]
            except Exception:
                url, revs = None, []

        rev = max(revs) if revs else 0

        return url, rev
