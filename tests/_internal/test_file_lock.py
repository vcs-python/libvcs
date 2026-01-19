"""Tests for libvcs._internal.file_lock."""

from __future__ import annotations

import os
import pickle  # Used to test exception picklability for multiprocessing support
import threading
import time
import typing as t
from pathlib import Path

import pytest

from libvcs._internal.file_lock import (
    AcquireReturnProxy,
    FileLock,
    FileLockContext,
    FileLockError,
    FileLockStale,
    FileLockTimeout,
    atomic_init,
)

# =============================================================================
# FileLock Sync Tests
# =============================================================================


class LockAcquireFixture(t.NamedTuple):
    """Test fixture for FileLock acquisition scenarios."""

    test_id: str
    timeout: float
    should_acquire: bool
    description: str


LOCK_ACQUIRE_FIXTURES = [
    LockAcquireFixture(
        test_id="default_timeout",
        timeout=-1.0,
        should_acquire=True,
        description="Acquire with infinite timeout",
    ),
    LockAcquireFixture(
        test_id="explicit_timeout",
        timeout=5.0,
        should_acquire=True,
        description="Acquire with 5s timeout",
    ),
    LockAcquireFixture(
        test_id="zero_timeout",
        timeout=0.0,
        should_acquire=True,
        description="Non-blocking acquire on free lock",
    ),
]


class TestFileLock:
    """Tests for FileLock synchronous operations."""

    @pytest.mark.parametrize(
        list(LockAcquireFixture._fields),
        LOCK_ACQUIRE_FIXTURES,
        ids=[f.test_id for f in LOCK_ACQUIRE_FIXTURES],
    )
    def test_acquire_scenarios(
        self,
        tmp_path: Path,
        test_id: str,
        timeout: float,
        should_acquire: bool,
        description: str,
    ) -> None:
        """Test various lock acquisition scenarios."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path, timeout=timeout)

        if should_acquire:
            with lock:
                assert lock.is_locked
                assert lock.lock_counter == 1
            assert not lock.is_locked

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test FileLock as context manager."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        assert not lock.is_locked
        with lock:
            assert lock.is_locked
            assert lock_path.exists()
        assert not lock.is_locked
        assert not lock_path.exists()

    def test_explicit_acquire_release(self, tmp_path: Path) -> None:
        """Test explicit acquire() and release()."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        proxy = lock.acquire()
        assert isinstance(proxy, AcquireReturnProxy)
        assert lock.is_locked
        assert lock.lock_counter == 1

        lock.release()
        assert not lock.is_locked
        assert lock.lock_counter == 0

    def test_reentrant_locking(self, tmp_path: Path) -> None:
        """Test reentrant lock acquisition."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        lock.acquire()
        assert lock.lock_counter == 1

        lock.acquire()
        assert lock.lock_counter == 2

        lock.acquire()
        assert lock.lock_counter == 3

        lock.release()
        assert lock.lock_counter == 2
        assert lock.is_locked

        lock.release()
        assert lock.lock_counter == 1
        assert lock.is_locked

        lock.release()
        assert lock.lock_counter == 0
        assert not lock.is_locked

    def test_force_release(self, tmp_path: Path) -> None:
        """Test force=True releases regardless of counter."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        lock.acquire()
        lock.acquire()
        lock.acquire()
        assert lock.lock_counter == 3

        lock.release(force=True)
        assert lock.lock_counter == 0
        assert not lock.is_locked

    def test_non_blocking_acquire(self, tmp_path: Path) -> None:
        """Test non-blocking acquire with blocking=False."""
        lock_path = tmp_path / "test.lock"

        # First lock acquires
        lock1 = FileLock(lock_path)
        lock1.acquire()

        # Second lock should fail immediately
        lock2 = FileLock(lock_path)
        with pytest.raises(FileLockTimeout):
            lock2.acquire(blocking=False)

        lock1.release()

    def test_timeout_on_held_lock(self, tmp_path: Path) -> None:
        """Test timeout when lock is held by another process."""
        lock_path = tmp_path / "test.lock"

        # Hold the lock
        lock1 = FileLock(lock_path)
        lock1.acquire()

        # Try to acquire with short timeout
        lock2 = FileLock(lock_path, timeout=0.1)
        with pytest.raises(FileLockTimeout) as exc_info:
            lock2.acquire()

        assert exc_info.value.lock_file == str(lock_path)
        assert exc_info.value.timeout == 0.1

        lock1.release()

    def test_pid_written_to_lock_file(self, tmp_path: Path) -> None:
        """Test PID is written to lock file for debugging."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        with lock:
            content = lock_path.read_text()
            assert content == str(os.getpid())

    def test_acquire_return_proxy_context(self, tmp_path: Path) -> None:
        """Test AcquireReturnProxy as context manager."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        with lock.acquire() as acquired_lock:
            assert acquired_lock is lock
            assert lock.is_locked

        assert not lock.is_locked

    def test_lock_file_property(self, tmp_path: Path) -> None:
        """Test lock_file property returns path."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        assert lock.lock_file == str(lock_path)

    def test_repr(self, tmp_path: Path) -> None:
        """Test __repr__ shows lock state."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)

        assert "unlocked" in repr(lock)
        with lock:
            assert "locked" in repr(lock)


