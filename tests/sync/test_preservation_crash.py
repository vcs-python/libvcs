"""Outer acceptance: kill real owners and recover their retained native state."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import typing as t

import pytest

from libvcs._internal.preservation import inventory
from libvcs.sync.base import SyncPolicy, SyncTarget
from libvcs.sync.git import GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync

pytestmark = [
    pytest.mark.slow,  # Process death, descendant reaping, and native recovery.
    pytest.mark.skipif(
        sys.platform != "linux", reason="requires Linux child subreaper"
    ),
]

Sync = GitSync | HgSync | SvnSync

_LIBRARY = r"""
import json, os, socket, sys
from libvcs._internal.preservation import RecoveryStore
from libvcs.sync.base import SyncPolicy, SyncTarget
from libvcs.sync.git import GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync
backend, url, path, revision, phase, endpoint = sys.argv[1:]
native_phase = RecoveryStore.phase

def publish(self, token, record, value):
    native_phase(self, token, record, value)
    if value == phase:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.connect(endpoint)
            event = {'pid': os.getpid(), 'phase': value}
            connection.sendall(json.dumps(event).encode())
            connection.recv(1)
        raise AssertionError('barrier released without process death')

RecoveryStore.phase = publish
repo = {'git': GitSync, 'hg': HgSync, 'svn': SvnSync}[backend](url=url, path=path)
selector = {'rev' if backend == 'svn' else 'commit': revision}
result = repo.update_repo(
    target=SyncTarget(**selector), policy=SyncPolicy(dirty='preserve')
)
raise AssertionError(repr(result))
"""

_SUPERVISOR = r"""
import ctypes, json, os, signal, subprocess, sys
# Adopt only this isolated supervisor's descendants, never pytest's children.
assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
child = subprocess.Popen(
    [sys.executable, '-c', sys.argv[1], *sys.argv[2:]], start_new_session=True
)
try:
    sys.stdin.buffer.read(1)
finally:
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    code = child.wait()
    reaped = []
    while True:
        try:
            pid, status = os.waitpid(-1, 0)
            reaped.append([pid, status])
        except ChildProcessError:
            break
    print(json.dumps({'owner': child.pid, 'code': code, 'reaped': reaped}), flush=True)
"""

_HOOK = r"""
import json, os, pathlib, socket
with socket.socket(socket.AF_UNIX) as connection:
    connection.connect(ENDPOINT)
    connection.sendall(json.dumps({
        'pid': os.getpid(), 'native': os.getppid(),
        'advanced': pathlib.Path('advance.txt').read_text(),
    }).encode())
    connection.recv(1)
