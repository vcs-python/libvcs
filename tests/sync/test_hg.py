"""Tests for libvcs hg repos."""

from __future__ import annotations

import pathlib
import shutil
import typing as t

import pytest

from libvcs import exc
from libvcs._internal.run import run
from libvcs._internal.shortcuts import create_project
from libvcs.pytest_plugin import hg_remote_repo_single_commit_post_init
from libvcs.sync.base import SyncPolicy, SyncResult, SyncTarget
from libvcs.sync.hg import HgSync

if t.TYPE_CHECKING:
    from libvcs.pytest_plugin import CreateRepoFn

if not shutil.which("hg"):
    pytestmark = pytest.mark.skip(reason="hg is not available")


@pytest.fixture(autouse=True)
def set_vcs_hgconfig(
    set_vcs_hgconfig: pathlib.Path,
) -> pathlib.Path:
    """Set mercurial configuration."""
    return set_vcs_hgconfig


def test_hg_position_reports_active_bookmark(hg_repo: HgSync) -> None:
    """An active bookmark takes precedence over the named branch."""
    revision = hg_repo.cmd.run(["log", "-r", ".", "-T", "{node}"]).strip()
    position = hg_repo.get_position()
    assert (position.ref_kind, position.ref_name) == ("branch", "default")
    assert position.revision == revision
    assert position.follows

    hg_repo.cmd.run(["branch", "next"], check_returncode=True)
    assert hg_repo.get_position().ref_name == "next"

    hg_repo.cmd.run(["bookmark", "develop"], check_returncode=True)
    position = hg_repo.get_position()
    assert (position.ref_kind, position.ref_name) == ("bookmark", "develop")
    assert position.revision == revision
    assert position.follows