class StaleLockFixture(t.NamedTuple):
    """Test fixture for stale lock scenarios."""

    test_id: str
    stale_timeout: float
    sleep_time: float
    should_acquire: bool


STALE_LOCK_FIXTURES = [
    StaleLockFixture(
        test_id="fresh_lock_blocks",
        stale_timeout=1.0,
        sleep_time=0.0,
        should_acquire=False,
    ),
    StaleLockFixture(
        test_id="stale_lock_acquired",
        stale_timeout=0.1,
        sleep_time=0.2,
        should_acquire=True,
    ),
]


class TestFileLockStaleDetection:
    """Tests for stale lock detection and removal."""

    @pytest.mark.parametrize(
        list(StaleLockFixture._fields),
        STALE_LOCK_FIXTURES,
        ids=[f.test_id for f in STALE_LOCK_FIXTURES],
    )
    def test_stale_detection(
        self,
        tmp_path: Path,
        test_id: str,
        stale_timeout: float,
        sleep_time: float,
        should_acquire: bool,
    ) -> None:
        """Test stale lock detection scenarios."""
        lock_path = tmp_path / "test.lock"

        # Create a lock file manually (simulating orphaned lock)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()))

        if sleep_time > 0:
            time.sleep(sleep_time)

        lock = FileLock(lock_path, timeout=0.05, stale_timeout=stale_timeout)

        if should_acquire:
            with lock:
                assert lock.is_locked
        else:
            with pytest.raises(FileLockTimeout):
                lock.acquire()


# =============================================================================
# FileLockContext Tests
# =============================================================================


class TestFileLockContext:
    """Tests for FileLockContext dataclass."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        ctx = FileLockContext("/tmp/test.lock")

        assert ctx.lock_file == "/tmp/test.lock"
        assert ctx.timeout == -1.0
        assert ctx.poll_interval == 0.05
        assert ctx.stale_timeout == 300.0
        assert ctx.mode == 0o644
        assert ctx.lock_file_fd is None
        assert ctx.lock_counter == 0

    def test_is_locked_property(self) -> None:
        """Test is_locked property."""
        ctx = FileLockContext("/tmp/test.lock")

        assert not ctx.is_locked

        ctx.lock_file_fd = 5
        assert ctx.is_locked


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for exception classes."""

    def test_file_lock_timeout_message(self) -> None:
        """Test FileLockTimeout message format."""
        exc = FileLockTimeout("/tmp/test.lock", 30.0)

        assert str(exc) == "Timeout (30.0s) waiting for lock: /tmp/test.lock"
        assert exc.lock_file == "/tmp/test.lock"
        assert exc.timeout == 30.0

    def test_file_lock_timeout_inheritance(self) -> None:
        """Test FileLockTimeout inherits from TimeoutError."""
        exc = FileLockTimeout("/tmp/test.lock", 30.0)

        assert isinstance(exc, FileLockError)
        assert isinstance(exc, TimeoutError)

    def test_file_lock_timeout_picklable(self) -> None:
        """Test FileLockTimeout is picklable for multiprocessing support."""
        exc = FileLockTimeout("/tmp/test.lock", 30.0)
        pickled = pickle.dumps(exc)
        restored = pickle.loads(pickled)

        assert restored.lock_file == exc.lock_file
        assert restored.timeout == exc.timeout

    def test_file_lock_stale_message(self) -> None:
        """Test FileLockStale message format."""
        exc = FileLockStale("/tmp/test.lock", 3600.0)

        assert str(exc) == "Stale lock (3600.0s old): /tmp/test.lock"
        assert exc.lock_file == "/tmp/test.lock"
        assert exc.age_seconds == 3600.0

    def test_file_lock_stale_picklable(self) -> None:
        """Test FileLockStale is picklable for multiprocessing support."""
        exc = FileLockStale("/tmp/test.lock", 3600.0)
        pickled = pickle.dumps(exc)
        restored = pickle.loads(pickled)

        assert restored.lock_file == exc.lock_file
        assert restored.age_seconds == exc.age_seconds


