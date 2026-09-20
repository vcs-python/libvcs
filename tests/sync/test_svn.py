"""Tests for libvcs svn repos."""

from __future__ import annotations

import shutil
import typing as t
import xml.etree.ElementTree as et

import pytest

from libvcs import exc
from libvcs.sync.base import SyncPolicy, SyncResult, SyncTarget
from libvcs.sync.svn import SvnOptions, SvnSync

if t.TYPE_CHECKING:
    import pathlib

    from libvcs.pytest_plugin import CreateRepoFn

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


def test_svn_position_reports_local_url_and_revision(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """Position reads the working copy after its remote becomes unavailable."""
    remote = tmp_path / "remote"
    shutil.copytree(svn_remote_repo_with_files, remote)
    repo = SvnSync(url=remote.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    shutil.rmtree(remote)

    position = repo.get_position()

    assert (position.ref_kind, position.ref_name) == ("url", repo.url)
    assert position.revision == "3"
    assert position.follows
    assert not position.mixed
    assert not position.switched


def test_svn_position_reports_mixed_and_switched_subtrees(
    tmp_path: pathlib.Path,
    create_svn_remote_repo: CreateRepoFn,
) -> None:
    """A root revision cannot stand in for mixed or switched child entries."""
    remote = create_svn_remote_repo()
    repo = SvnSync(url=remote.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    (repo.path / "trunk").mkdir()
    (repo.path / "trunk" / "file.txt").write_text("first\n")
    repo.cmd.run(["add", "trunk"])
    assert not repo.get_position().mixed
    repo.cmd.run(["commit", "-m", "add trunk"])

    position = repo.get_position()
    assert position.mixed
    assert position.revision == "0"

    repo.cmd.run(["update"])
    repo.cmd.run(["copy", "trunk", "branch"])
    repo.cmd.run(["commit", "-m", "copy branch"])
    repo.cmd.run(["update"])
    repo.cmd.run(["copy", "-r", "1", f"{repo.url}/trunk", "old-copy"])
    assert not repo.get_position().mixed
    repo.cmd.run(["propset", "svn:externals", "--", "-r1 ^/trunk external-copy", "."])
    repo.cmd.run(["update"])
    assert not repo.get_position().mixed
    repo.cmd.run(["switch", f"{repo.url}/branch", "trunk"])

    position = repo.get_position()
    assert not position.mixed
    assert position.switched
    assert position.ref_name == repo.url


def test_svn_sync(tmp_path: pathlib.Path, svn_remote_repo: pathlib.Path) -> None:
    """Tests for SvnSync."""
    repo_name = "my_svn_project"

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo}",
        path=str(tmp_path / repo_name),
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert (tmp_path / repo_name).exists()


def test_svn_sync_with_files(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """Tests for SvnSync."""
    repo_name = "my_svn_project"

    svn_repo = SvnSync(
        url=f"file://{svn_remote_repo_with_files}",
        path=str(tmp_path / repo_name),
    )

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 3

    assert (tmp_path / repo_name).exists()


def test_svn_options_establish_ambient_checkout_depth(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """An empty-depth checkout creates only the working-copy root."""
    checkout = tmp_path / "empty-checkout"
    repo = SvnSync(
        url=svn_remote_repo_with_files.as_uri(),
        path=checkout,
        options=SvnOptions(depth="empty"),
    )

    repo.obtain()

    assert {entry.name for entry in checkout.iterdir()} == {".svn"}


def test_repo_svn_remote_checkout(
    create_svn_remote_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Tests for SvnSync with remote checkout."""
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SvnSync(path=svn_repo_checkout_dir, url=f"file://{svn_server!s}")

    svn_repo.obtain()
    svn_repo.update_repo()

    assert svn_repo.get_revision() == 0
    assert svn_repo.get_revision_file("./") == 0

    assert svn_repo_checkout_dir.exists()


def test_update_repo_target_failure_returns_sync_result(
    create_svn_remote_repo: CreateRepoFn,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    """Test that a deleted remote in update_repo() returns SyncResult with error."""
    svn_server = create_svn_remote_repo()
    svn_repo_checkout_dir = projects_path / "my_svn_checkout"
    svn_repo = SvnSync(path=svn_repo_checkout_dir, url=f"file://{svn_server!s}")

    svn_repo.obtain()

    # Delete the remote to cause an update failure
    shutil.rmtree(svn_server)

    result = svn_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "target"
    assert isinstance(result.errors[0].exception, exc.CommandError)


def test_svn_dirty_abort_precedes_update(
    tmp_path: pathlib.Path, svn_remote_repo_with_files: pathlib.Path
) -> None:
    """Default dirty policy leaves the checkout and unknown files untouched."""
    repo = SvnSync(url=svn_remote_repo_with_files.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    (repo.path / "unknown").write_bytes(b"local\0bytes")
    result = repo.update_repo()
    assert not result.ok
    assert result.errors[0].step == "dirty"
    assert (repo.path / "unknown").read_bytes() == b"local\0bytes"


def test_svn_retained_copy_recovers_offline_twice(
    tmp_path: pathlib.Path, svn_remote_repo_with_files: pathlib.Path
) -> None:
    """Retained physical copies recover schedules and binary properties offline."""
    remote = tmp_path / "remote"
    shutil.copytree(svn_remote_repo_with_files, remote)
    repo = SvnSync(url=remote.as_uri(), path=tmp_path / "copy")
    repo.obtain()
    (repo.path / "added").write_bytes(b"added\0bytes")
    repo.cmd.run(["add", "added"])
    blob = tmp_path / "blob"
    blob.write_bytes(b"property\0\xff")
    repo.cmd.run(["propset", "test:binary", "--file", str(blob), "added"])
    (repo.path / "unknown").write_bytes(b"unknown\0bytes")
    result = repo.update_repo(
        target=SyncTarget(rev="2"), policy=SyncPolicy(dirty="preserve")
    )
    assert result.ok, result.errors
    assert result.recovery is not None
    before = et.canonicalize(repo.cmd.run(["status", "--xml", "--no-ignore"]))
    shutil.rmtree(remote)
    for index in range(2):
        destination = tmp_path / f"recovered-{index}"
        recovered = repo.recover_changes(result.recovery, destination=destination)
        assert recovered.ok, recovered.errors
        clone = SvnSync(url=repo.url, path=destination)
        assert (
            et.canonicalize(clone.cmd.run(["status", "--xml", "--no-ignore"])) == before
        )
        assert et.canonicalize(
            clone.cmd.run(["proplist", "--xml", "--verbose", "added"])
        ) == et.canonicalize(repo.cmd.run(["proplist", "--xml", "--verbose", "added"]))
        assert (destination / "added").read_bytes() == b"added\0bytes"
        assert (destination / "unknown").read_bytes() == b"unknown\0bytes"
    repo.release_changes(result.recovery)
    assert repo.list_recoveries() == ()


@pytest.fixture
def svn_pair(
    tmp_path: pathlib.Path, create_svn_remote_repo: CreateRepoFn
) -> tuple[SvnSync, SvnSync, pathlib.Path]:
    """Create related native working copies with file and directory history."""
    remote = create_svn_remote_repo()
    source = SvnSync(url=remote.as_uri(), path=tmp_path / "source")
    source.obtain()
    (source.path / "trunk").mkdir()
    source.cmd.run(["add", "trunk"])
    source.cmd.run(["commit", "-m", "layout"])
    source = SvnSync(url=remote.as_uri() + "/trunk", path=tmp_path / "upstream")
    source.obtain()
    (source.path / "file").write_text("first\n" + "middle\n" * 12 + "last\n")
    (source.path / "missing").write_text("missing base\n")
    (source.path / "folder").mkdir()
    (source.path / "folder" / "child").write_text("child base\n")
    source.cmd.run(["add", "file", "missing", "folder"])
    source.cmd.run(["propset", "test:property", "base", "file"])
    source.cmd.run(["commit", "-m", "base"])
    repo = SvnSync(url=source.url, path=tmp_path / "copy")
    repo.obtain()
    return source, repo, remote


@pytest.mark.parametrize(
    "kind", ["disjoint", "switch", "text", "property", "tree", "unknown", "binary"]
)
def test_svn_native_merge_and_conflicts(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path], tmp_path: pathlib.Path, kind: str
) -> None:
    """Native update and switch preserve dirt or expose conflicts with recovery."""
    from libvcs._internal import svn_preservation

    source, repo, _ = svn_pair
    if kind == "switch":
        source.cmd.run(
            [
                "copy",
                source.url,
                source.url.removesuffix("/trunk") + "/branch",
                "-m",
                "branch",
            ]
        )
        source = SvnSync(
            url=source.url.removesuffix("/trunk") + "/branch", path=tmp_path / "branch"
        )
        source.obtain()
        repo.url = source.url
    (repo.path / "file.orig").write_text("caller backup\n")
    if kind == "tree":
        repo.cmd.run(["delete", "file"])
    elif kind == "property":
        repo.cmd.run(["propset", "test:property", "local", "file"])
    elif kind == "unknown":
        (repo.path / "incoming").write_text("local\n")
    elif kind == "binary":
        (repo.path / "file").write_bytes(b"local\0binary")
    else:
        (repo.path / "file").write_text("local\n" + "middle\n" * 12 + "last\n")
    original = svn_preservation.WorkingCopy(repo.path).native()
    if kind == "property":
        source.cmd.run(["propset", "test:property", "upstream", "file"])
    elif kind == "unknown":
        (source.path / "incoming").write_text("upstream\n")
        source.cmd.run(["add", "incoming"])
    elif kind == "binary":
        (source.path / "file").write_bytes(b"upstream\0binary")
    else:
        (source.path / "file").write_text(
            ("upstream\n" if kind == "text" else "first\n")
            + "middle\n" * 12
            + "upstream last\n"
        )
    source.cmd.run(["commit", "-m", "upstream"])
    result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.recovery is not None, result.errors
    if kind in {"disjoint", "switch"}:
        assert result.ok, result.errors
        assert (
            repo.path / "file"
        ).read_text() == "local\n" + "middle\n" * 12 + "upstream last\n"
    else:
        assert not result.ok
        assert result.conflicts
        assert result.preservation_state == "conflicted"
    assert (repo.path / "file.orig").read_text() == "caller backup\n"
    destination = tmp_path / "recovered"
    recovered = repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    assert svn_preservation.WorkingCopy(destination).native() == original


@pytest.mark.parametrize(
    "kind,changed",
    [("missing", False), ("missing", True), ("folder", False), ("folder", True)],
)
def test_svn_missing_intent_guards_upstream(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path], kind: str, changed: bool
) -> None:
    """Unchanged missing scopes stay absent; changed descendants stay present."""
    source, repo, _ = svn_pair
    path = repo.path / kind
    if kind == "folder":
        shutil.rmtree(path)
    else:
        path.unlink()
    affected = source.path / kind / "child" if kind == "folder" else source.path / kind
    if changed:
        affected.write_text("upstream change\n")
    else:
        (source.path / "file").write_text("unrelated upstream\n")
    source.cmd.run(["commit", "-m", "upstream"])
    result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert result.recovery is not None, result.errors
    assert result.ok is not changed, result.errors
    assert path.exists() is changed
    if changed:
        assert result.conflicts[0].reason == "missing-intent-upstream-changed"


@pytest.mark.parametrize("scope", ["ignored", "symlink", "descendant"])
def test_svn_missing_guard_rejects_unowned_scope(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path], scope: str
) -> None:
    """Physical obstructions and descendant-only identity changes block deletion."""
    from libvcs._internal import svn_preservation

    _, repo, _ = svn_pair
    wc = svn_preservation.WorkingCopy(repo.path)
    if scope == "ignored":
        repo.cmd.run(["propset", "svn:ignore", "cache", "folder"])
        repo.cmd.run(["commit", "-m", "ignore cache"])
    shutil.rmtree(repo.path / "folder")
    original = wc.native()
    repo.cmd.run(["update"])
    if scope == "ignored":
        (repo.path / "folder" / "cache").write_text("ignored\n")
    elif scope == "symlink":
        shutil.rmtree(repo.path / "folder")
        (repo.path / "folder").symlink_to(repo.path.parent)
    else:
        document = et.fromstring(original["info"])
        for entry in document.findall("entry"):
            if entry.get("path") == "folder/child":
                commit = entry.find("commit")
                assert commit is not None
                commit.set("revision", "0")
        original["info"] = et.tostring(document, encoding="unicode")
    result = svn_preservation.restore_missing(wc, original)
    assert result
    assert (repo.path / "folder").exists()


@pytest.mark.parametrize(
    "obstruction", ["database", "schema", "external", "nested", "subdirectory"]
)
def test_svn_preconditions_leave_source_unchanged(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    obstruction: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported scope and native activity fail before capture or update."""
    import sqlite3

    _, repo, _ = svn_pair
    database = sqlite3.connect(repo.path / ".svn" / "wc.db", timeout=0)
    try:
        if obstruction == "database":
            database.execute("BEGIN IMMEDIATE")
        elif obstruction == "schema":
            database.execute("PRAGMA user_version=999")
        elif obstruction == "external":
            repo.cmd.run(["propset", "svn:externals", "^/trunk external", "."])
        elif obstruction == "nested":
            (repo.path / "nested" / ".svn").mkdir(parents=True)
        elif obstruction == "subdirectory":
            repo = SvnSync(url=repo.url + "/folder", path=repo.path / "folder")

            def reject_obtain() -> None:
                message = "subdirectory must not run checkout"
                raise AssertionError(message)

            monkeypatch.setattr(repo, "obtain", reject_obtain)
        (repo.path / "unknown").write_text("local\n")
        result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
        assert not result.ok
        assert result.recovery is None
        assert (repo.path / "unknown").read_text() == "local\n"
    finally:
        database.rollback()
        database.close()


def test_svn_offline_copy_history_and_physical_state(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path], tmp_path: pathlib.Path
) -> None:
    """Recovery needs no remote history even for copies from outside the checkout."""
    from libvcs._internal import svn_preservation

    source, repo, remote = svn_pair
    source.cmd.run(
        ["copy", source.url + "/file", remote.as_uri() + "/outside", "-m", "outside"]
    )
    repo.cmd.run(["copy", remote.as_uri() + "/outside", "copied"])
    repo.cmd.run(["move", "missing", "moved"])
    repo.cmd.run(["delete", "file"])
    (repo.path / "file").write_text("replacement\n")
    repo.cmd.run(["add", "file"])
    repo.cmd.run(["changelist", "local", "copied"])
    repo.cmd.run(["propset", "svn:ignore", "cache", "."])
    (repo.path / "cache").write_bytes(b"ignored\0bytes")
    (repo.path / "unknown-dir").mkdir()
    (repo.path / "unknown-dir" / "file").write_bytes(b"unknown\0bytes")
    (repo.path / "link").symlink_to("copied")
    (repo.path / "copied").chmod(0o751)
    original = svn_preservation.WorkingCopy(repo.path).native()
    result = repo.update_repo(
        target=SyncTarget(rev="2"), policy=SyncPolicy(dirty="preserve")
    )
    assert result.recovery is not None, result.errors
    shutil.rmtree(remote)
    for index in range(2):
        destination = tmp_path / f"offline-{index}"
        recovered = repo.recover_changes(result.recovery, destination=destination)
        assert recovered.ok, recovered.errors
        assert svn_preservation.WorkingCopy(destination).native() == original
        assert (destination / "cache").read_bytes() == b"ignored\0bytes"
        assert (destination / "unknown-dir" / "file").read_bytes() == b"unknown\0bytes"
        assert (destination / "link").readlink().as_posix() == "copied"
        assert (destination / "copied").stat().st_mode & 0o777 == 0o751


@pytest.mark.parametrize(
    "fault",
    [
        "capture",
        "sealed",
        "updating",
        "update",
        "inspection",
        "inspection-schema",
        "absence",
        "publication",
    ],
)
def test_svn_failure_paths_retain_tokens(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """Every post-intent failure retains its token and prevents unsafe continuation."""
    from libvcs._internal import preservation, svn_preservation

    source, repo, _ = svn_pair
    (source.path / "file").write_text("upstream\n")
    source.cmd.run(["commit", "-m", "upstream"])
    (repo.path / "unknown").write_text("local\n")
    before = svn_preservation.WorkingCopy(repo.path).native()
    real_run, real_phase = repo.cmd.run, preservation.RecoveryStore.phase
    real_read = svn_preservation.WorkingCopy.read
    updated = False

    def run(args: t.Any, **kwargs: t.Any) -> str:
        nonlocal updated
        if "update" in args:
            updated = True
            if fault == "update":
                raise exc.CommandError(
                    cmd=args, returncode=1, output="original update error"
                )
        return real_run(args, **kwargs)

    def phase(store: t.Any, token: t.Any, record: t.Any, value: str) -> None:
        if value == fault:
            raise OSError(fault)
        real_phase(store, token, record, value)

    def fail(*args: t.Any, **kwargs: t.Any) -> t.Any:
        raise OSError(fault)

    def read(wc: t.Any, args: list[str]) -> bytes:
        if updated and args[0] == "status":
            return b"<unexpected/>"
        return real_read(wc, args)

    with monkeypatch.context() as patch:
        patch.setattr(repo.cmd, "run", run)
        patch.setattr(preservation.RecoveryStore, "phase", phase)
        if fault == "capture":
            patch.setattr(shutil, "copytree", fail)
        if fault == "inspection":
            patch.setattr(
                svn_preservation,
                "conflicts",
                lambda native: () if not updated else fail(),
            )
        if fault == "inspection-schema":
            patch.setattr(svn_preservation.WorkingCopy, "read", read)
        if fault == "absence":
            patch.setattr(svn_preservation, "restore_missing", fail)
        if fault == "publication":
            patch.setattr(preservation.RecoveryStore, "finish", fail)
        result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is not None
    expected_step = (
        "capture"
        if fault in {"capture", "sealed"}
        else "update"
        if fault in {"updating", "update"}
        else "inspection"
        if fault in {"inspection", "inspection-schema", "absence"}
        else "publication"
    )
    assert result.errors[0].step == expected_step
    found = repo.list_recoveries()[0]
    assert found.recovery == result.recovery
    if fault in {"capture", "sealed", "updating"}:
        assert not updated
        assert svn_preservation.WorkingCopy(repo.path).native() == before
    if fault != "capture":
        recovered = repo.recover_changes(
            result.recovery, destination=tmp_path / "recovered"
        )
        assert recovered.ok, recovered.errors
    else:
        assert not found.ok


@pytest.mark.parametrize("fault", ["copy", "verify", "publish"])
def test_svn_recovery_failure_keeps_owned_staging(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """Failed recovery retains staging, source, sealed data, and the same token."""
    import pathlib

    _, repo, _ = svn_pair
    (repo.path / "unknown").write_text("local\n")
    saved = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert saved.ok, saved.errors
    assert saved.recovery is not None
    real_copy = shutil.copytree
    real_rename = pathlib.Path.rename

    def copy(source: t.Any, destination: t.Any, *args: t.Any, **kwargs: t.Any) -> t.Any:
        output = real_copy(source, destination, *args, **kwargs)
        if pathlib.Path(destination).name != "wc":
            return output
        if fault == "copy":
            message = "recovery copy failed"
            raise OSError(message)
        if fault == "verify":
            (pathlib.Path(destination) / "unknown").write_text("wrong\n")
        return output

    def rename(source: pathlib.Path, target: t.Any) -> pathlib.Path:
        if fault == "publish":
            message = "recovery publication failed"
            raise OSError(message)
        return real_rename(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "copytree", copy)
        patch.setattr(pathlib.Path, "rename", rename)
        result = repo.recover_changes(
            saved.recovery, destination=tmp_path / "recovered"
        )
    assert not result.ok
    assert result.recovery == saved.recovery
    assert "staging retained at" in result.errors[0].message
    expected = {
        "copy": "recovery copy failed",
        "verify": "does not match sealed state",
        "publish": "recovery publication failed",
    }
    assert expected[fault] in result.errors[0].message
    assert list(tmp_path.glob(".libvcs-recover-*"))
    assert (repo.path / "unknown").read_text() == "local\n"
    assert repo.recover_changes(saved.recovery, destination=tmp_path / "second").ok


def test_svn_ignored_collision_keeps_local_bytes(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
) -> None:
    """An ignored-only obstruction remains intact when upstream tracks that path."""
    source, repo, _ = svn_pair
    repo.cmd.run(["propset", "svn:ignore", "cache", "."])
    repo.cmd.run(["commit", "-m", "ignore"])
    (repo.path / "cache").write_bytes(b"local ignored\0bytes")
    assert not repo.is_dirty()
    (source.path / "cache").write_bytes(b"upstream tracked\0bytes")
    source.cmd.run(["add", "cache"])
    source.cmd.run(["commit", "-m", "track cache"])
    result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.conflicts or result.errors
    assert (repo.path / "cache").read_bytes() == b"local ignored\0bytes"


def test_svn_explicit_discard_retains_ignored_files(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
) -> None:
    """Discard reverts schedules and ordinary dirt without deleting ignored files."""
    source, repo, _ = svn_pair
    repo.cmd.run(["propset", "svn:ignore", "cache", "."])
    repo.cmd.run(["commit", "-m", "ignore"])
    source.cmd.run(["update"])
    (source.path / "file").write_text("upstream\n")
    source.cmd.run(["commit", "-m", "advance"])
    (repo.path / "file").write_text("local\n")
    repo.cmd.run(["delete", "missing"])
    (repo.path / "added").write_text("added\n")
    repo.cmd.run(["add", "added"])
    (repo.path / "unknown").write_text("unknown\n")
    (repo.path / "cache").write_text("ignored\n")
    result = repo.update_repo(policy=SyncPolicy(dirty="discard"))
    assert result.ok, result.errors
    assert result.recovery is None
    assert not repo.is_dirty()
    assert (repo.path / "file").read_text() == "upstream\n"
    assert (repo.path / "missing").exists()
    assert not (repo.path / "added").exists()
    assert not (repo.path / "unknown").exists()
    assert (repo.path / "cache").read_text() == "ignored\n"


@pytest.mark.parametrize("drift", ["keep", "warn"])
def test_svn_drift_uses_local_revision_and_url(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    caplog: pytest.LogCaptureFixture,
    drift: t.Literal["keep", "warn"],
) -> None:
    """Numeric target comparison stays offline and emits structured drift records."""
    _, repo, remote = svn_pair
    position = repo.get_position()
    (repo.path / "unknown").write_text("local\n")
    shutil.rmtree(remote)
    result = repo.update_repo(target=SyncTarget(rev=1), policy=SyncPolicy(drift=drift))
    assert result.ok, result.errors
    assert repo.get_position() == position
    assert (repo.path / "unknown").read_text() == "local\n"
    warnings = [record for record in caplog.records if record.name == "libvcs.sync.svn"]
    assert bool(warnings) is (drift == "warn")
    if warnings:
        assert warnings[0].__dict__["vcs_event"] == "target_drift"
    caplog.clear()
    result = repo.update_repo(
        target=SyncTarget(rev=position.revision), policy=SyncPolicy(drift="warn")
    )
    assert result.ok
    assert not [record for record in caplog.records if record.name == "libvcs.sync.svn"]
    with pytest.raises(ValueError, match="HEAD"):
        repo.resolve_target(SyncTarget(rev="HEAD"))


@pytest.mark.parametrize(
    "target",
    [
        SyncTarget(branch="main"),
        SyncTarget(tag="v1"),
        SyncTarget(commit="1"),
        SyncTarget(rev="1", remote="origin"),
    ],
)
def test_svn_rejects_nonrevision_targets_before_checkout(
    tmp_path: pathlib.Path, target: SyncTarget
) -> None:
    """SVN never guesses branch layouts or starts a checkout for invalid selectors."""
    repo = SvnSync(url="file:///unavailable", path=tmp_path / "copy")
    result = repo.update_repo(target=target)
    assert not result.ok
    assert result.errors[0].step == "target"
    assert not repo.path.exists()


@pytest.mark.parametrize("damage", ["phase", "native", "material"])
def test_svn_damaged_record_exposes_token(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path], tmp_path: pathlib.Path, damage: str
) -> None:
    """Malformed records and damaged copies remain visible, unreleased errors."""
    import json
    import pathlib

    _, repo, _ = svn_pair
    (repo.path / "unknown").write_text("local\n")
    saved = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert saved.ok, saved.errors
    assert saved.recovery is not None
    operation = pathlib.Path(saved.recovery.location) / "operation.json"
    if damage == "material":
        (operation.parent / "material" / "wc" / "unknown").write_text("changed\n")
    else:
        record = json.loads(operation.read_text())
        if damage == "phase":
            record["phase"] = []
        else:
            record["native"]["metadata"] = []
        operation.write_text(json.dumps(record))
    result = repo.list_recoveries()[0]
    assert not result.ok
    assert result.recovery == saved.recovery
    recovered = repo.recover_changes(saved.recovery, destination=tmp_path / "recovered")
    assert not recovered.ok
    assert recovered.recovery == saved.recovery
    with pytest.raises(ValueError):
        repo.release_changes(saved.recovery)
    if damage != "material":
        result = repo.update_repo()
        assert not result.ok
        assert result.recovery == saved.recovery


def test_svn_interrupted_publication_is_discoverable(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sealed copy survives interruption before its phase record is published."""
    from libvcs._internal import preservation

    _, repo, remote = svn_pair
    (repo.path / "unknown").write_text("local\n")
    real_phase = preservation.RecoveryStore.phase

    def interrupt(store: t.Any, token: t.Any, record: t.Any, phase: str) -> None:
        if phase == "sealed":
            raise KeyboardInterrupt
        real_phase(store, token, record, phase)

    with monkeypatch.context() as patch:
        patch.setattr(preservation.RecoveryStore, "phase", interrupt)
        with pytest.raises(KeyboardInterrupt):
            repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    saved = repo.list_recoveries()[0]
    assert not saved.ok
    assert saved.recovery is not None
    assert repo.update_repo().recovery == saved.recovery
    shutil.rmtree(remote)
    result = repo.recover_changes(saved.recovery, destination=tmp_path / "recovered")
    assert result.ok, result.errors


@pytest.mark.parametrize("replacement", [False, True])
def test_svn_recovery_survives_source_loss(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
    replacement: bool,
) -> None:
    """Sealed copies recover offline without reading or mutating a replacement WC."""
    from libvcs._internal import svn_preservation

    _, repo, remote = svn_pair
    (repo.path / "unknown").write_bytes(b"original\0bytes")
    saved = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert saved.ok, saved.errors
    assert saved.recovery is not None
    shutil.rmtree(remote)
    shutil.rmtree(repo.path)
    if replacement:
        (repo.path / ".svn").mkdir(parents=True)
        (repo.path / "replacement").write_bytes(b"untouched\0bytes")
        before = svn_preservation.tree(repo.path)
    for index in range(2):
        destination = tmp_path / f"independent-{index}"
        result = repo.recover_changes(saved.recovery, destination=destination)
        assert result.ok, result.errors
        assert (destination / "unknown").read_bytes() == b"original\0bytes"
    assert repo.list_recoveries()[0].recovery == saved.recovery
    repo.release_changes(saved.recovery)
    assert repo.list_recoveries() == ()
    if replacement:
        assert svn_preservation.tree(repo.path) == before
    else:
        assert not repo.path.exists()


def test_svn_native_partial_failure_keeps_first_error(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native multi-target failure after progress retains original recovery state."""
    from libvcs._internal import svn_preservation

    source, repo, remote = svn_pair
    other = remote.as_uri() + "/other"
    source.cmd.run(["copy", source.url + "/folder", other, "-m", "other"])
    repo.cmd.run(["switch", other, "folder"])
    (repo.path / "unknown").write_text("local\n")
    original = svn_preservation.WorkingCopy(repo.path).native()
    (source.path / "file").write_text("upstream\n")
    source.cmd.run(["commit", "-m", "advance"])
    source.cmd.run(["delete", other, "-m", "remove switched target"])
    real_run = repo.cmd.run

    def partial(args: list[str], **kwargs: t.Any) -> str:
        if args[0] == "update":
            args = [*args[:-1], "file", "folder"]
        return real_run(args, **kwargs)

    def reject_absence(*args: t.Any) -> t.Any:
        message = "failed update must not delete missing scopes"
        raise AssertionError(message)

    with monkeypatch.context() as patch:
        patch.setattr(repo.cmd, "run", partial)
        patch.setattr(svn_preservation, "restore_missing", reject_absence)
        result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is not None
    assert result.update_state == "failed"
    assert result.errors[0].step == "update"
    assert isinstance(result.errors[0].exception, exc.CommandError)
    assert (repo.path / "file").read_text() == "upstream\n"
    destination = tmp_path / "recovered"
    recovered = repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    assert svn_preservation.WorkingCopy(destination).native() == original


def test_svn_capture_detects_persistent_editor_change(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capture failure preserves an observed external edit and starts no update."""
    import pathlib

    _, repo, _ = svn_pair
    (repo.path / "unknown").write_text("local\n")
    position = repo.get_position()
    real_copy = shutil.copytree

    def edit(source: t.Any, destination: t.Any, *args: t.Any, **kwargs: t.Any) -> t.Any:
        output = real_copy(source, destination, *args, **kwargs)
        if pathlib.Path(destination).name == "wc":
            (repo.path / "unknown").write_text("editor changed\n")
        return output

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "copytree", edit)
        result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.recovery is not None
    assert result.errors[0].step == "capture"
    assert result.update_state == "not-started"
    assert repo.get_position() == position
    assert (repo.path / "unknown").read_text() == "editor changed\n"


def test_svn_rejects_linked_administrative_storage(
    svn_pair: tuple[SvnSync, SvnSync, pathlib.Path],
    tmp_path: pathlib.Path,
) -> None:
    """A full-copy capture cannot depend on pristine objects outside its root."""
    from libvcs._internal import svn_preservation

    _, repo, _ = svn_pair
    pristine = repo.path / ".svn" / "pristine"
    external = tmp_path / "external-pristine"
    pristine.rename(external)
    pristine.symlink_to(external, target_is_directory=True)
    (repo.path / "unknown").write_text("local\n")
    before = svn_preservation.tree(repo.path)
    result = repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.errors[0].step == "precondition"
    assert result.recovery is None
    assert svn_preservation.tree(repo.path) == before


def test_svn_initial_target_overrides_constructor_revision(
    tmp_path: pathlib.Path,
    svn_remote_repo_with_files: pathlib.Path,
) -> None:
    """An explicit initial sync target replaces the constructor revision default."""
    repo = SvnSync(
        url=svn_remote_repo_with_files.as_uri(), path=tmp_path / "copy", rev="999"
    )
    result = repo.update_repo(target=SyncTarget(rev=2))
    assert result.ok, result.errors
    assert repo.get_position().revision == "2"