def test_hg_sync(
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Test HgSync."""
    repo_name = "my_mercurial_project"

    mercurial_repo = HgSync(
        url=f"file://{hg_remote_repo}",
        path=projects_path / repo_name,
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"],
        cwd=projects_path / repo_name,
    )

    assert mercurial_repo.get_revision() == test_repo_revision


def test_repo_mercurial_via_create_project(
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Test HgSync via create_project()."""
    repo_name = "my_mercurial_project"

    mercurial_repo = create_project(
        url=f"file://{hg_remote_repo}",
        path=projects_path / repo_name,
        vcs="hg",
    )

    run(["hg", "init", mercurial_repo.repo_name], cwd=tmp_path)

    mercurial_repo.update_repo()

    test_repo_revision = run(
        ["hg", "parents", "--template={rev}"],
        cwd=projects_path / repo_name,
    )

    assert mercurial_repo.get_revision() == test_repo_revision


def test_vulnerability_2022_03_12_command_injection(
    monkeypatch: pytest.MonkeyPatch,
    user_path: pathlib.Path,
    tmp_path: pathlib.Path,
    hg_remote_repo: pathlib.Path,
) -> None:
    """Prevent hg aliases from executed arbitrary commands via URLs.

    As of 0.11 this code path is/was only executed via .obtain(), so this only would
    effect explicit invocation of .object() or update_repo() of uncloned destination.
    """
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    monkeypatch.chdir(str(random_dir))
    mercurial_repo = create_project(
        url="--config=alias.clone=!touch ./HELLO",
        vcs="hg",
        path="./",
    )
    result = mercurial_repo.update_repo()

    assert not result.ok, "update_repo() should report failure for malicious URL"
    assert any(e.step == "obtain" for e in result.errors), (
        "Error should be recorded under 'obtain' step"
    )
    assert not pathlib.Path(
        random_dir / "HELLO",
    ).exists(), "Prevent command injection in hg aliases"


def test_update_repo_pull_failure_returns_sync_result(
    projects_path: pathlib.Path,
    create_hg_remote_repo: CreateRepoFn,
) -> None:
    """Test that a deleted remote in update_repo() returns SyncResult with error."""
    repo_name = "my_hg_error_project"
    hg_remote = create_hg_remote_repo(
        remote_repo_post_init=hg_remote_repo_single_commit_post_init,
    )

    hg_repo = HgSync(
        url=f"file://{hg_remote}",
        path=projects_path / repo_name,
    )

    hg_repo.update_repo()

    shutil.rmtree(hg_remote)

    result = hg_repo.update_repo()

    assert isinstance(result, SyncResult)
    assert result.ok is False
    assert len(result.errors) > 0
    assert result.errors[0].step == "pull"
    assert isinstance(result.errors[0].exception, exc.CommandError)


@pytest.mark.parametrize("prefix,revision", [("hg+", None), ("", "0")])
def test_obtain_transport_and_revision(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
    prefix: str,
    revision: str | None,
) -> None:
    """Clone strips adapter prefixes and checks out the requested initial revision."""
    base = hg_repo.cmd.run(["log", "-r", "0", "-T", "{node}"])
    (hg_repo.path / "later").write_text("later\n")
    hg_repo.cmd.run(["add", "later"])
    hg_repo.cmd.run(["commit", "-m", "later"])
    repo = HgSync(
        url=prefix + hg_repo.path.as_uri(), path=tmp_path / "clone", rev=revision
    )
    repo.obtain()
    expected = base if revision else hg_repo.get_position().revision
    assert repo.get_position().revision == expected


def _hg_advance(repo: HgSync) -> tuple[str, str]:
    base = repo.get_position().revision
    (repo.path / "upstream").write_text("upstream\n")
    repo.cmd.run(["add", "upstream"])
    repo.cmd.run(["commit", "-m", "upstream"])
    target = repo.get_position().revision
    repo.cmd.run(["update", "--rev", base])
    return base, target


def test_hg_preservation_default_abort(hg_repo: HgSync) -> None:
    """Dirty abort never updates the parent or removes unknown files."""
    base, _ = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("unknown\n")
    result = hg_repo.update_repo()
    assert not result.ok
    assert hg_repo.get_position().revision == base
    assert (hg_repo.path / "unknown").read_text() == "unknown\n"


@pytest.mark.slow
def test_hg_preservation_offline_exact_status(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
) -> None:
    """Independent recovery retains schedules, missing paths, and unknown files."""
    for name in ("removed", "missing"):
        (hg_repo.path / name).write_text(name + "\n")
    hg_repo.cmd.run(["add", "removed", "missing"])
    hg_repo.cmd.run(["commit", "-m", "base files"])
    base, target = _hg_advance(hg_repo)
    hg_repo.cmd.run(["remove", "removed"])
    (hg_repo.path / "missing").unlink()
    (hg_repo.path / "added").write_text("added\n")
    hg_repo.cmd.run(["add", "added"])
    (hg_repo.path / "unknown").write_text("unknown\n")
    (hg_repo.path / "caller.orig").write_text("caller backup\n")
    before = hg_repo.cmd.run(["status", "-0"])
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    assert result.ok, result.errors
    assert result.recovery is not None
    assert result.preservation_state == "restored"
    assert hg_repo.cmd.run(["status", "-0"]) == before
    (hg_repo.path / ".hg" / "hgrc").write_text(
        "[paths]\ndefault = /nonexistent-remote\n"
    )
    destination = tmp_path / "recovered"
    recovered = hg_repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    assert run(["hg", "status", "-0"], cwd=destination) == before
    assert run(["hg", "log", "-r", ".", "-T", "{node}"], cwd=destination) == base
    assert (destination / "caller.orig").read_text() == "caller backup\n"
    hg_repo.release_changes(result.recovery)
    assert hg_repo.list_recoveries() == ()


@pytest.mark.slow
@pytest.mark.parametrize(
    "state",
    ["missing-added", "missing-copy", "removed-present", "removed-capture-failure"],
)
def test_hg_preservation_overlapping_schedule_and_files(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
    state: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retain schedules hidden by status and files hidden by removal schedules."""
    (hg_repo.path / "tracked").write_bytes(b"base\n")
    hg_repo.cmd.run(["add", "tracked"])
    hg_repo.cmd.run(["commit", "-m", "tracked base"])
    _, target = _hg_advance(hg_repo)
    if state.startswith("removed"):
        hg_repo.cmd.run(["remove", "tracked"])
        (hg_repo.path / "tracked").write_bytes(b"valuable\x00recreated\n")
    else:
        if state == "missing-copy":
            hg_repo.cmd.run(["copy", "tracked", "added"])
        else:
            (hg_repo.path / "added").write_text("added\n")
            hg_repo.cmd.run(["add", "added"])
        (hg_repo.path / "added").unlink()
        (hg_repo.path / "unknown").write_text("unknown\n")
    if state == "removed-capture-failure":
        (hg_repo.path / "unknown").write_text("unknown\n")
        native_run = hg_repo.cmd.run

        def fail_shelve(args: t.Any, **kwargs: t.Any) -> str:
            if "shelve" in args:
                raise exc.CommandError(
                    cmd=args, returncode=1, output="native shelve did not start"
                )
            return native_run(args, **kwargs)

        monkeypatch.setattr(hg_repo.cmd, "run", fail_shelve)
    before = hg_repo.cmd.run(["status", "--copies", "-Tjson"])
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    if state == "removed-capture-failure":
        assert not result.ok
        assert (hg_repo.path / "tracked").read_bytes() == b"valuable\x00recreated\n"
        assert hg_repo.cmd.run(["status", "--copies", "-Tjson"]) == before
        return
    assert result.ok, result.errors
    assert result.recovery is not None
    assert hg_repo.cmd.run(["status", "--copies", "-Tjson"]) == before
    destination = tmp_path / "recovered"
    restored = hg_repo.recover_changes(result.recovery, destination=destination)
    assert restored.ok, restored.errors
    assert run(["hg", "status", "--copies", "-Tjson"], cwd=destination) == before
    if state == "removed-present":
        for root in (hg_repo.path, destination):
            assert (root / "tracked").read_bytes() == b"valuable\x00recreated\n"
    else:
        assert not (destination / "added").exists()
        assert (destination / "unknown").read_text() == "unknown\n"


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["disjoint", "text", "binary", "unknown", "missing"])
def test_hg_preservation_native_conflict_recovery(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
    kind: str,
) -> None:
    """Native shelf conflict matrices include independent original-state recovery."""
    shared = hg_repo.path / "shared"
    if kind != "unknown":
        shared.write_bytes(
            b"base\0binary"
            if kind == "binary"
            else b"first\n" + b"middle\n" * 12 + b"last\n"
        )
        hg_repo.cmd.run(["add", "shared"])
        hg_repo.cmd.run(["commit", "-m", "base"])
    base = hg_repo.get_position().revision
    shared.write_bytes(
        b"upstream\0binary"
        if kind == "binary"
        else b"upstream\n" + b"middle\n" * 12 + b"last\n"
    )
    if kind == "unknown":
        hg_repo.cmd.run(["add", "shared"])
    hg_repo.cmd.run(["commit", "-m", "upstream"])
    target = hg_repo.get_position().revision
    hg_repo.cmd.run(["update", "--rev", base])
    if kind == "missing":
        shared.unlink()
    else:
        shared.write_bytes(
            b"local\0binary"
            if kind == "binary"
            else b"first\n" + b"middle\n" * 12 + b"local\n"
            if kind == "disjoint"
            else b"local\n"
        )
    (hg_repo.path / "shared.orig").write_text("caller backup\n")
    before = hg_repo.cmd.run(["status", "-0"])
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    assert result.ok is (kind == "disjoint"), result.errors
    if kind != "disjoint":
        assert result.preservation_state == "conflicted", result.errors
        assert result.conflicts
    assert result.recovery is not None
    assert (hg_repo.path / "shared.orig").read_text() == "caller backup\n"
    destination = tmp_path / "recovered"
    recovered = hg_repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    assert run(["hg", "status", "-0"], cwd=destination) == before
    assert (destination / "shared.orig").read_text() == "caller backup\n"
    if kind == "missing":
        assert not (destination / "shared").exists()
    elif kind == "disjoint":
        assert shared.read_bytes().startswith(b"upstream\n")
        assert shared.read_bytes().endswith(b"local\n")
    else:
        assert (destination / "shared").read_bytes() == (
            b"local\0binary" if kind == "binary" else b"local\n"
        )


@pytest.mark.slow
@pytest.mark.parametrize("identity", ["bookmark", "pending-branch", "missing-only"])
def test_hg_preservation_original_metadata(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
    identity: str,
) -> None:
    """Original metadata and missing-only state survive separate native recovery."""
    (hg_repo.path / "tracked").write_text("tracked\n")
    hg_repo.cmd.run(["add", "tracked"])
    hg_repo.cmd.run(["commit", "-m", "base"])
    _, target = _hg_advance(hg_repo)
    if identity == "bookmark":
        hg_repo.cmd.run(["bookmark", "local-bookmark"])
        (hg_repo.path / "tracked").write_text("local\n")
    elif identity == "pending-branch":
        hg_repo.cmd.run(["branch", "pending-branch"])
    else:
        (hg_repo.path / "tracked").unlink()
    original = hg_repo.get_position()
    before = hg_repo.cmd.run(["status", "-0"])
    assert hg_repo.is_dirty()
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    assert result.ok, result.errors
    assert result.recovery is not None
    destination = tmp_path / "recovered"
    recovered = hg_repo.recover_changes(result.recovery, destination=destination)
    assert recovered.ok, recovered.errors
    repo = HgSync(url=hg_repo.url, path=destination)
    assert repo.get_position() == original
    assert repo.cmd.run(["status", "-0"]) == before


@pytest.mark.slow
@pytest.mark.parametrize("collision", [True, False])
def test_hg_preservation_ignored_collision(hg_repo: HgSync, collision: bool) -> None:
    """Ignored output blocks only target writes that overlap it."""
    base, target = _hg_advance(hg_repo)
    (hg_repo.path / ".hgignore").write_text("syntax: glob\nupstream\ncache\n")
    hg_repo.cmd.run(["add", ".hgignore"])
    hg_repo.cmd.run(["commit", "-m", "ignore"])
    base = hg_repo.get_position().revision
    output = hg_repo.path / ("upstream" if collision else "cache")
    output.write_text("ignored\n")
    result = hg_repo.update_repo(target=SyncTarget(commit=target))
    assert result.ok is not collision, result.errors
    assert output.read_text() == "ignored\n"
    if collision:
        assert hg_repo.get_position().revision == base
        assert result.recovery is None


@pytest.mark.slow
@pytest.mark.parametrize(
    "fault", ["capture", "update", "restore", "inspection", "publication"]
)
def test_hg_preservation_retains_token_after_fault(
    hg_repo: HgSync,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    fault: str,
) -> None:
    """Native failure stages retain their first error and independent shelf."""
    from libvcs._internal import preservation

    _, target = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("unknown\n")
    real_run = hg_repo.cmd.run

    def fail_command(args: t.Any, **kwargs: t.Any) -> str:
        if (fault == "update" and "update" in args) or (
            fault == "restore" and "unshelve" in args
        ):
            raise exc.CommandError(cmd=args, returncode=1, output=fault)
        output = real_run(args, **kwargs)
        if fault == "capture" and "shelve" in args:
            raise exc.CommandError(cmd=args, returncode=1, output=fault)
        return output

    def fail_inspection() -> tuple[t.Any, ...]:
        raise exc.CommandError(cmd="hg resolve", returncode=1, output="inspection")

    def fail_finish(*args: t.Any, **kwargs: t.Any) -> None:
        message = "publication"
        raise OSError(message)

    with monkeypatch.context() as patch:
        patch.setattr(hg_repo.cmd, "run", fail_command)
        if fault == "inspection":
            patch.setattr(hg_repo, "_conflicts", fail_inspection)
        if fault == "publication":
            patch.setattr(preservation.RecoveryStore, "finish", fail_finish)
        result = hg_repo.update_repo(
            target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
        )
    assert not result.ok
    assert result.recovery is not None
    assert result.errors[0].step == fault
    assert hg_repo.list_recoveries()[0].recovery == result.recovery
    if fault == "inspection":
        assert result.preservation_state == "unknown"
    if fault == "update":
        shutil.rmtree(hg_repo.path / ".hg" / "shelved")
        recovered = hg_repo.recover_changes(
            result.recovery, destination=tmp_path / "recovered"
        )
        assert recovered.ok, recovered.errors
        assert (tmp_path / "recovered" / "unknown").read_text() == "unknown\n"


@pytest.mark.slow
def test_hg_preservation_interrupted_capture(
    hg_repo: HgSync,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Interrupted shelf creation remains discoverable without resuming update."""
    _, target = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("unknown\n")
    real_run = hg_repo.cmd.run

    def interrupt(args: t.Any, **kwargs: t.Any) -> str:
        output = real_run(args, **kwargs)
        if "shelve" in args:
            raise KeyboardInterrupt
        return output

    with monkeypatch.context() as patch:
        patch.setattr(hg_repo.cmd, "run", interrupt)
        with pytest.raises(KeyboardInterrupt):
            hg_repo.update_repo(
                target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
            )
    interrupted = hg_repo.list_recoveries()[0]
    assert not interrupted.ok
    assert interrupted.recovery is not None
    assert hg_repo.update_repo().recovery == interrupted.recovery
    result = hg_repo.recover_changes(
        interrupted.recovery, destination=tmp_path / "recovered"
    )
    assert result.ok, result.errors
    assert (tmp_path / "recovered" / "unknown").read_text() == "unknown\n"


@pytest.mark.parametrize(
    "native", ["wlock", "shelvedstate", "rebasestate", "subrepo", "nested"]
)
def test_hg_preservation_native_preconditions(hg_repo: HgSync, native: str) -> None:
    """Native busy and unsupported nested scopes fail before pulling or capturing."""
    if native == "wlock":
        (hg_repo.path / ".hg" / native).symlink_to("busy-owner:12345")
    elif native == "subrepo":
        (hg_repo.path / ".hgsub").write_text("child = ../child\n")
    elif native == "nested":
        (hg_repo.path / "child" / ".hg").mkdir(parents=True)
    else:
        (hg_repo.path / ".hg" / native).write_text("busy\n")
    result = hg_repo.update_repo(policy=SyncPolicy(dirty="preserve"))
    assert not result.ok
    assert result.errors[0].step == "precondition"
    assert result.recovery is None


@pytest.mark.slow
@pytest.mark.parametrize("drift", ["keep", "warn"])
def test_hg_preservation_drift_keeps_dirty_position(
    hg_repo: HgSync,
    drift: t.Literal["keep", "warn"],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep and warn compare resolved nodes and leave dirty checkouts untouched."""
    base, target = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("local\n")
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(drift=drift)
    )
    assert result.ok, result.errors
    assert result.recovery is None
    assert hg_repo.get_position().revision == base
    assert (hg_repo.path / "unknown").read_text() == "local\n"
    warnings = [record for record in caplog.records if record.name == "libvcs.sync.hg"]
    assert bool(warnings) is (drift == "warn")
    if warnings:
        assert warnings[0].__dict__["vcs_type"] == "hg"


@pytest.mark.slow
def test_hg_preservation_release_owns_only_named_shelf(hg_repo: HgSync) -> None:
    """Release preserves a caller shelf and detects changed owned material."""
    _, target = _hg_advance(hg_repo)
    (hg_repo.path / "caller").write_text("caller\n")
    hg_repo.cmd.run(["shelve", "--unknown", "--name", "caller", "--message", "caller"])
    caller = (hg_repo.path / ".hg" / "shelved" / "caller.patch").read_bytes()
    (hg_repo.path / "unknown").write_text("local\n")
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    assert result.ok, result.errors
    assert result.recovery is not None
    owned = hg_repo.path / ".hg" / "shelved" / f"libvcs-{result.recovery.id}.patch"
    original = owned.read_bytes()
    owned.write_bytes(original + b"changed\n")
    with pytest.raises(ValueError, match="ownership"):
        hg_repo.release_changes(result.recovery)
    assert pathlib.Path(result.recovery.location).exists()
    owned.write_bytes(original)
    hg_repo.release_changes(result.recovery)
    assert hg_repo.list_recoveries() == ()
    assert (hg_repo.path / ".hg" / "shelved" / "caller.patch").read_bytes() == caller


@pytest.mark.slow
@pytest.mark.parametrize("damage", ["phase", "status", "material"])
def test_hg_preservation_damaged_records_retain_token(
    hg_repo: HgSync,
    tmp_path: pathlib.Path,
    damage: str,
) -> None:
    """Damaged schema or sealed artifacts never become successful recovery."""
    import json

    _, target = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("local\n")
    saved = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
    )
    assert saved.ok, saved.errors
    assert saved.recovery is not None
    record_path = pathlib.Path(saved.recovery.location) / "operation.json"
    if damage == "material":
        patch = record_path.parent / "material" / f"libvcs-{saved.recovery.id}.patch"
        patch.write_bytes(b"corrupt")
    else:
        record = json.loads(record_path.read_text())
        if damage == "phase":
            record["phase"] = []
        else:
            record["original"]["status"] = []
        record_path.write_text(json.dumps(record))
    found = hg_repo.list_recoveries()[0]
    assert not found.ok
    assert found.recovery == saved.recovery
    destination = tmp_path / "recovered"
    result = hg_repo.recover_changes(saved.recovery, destination=destination)
    assert not result.ok
    assert result.recovery == saved.recovery
    assert not destination.exists()
    if damage != "material":
        result = hg_repo.update_repo()
        assert not result.ok
        assert result.recovery == saved.recovery


@pytest.mark.slow
def test_hg_target_equal_bookmark_follow_and_keep(hg_repo: HgSync) -> None:
    """Equal nodes are not drift; follow activates an explicitly selected bookmark."""
    hg_repo.cmd.run(["bookmark", "--inactive", "alias"])
    original = hg_repo.get_position()
    target = SyncTarget(branch="alias")
    assert hg_repo.resolve_target(target).revision == original.revision
    assert hg_repo.resolve_target(SyncTarget(rev="alias")).ref_kind == "bookmark"
    result = hg_repo.update_repo(target=target, policy=SyncPolicy(drift="keep"))
    assert result.ok, result.errors
    assert hg_repo.get_position() == original
    result = hg_repo.update_repo(target=target)
    assert result.ok, result.errors
    assert hg_repo.get_position().ref_name == "alias"
    assert hg_repo.get_position().ref_kind == "bookmark"


@pytest.mark.slow
def test_hg_preservation_phase_failure_stops_mutation(
    hg_repo: HgSync, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed phase write retains the shelf without starting another mutation."""
    from libvcs._internal import preservation

    base, target = _hg_advance(hg_repo)
    (hg_repo.path / "unknown").write_text("local\n")
    real_phase = preservation.RecoveryStore.phase
    real_run = hg_repo.cmd.run
    mutated = []

    def fail_phase(
        store: preservation.RecoveryStore,
        token: t.Any,
        record: t.Any,
        phase: str,
    ) -> None:
        if phase == "updating":
            message = "phase publication failed"
            raise OSError(message)
        real_phase(store, token, record, phase)

    def record_run(args: t.Any, **kwargs: t.Any) -> str:
        if "update" in args or "unshelve" in args:
            mutated.append(args)
        return real_run(args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(preservation.RecoveryStore, "phase", fail_phase)
        patch.setattr(hg_repo.cmd, "run", record_run)
        result = hg_repo.update_repo(
            target=SyncTarget(commit=target), policy=SyncPolicy(dirty="preserve")
        )
    assert not result.ok
    assert result.recovery is not None
    assert not mutated
    assert hg_repo.get_position().revision == base
    assert not (hg_repo.path / "unknown").exists()
    assert hg_repo.list_recoveries()[0].recovery == result.recovery


@pytest.mark.slow
def test_hg_discard_preserves_ignored_output(hg_repo: HgSync) -> None:
    """Explicit discard removes ordinary dirt while retaining ignored output."""
    (hg_repo.path / ".hgignore").write_text("syntax: glob\ncache\n")
    (hg_repo.path / "tracked").write_text("base\n")
    hg_repo.cmd.run(["add", ".hgignore", "tracked"])
    hg_repo.cmd.run(["commit", "-m", "tracked base"])
    _, target = _hg_advance(hg_repo)
    (hg_repo.path / "tracked").write_text("local\n")
    (hg_repo.path / "added").write_text("added\n")
    hg_repo.cmd.run(["add", "added"])
    (hg_repo.path / "unknown").write_text("unknown\n")
    (hg_repo.path / "cache").write_text("ignored\n")
    result = hg_repo.update_repo(
        target=SyncTarget(commit=target), policy=SyncPolicy(dirty="discard")
    )
    assert result.ok, result.errors
    assert result.recovery is None
    assert hg_repo.get_position().revision == target
    assert hg_repo.cmd.run(["status", "-0"]) == ""
    assert (hg_repo.path / "tracked").read_text() == "base\n"
    assert not (hg_repo.path / "added").exists()
    assert not (hg_repo.path / "unknown").exists()
    assert (hg_repo.path / "cache").read_text() == "ignored\n"


@pytest.mark.slow
def test_hg_target_aliases_are_metadata_only(
    hg_repo: HgSync, caplog: pytest.LogCaptureFixture
) -> None:
    """Named branches, tags, and revisions at the same node cause no drift."""
    hg_repo.cmd.run(["tag", "--local", "alias"])
    original = hg_repo.get_position()
    for target in (
        SyncTarget(branch="default"),
        SyncTarget(tag="alias"),
        SyncTarget(commit=original.revision),
        SyncTarget(rev="alias"),
    ):
        assert hg_repo.resolve_target(target).revision == original.revision
        result = hg_repo.update_repo(target=target, policy=SyncPolicy(drift="warn"))
        assert result.ok, result.errors
        assert result.update_state == "not-started"
    assert hg_repo.get_position() == original
    assert not [record for record in caplog.records if record.name == "libvcs.sync.hg"]
