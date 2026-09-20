"""Durable recovery ownership and publication checks."""

from __future__ import annotations

import dataclasses
import pathlib

import pytest

from libvcs import RecoveryToken, SyncPolicy, SyncTarget
from libvcs._internal.preservation import RecoveryStore, atomic_record, inventory


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"branch": "a", "tag": "b"},
        {"rev": True},
        {"rev": -1},
        {"branch": "-bad"},
        {"remote": "origin"},
    ],
)
def test_target_rejects_invalid_selectors(kwargs: dict[str, object]) -> None:
    """Invalid selectors fail without invoking a backend."""
    with pytest.raises((ValueError, TypeError)):
        SyncTarget(**kwargs)  # type: ignore[arg-type]


def test_policy_and_target_are_immutable() -> None:
    """Policy defaults protect dirt and malformed policy names fail early."""
    assert SyncPolicy().dirty == "abort"
    assert SyncTarget(rev=0).rev == 0
    with pytest.raises(ValueError, match="dirty"):
        SyncPolicy(dirty="reset")  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        SyncTarget(branch="main").branch = "next"  # type: ignore[misc]


def test_store_publication_discovery_and_lock(tmp_path: pathlib.Path) -> None:
    """Interrupted records remain discoverable and concurrent owners fail promptly."""
    source = tmp_path / "source"
    source.mkdir()
    store = RecoveryStore(source, "git", source)
    with store.lock():
        token, record = store.create(original={"revision": "base"}, target={})
        with pytest.raises(RuntimeError, match="busy"), store.lock():
            pytest.fail("acquired an owned lock")
    snapshots = store.discover()
    assert len(snapshots) == 1
    assert snapshots[0].recovery == token
    assert snapshots[0].preservation_state == "unknown"
    assert not snapshots[0].ok
    assert store.read(token)["phase"] == "capturing"
    with pytest.raises(ValueError, match="backend"):
        store.read(dataclasses.replace(token, backend="hg"))
    with pytest.raises(ValueError, match="location"):
        store.read(RecoveryToken(token.id, "git", str(tmp_path)))
    source.rename(tmp_path / "old-source")
    source.mkdir()
    # Replaced filesystems may immediately reuse inodes; force a mismatched record.
    record["source_identity"] = [-1, -1]
    store.write(token, record)
    with pytest.raises(ValueError, match="identity"):
        store.validate_source(record)


def test_atomic_record_keeps_previous_on_publish_failure(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed rename leaves the prior complete record readable."""
    path = tmp_path / "operation.json"
    atomic_record(path, {"phase": "sealed"})

    def fail_replace(*args: object) -> None:
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(pathlib.Path, "replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        atomic_record(path, {"phase": "updating"})
    assert '"sealed"' in path.read_text()
    assert list(tmp_path.iterdir()) == [path]


def test_destination_and_inventory_boundaries(tmp_path: pathlib.Path) -> None:
    """Destinations cannot overlap sources or follow dangling symlinks."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_bytes(b"\x00payload")
    (source / "link").symlink_to("file")
    store = RecoveryStore(source, "git", source)
    for destination in [source, source / "nested", tmp_path]:
        with pytest.raises(ValueError):
            store.destination(destination)
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match=r"symlink|exist"):
        store.destination(dangling)
    data = inventory(source)
    assert data["file"]["sha256"]
    assert data["link"]["target"] == "file"
    (source / "file").write_bytes(b"changed")
    assert inventory(source) != data
