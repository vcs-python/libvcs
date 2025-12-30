"""Async tests for libvcs._internal.file_lock."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from libvcs._internal.file_lock import (
    AsyncAcquireReturnProxy,
    AsyncFileLock,
    FileLockTimeout,
    async_atomic_init,
)


class TestAsyncFileLock:
    """Tests for AsyncFileLock asynchronous operations."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path: Path) -> None:
        """Test AsyncFileLock as async context manager."""
        lock_path = tmp_path / "test.lock"
        lock = AsyncFileLock(lock_path)

        assert not lock.is_locked
        async with lock:
            assert lock.is_locked
            assert lock_path.exists()
        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_async_explicit_acquire_release(self, tmp_path: Path) -> None:
        """Test explicit acquire() and release() for async lock."""
        lock_path = tmp_path / "test.lock"
        lock = AsyncFileLock(lock_path)

        proxy = await lock.acquire()
        assert isinstance(proxy, AsyncAcquireReturnProxy)
        assert lock.is_locked

        await lock.release()
        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_async_reentrant(self, tmp_path: Path) -> None:
        """Test async reentrant locking."""
        lock_path = tmp_path / "test.lock"
        lock = AsyncFileLock(lock_path)

        await lock.acquire()
        assert lock.lock_counter == 1

        await lock.acquire()
        assert lock.lock_counter == 2

        await lock.release()
        assert lock.lock_counter == 1

        await lock.release()
        assert lock.lock_counter == 0

    @pytest.mark.asyncio
    async def test_async_timeout(self, tmp_path: Path) -> None:
        """Test async lock timeout."""
        lock_path = tmp_path / "test.lock"

        lock1 = AsyncFileLock(lock_path)
        await lock1.acquire()

        lock2 = AsyncFileLock(lock_path, timeout=0.1)
        with pytest.raises(FileLockTimeout):
            await lock2.acquire()

        await lock1.release()

    @pytest.mark.asyncio
    async def test_async_non_blocking(self, tmp_path: Path) -> None:
        """Test async non-blocking acquire."""
        lock_path = tmp_path / "test.lock"

        lock1 = AsyncFileLock(lock_path)
        await lock1.acquire()

        lock2 = AsyncFileLock(lock_path)
        with pytest.raises(FileLockTimeout):
            await lock2.acquire(blocking=False)

        await lock1.release()

    @pytest.mark.asyncio
    async def test_async_acquire_proxy_context(self, tmp_path: Path) -> None:
        """Test AsyncAcquireReturnProxy as async context manager."""
        lock_path = tmp_path / "test.lock"
        lock = AsyncFileLock(lock_path)

        proxy = await lock.acquire()
        async with proxy as acquired_lock:
            assert acquired_lock is lock
            assert lock.is_locked

        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_async_concurrent_acquisition(self, tmp_path: Path) -> None:
        """Test concurrent async lock acquisition."""
        lock_path = tmp_path / "test.lock"
        results: list[int] = []

        async def worker(lock: AsyncFileLock, worker_id: int) -> None:
            async with lock:
                results.append(worker_id)
                await asyncio.sleep(0.01)

        lock = AsyncFileLock(lock_path)
        await asyncio.gather(*[worker(lock, i) for i in range(3)])

        # All workers should have completed
        assert len(results) == 3
        # Results should be sequential (one at a time)
        assert sorted(results) == list(range(3))

    @pytest.mark.asyncio
    async def test_async_repr(self, tmp_path: Path) -> None:
        """Test __repr__ for async lock."""
        lock_path = tmp_path / "test.lock"
        lock = AsyncFileLock(lock_path)

        assert "unlocked" in repr(lock)
        async with lock:
            assert "locked" in repr(lock)


class TestAsyncAtomicInit:
    """Tests for async_atomic_init function."""

    @pytest.mark.asyncio
    async def test_async_atomic_init_first(self, tmp_path: Path) -> None:
        """Test first async_atomic_init performs initialization."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        init_called: list[bool] = []

        async def async_init_fn() -> None:
            init_called.append(True)
            await asyncio.sleep(0)

        result = await async_atomic_init(resource_path, async_init_fn)

        assert result is True
        assert len(init_called) == 1
        assert (resource_path / ".initialized").exists()

    @pytest.mark.asyncio
    async def test_async_atomic_init_already_done(self, tmp_path: Path) -> None:
        """Test async_atomic_init skips when already initialized."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        (resource_path / ".initialized").touch()

        init_called: list[bool] = []

        async def async_init_fn() -> None:
            init_called.append(True)

        result = await async_atomic_init(resource_path, async_init_fn)

        assert result is False
        assert len(init_called) == 0

    @pytest.mark.asyncio
    async def test_async_atomic_init_sync_fn(self, tmp_path: Path) -> None:
        """Test async_atomic_init works with sync init function."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        init_called: list[bool] = []

        def sync_init_fn() -> None:
            init_called.append(True)

        result = await async_atomic_init(resource_path, sync_init_fn)

        assert result is True
        assert len(init_called) == 1

    @pytest.mark.asyncio
    async def test_async_atomic_init_concurrent(self, tmp_path: Path) -> None:
        """Test async_atomic_init handles concurrent calls."""
        resource_path = tmp_path / "resource"
        resource_path.mkdir()
        init_count = {"count": 0}

        async def init_fn() -> None:
            init_count["count"] += 1
            await asyncio.sleep(0.1)  # Simulate slow init

        results = await asyncio.gather(
            *[async_atomic_init(resource_path, init_fn) for _ in range(5)]
        )

        # Only one should have returned True
        assert sum(results) == 1
        # Only one init should have run
        assert init_count["count"] == 1