# =============================================================================
# atomic_init Tests
# =============================================================================


class AtomicInitFixture(t.NamedTuple):
    """Test fixture for atomic_init scenarios."""

    test_id: str
    pre_initialized: bool
    expected_result: bool
    description: str


ATOMIC_INIT_FIXTURES = [
    AtomicInitFixture(
        test_id="first_init",
        pre_initialized=False,
        expected_result=True,
        description="First call performs initialization",
    ),
    AtomicInitFixture(
        test_id="already_initialized",
        pre_initialized=True,
        expected_result=False,
        description="Already initialized returns False",
    ),
]


class TestAtomicInit:
    """Tests for atomic_init function."""

    @pytest.mark.parametrize(
        list(AtomicInitFixture._fields),
        ATOMIC_INIT_FIXTURES,
        ids=[f.test_id for f in ATOMIC_INIT_FIXTURES],
    )
    def test_atomic_init_scenarios(
        self,
        tmp_path: Path,
        test_id: str,
        pre_initialized: bool,
        expected_result: bool,
        description: str,
    ) -> None:
        """Test atomic_init return values."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        marker = resource_path / ".initialized"

        if pre_initialized:
            marker.touch()

        init_called = []

        def init_fn() -> None:
            init_called.append(True)

        result = atomic_init(resource_path, init_fn)

        assert result == expected_result
        if expected_result:
            assert len(init_called) == 1
        else:
            assert len(init_called) == 0
        assert marker.exists()

    def test_atomic_init_creates_marker(self, tmp_path: Path) -> None:
        """Test atomic_init creates marker file."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()

        atomic_init(resource_path, lambda: None)

        assert (resource_path / ".initialized").exists()

    def test_atomic_init_custom_marker(self, tmp_path: Path) -> None:
        """Test atomic_init with custom marker name."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()

        atomic_init(resource_path, lambda: None, marker_name=".custom_marker")

        assert (resource_path / ".custom_marker").exists()
        assert not (resource_path / ".initialized").exists()

    def test_atomic_init_cleans_partial_state(self, tmp_path: Path) -> None:
        """Test atomic_init cleans partial state before init."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        # Create partial state (no marker)
        (resource_path / "partial_file.txt").write_text("partial")

        def init_fn() -> None:
            (resource_path / "complete_file.txt").write_text("complete")

        atomic_init(resource_path, init_fn)

        # Partial file should be gone, complete file should exist
        assert not (resource_path / "partial_file.txt").exists()
        assert (resource_path / "complete_file.txt").exists()

    def test_atomic_init_concurrent(self, tmp_path: Path) -> None:
        """Test atomic_init handles concurrent calls."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        init_count = {"count": 0}
        lock = threading.Lock()

        def init_fn() -> None:
            with lock:
                init_count["count"] += 1
            time.sleep(0.1)  # Simulate slow init

        threads = []
        for _ in range(5):
            t = threading.Thread(target=atomic_init, args=(resource_path, init_fn))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one thread should have initialized
        assert init_count["count"] == 1