raise AssertionError('hook released without process death')
"""


class Checkout(t.NamedTuple):
    """Native source and the exact pre-capture and requested positions."""

    repo: Sync
    remote: pathlib.Path
    base: str
    target: str
    status: str


def _backend(repo: Sync) -> str:
    return {GitSync: "git", HgSync: "hg", SvnSync: "svn"}[type(repo)]


def _status(repo: Sync) -> str:
    arguments = {
        "git": ["status", "--porcelain=v1"],
        "hg": ["status", "--copies"],
        "svn": ["status"],
    }
    return repo.cmd.run(arguments[_backend(repo)], check_returncode=True)


@pytest.fixture
def checkout(request: pytest.FixtureRequest, tmp_path: pathlib.Path) -> Checkout:
    """Reuse native fixture configuration while keeping the remote disposable."""
    backend = request.param
    template = request.getfixturevalue(f"{backend}_repo")
    remote_template = pathlib.Path(template.url.removeprefix("file://"))
    remote = tmp_path / "remote"
    shutil.copytree(remote_template, remote)
    repo = type(template)(url=remote.as_uri(), path=tmp_path / "source")
    repo.obtain()
    for name in ("local.txt", "advance.txt"):
        (repo.path / name).write_text("base\n")
    repo.cmd.run(["add", "local.txt", "advance.txt"], check_returncode=True)
    repo.cmd.run(["commit", "-m", "base"], check_returncode=True)
    if backend == "svn":
        repo.cmd.run(["update"], check_returncode=True)
    base = repo.get_position().revision
    (repo.path / "advance.txt").write_text("target\n")
    if backend == "git":
        repo.cmd.run(["add", "advance.txt"], check_returncode=True)
    repo.cmd.run(["commit", "-m", "advance"], check_returncode=True)
    if backend == "svn":
        repo.cmd.run(["update"], check_returncode=True)
    target = repo.get_position().revision
    rollback = {
        "git": ["checkout", "--detach", base],
        "hg": ["update", "-r", base],
        "svn": ["update", "-r", base],
    }
    repo.cmd.run(rollback[backend], check_returncode=True)
    (repo.path / "local.txt").write_text("staged\n")
    if backend == "git":
        repo.cmd.run(["add", "local.txt"], check_returncode=True)
    (repo.path / "local.txt").write_text("working\n")
    (repo.path / "unknown.txt").write_bytes(b"unknown\x00bytes\n")
    return Checkout(repo, remote, base, target, _status(repo))


def _kill_at_barrier(
    checkout: Checkout, phase: str, tmp_path: pathlib.Path
) -> tuple[dict[str, t.Any], dict[str, t.Any]]:
    repo = checkout.repo
    endpoint = str(tmp_path / "event.sock")
    if phase == "native":
        hook = repo.path / ".git" / "hooks" / "post-checkout"
        hook.write_text(f"#!{sys.executable}\nENDPOINT = {endpoint!r}\n" + _HOOK)
        hook.chmod(0o700)
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(endpoint)
        listener.listen(1)
        listener.settimeout(10)
        with subprocess.Popen(
            [
                sys.executable,
                "-c",
                _SUPERVISOR,
                _LIBRARY,
                _backend(repo),
                repo.url,
                str(repo.path),
                checkout.target,
                phase,
                endpoint,
            ],
            env={
                **os.environ,
                "PYTHONPATH": str(pathlib.Path(__file__).resolve().parents[2] / "src"),
            },
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as supervisor:
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(10)
                    event = json.loads(connection.recv(4096))
                    # The blocked process must still exist when its event arrives.
                    os.kill(event["pid"], 0)
                    if phase == "native":
                        assert event["advanced"] == "target\n"
                        assert repo.get_position().revision == checkout.target
                        native = pathlib.Path(f"/proc/{event['native']}/comm")
                        assert native.read_text().strip() == "git"
                    stdout, stderr = supervisor.communicate("kill", timeout=10)
            except TimeoutError:
                stdout, stderr = supervisor.communicate("kill", timeout=10)
                pytest.fail(f"barrier not reached: {stdout} {stderr}")
            finally:
                if supervisor.poll() is None:
                    supervisor.communicate("kill", timeout=10)
            assert supervisor.returncode == 0, stderr
    death = json.loads(stdout)
    assert death["code"] == -signal.SIGKILL
    if phase == "native":
        reaped = dict(death["reaped"])
        assert os.WIFSIGNALED(reaped[event["native"]])
        assert os.WTERMSIG(reaped[event["native"]]) == signal.SIGKILL
        assert event["pid"] in reaped
    else:
        assert death["owner"] == event["pid"]
    return event, death


@pytest.mark.parametrize("checkout", ["git", "hg", "svn"], indirect=True)
@pytest.mark.parametrize("phase", ["sealed", "updating", "inspecting"])
def test_process_death_after_published_capture(
    checkout: Checkout, phase: str, tmp_path: pathlib.Path
) -> None:
    """Killed owners leave discoverable uncertainty and repeatable offline recovery."""
    _kill_at_barrier(checkout, phase, tmp_path)
    _assert_recovery(checkout, phase, tmp_path, advanced=phase == "inspecting")


@pytest.mark.parametrize("checkout", ["git"], indirect=True)
def test_process_death_during_native_checkout(
    checkout: Checkout, tmp_path: pathlib.Path
) -> None:
    """Kill Git itself after checkout progress while its post-checkout hook blocks."""
    _kill_at_barrier(checkout, "native", tmp_path)
    _assert_recovery(checkout, "updating", tmp_path, advanced=True)


def _assert_recovery(
    checkout: Checkout, phase: str, tmp_path: pathlib.Path, *, advanced: bool = False
) -> None:
    repo = checkout.repo
    source_before = inventory(repo.path)
    retained = repo.list_recoveries()
    assert len(retained) == 1
    interrupted = retained[0]
    assert not interrupted.ok
    assert interrupted.update_state == "unknown"
    assert interrupted.preservation_state == "unknown"
    assert [error.step for error in interrupted.errors] == ["interrupted"]
    token = interrupted.recovery
    assert token is not None
    record_path = pathlib.Path(token.location) / "operation.json"
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    assert record["phase"] == phase
    assert repo.get_position().revision == (
        checkout.target if advanced else checkout.base
    )
    assert inventory(repo.path) == source_before
    result = repo.update_repo(
        target=SyncTarget(
            **{"rev" if _backend(repo) == "svn" else "commit": checkout.target}
        ),
        policy=SyncPolicy(dirty="preserve"),
    )
    assert not result.ok
    assert result.recovery == token
    assert inventory(repo.path) == source_before
    assert record_path.read_bytes() == record_bytes
    shutil.rmtree(checkout.remote)
    for attempt in range(2):
        destination = tmp_path / f"recovered-{attempt}"
        recovered = repo.recover_changes(token, destination=destination)
        assert recovered.ok, recovered.errors
        copy = type(repo)(url=repo.url, path=destination)
        assert copy.get_position().revision == checkout.base
        assert (destination / "local.txt").read_text() == "working\n"
        assert (destination / "unknown.txt").read_bytes() == b"unknown\x00bytes\n"
        assert (destination / "advance.txt").read_text() == "base\n"
        assert _status(copy) == checkout.status
        if _backend(repo) == "git":
            assert copy.cmd.run(["show", ":local.txt"]) == "staged\n"
        assert inventory(repo.path) == source_before
        assert record_path.read_bytes() == record_bytes
    assert repo.list_recoveries()[0].recovery == token
