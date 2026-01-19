"""Typed, asyncio-friendly file locking based on filelock patterns.

This module provides atomic file-based locking with support for both synchronous
and asynchronous contexts. It uses the SoftFileLock pattern (``os.O_CREAT | os.O_EXCL``)
for portable, atomic lock acquisition.

Note
----
This is an internal API not covered by versioning policy.

Design Principles
-----------------
1. **Atomic acquisition**: Uses ``os.O_CREAT | os.O_EXCL`` for race-free lock creation
2. **Reentrant locking**: Same thread can acquire lock multiple times
3. **Stale lock detection**: Auto-removes locks older than configurable timeout
4. **Async support**: :class:`AsyncFileLock` wraps sync lock with ``asyncio.sleep``
5. **PID tracking**: Writes PID to lock file for debugging
6. **Two-file pattern**: Lock file (temporary) + marker file (permanent)

Examples
--------
Basic synchronous usage:

>>> import tempfile
>>> import pathlib
>>> with tempfile.TemporaryDirectory() as tmpdir:
...     lock_path = pathlib.Path(tmpdir) / "my.lock"
...     lock = FileLock(lock_path)
...     with lock:
...         # Critical section - only one process at a time
...         pass
...     lock.is_locked
False

Async usage:

>>> async def example():
...     import tempfile
...     import pathlib
...     with tempfile.TemporaryDirectory() as tmpdir:
...         lock_path = pathlib.Path(tmpdir) / "my.lock"
...         async with AsyncFileLock(lock_path):
...             # Async critical section
...             pass
...         return "done"
>>> asyncio.run(example())
'done'

Two-file atomic initialization pattern:

>>> def do_expensive_init():
...     pass  # Expensive one-time setup
>>> with tempfile.TemporaryDirectory() as tmpdir:
...     path = pathlib.Path(tmpdir) / "resource"
...     path.mkdir()
...     result = atomic_init(path, do_expensive_init)
...     result  # True if we did init, False if another process did
True

See Also
--------
- filelock: The library that inspired this implementation
- pytest's make_numbered_dir_with_cleanup: Similar atomic init pattern
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import os
import pathlib
import shutil
import time
import typing as t
from types import TracebackType

if t.TYPE_CHECKING:
    from typing_extensions import Self

__all__ = [
    "AcquireReturnProxy",
    "AsyncAcquireReturnProxy",
    "AsyncFileLock",
    "FileLock",
    "FileLockContext",
    "FileLockError",
    "FileLockStale",
    "FileLockTimeout",
    "async_atomic_init",
    "atomic_init",
]


# =============================================================================
# Exceptions
# =============================================================================


class FileLockError(Exception):
    """Base exception for file lock errors.

    All file lock-related exceptions inherit from this class, making it easy
    to catch any lock-related error with a single except clause.

    Examples
    --------
    >>> try:
    ...     raise FileLockError("Lock failed")
    ... except FileLockError as e:
    ...     str(e)
    'Lock failed'
    """


class FileLockTimeout(FileLockError, TimeoutError):
    """Raised when lock acquisition times out.

    This exception inherits from both :class:`FileLockError` and
    :class:`TimeoutError`, allowing it to be caught by either.

    Parameters
    ----------
    lock_file : str
        Path to the lock file that could not be acquired.
    timeout : float
        Timeout value in seconds that was exceeded.

    Examples
    --------
    >>> exc = FileLockTimeout("/tmp/my.lock", 30.0)
    >>> str(exc)
    'Timeout (30.0s) waiting for lock: /tmp/my.lock'
    >>> exc.lock_file
    '/tmp/my.lock'
    >>> exc.timeout
    30.0
    """

    def __init__(self, lock_file: str, timeout: float) -> None:
        #: Path to the lock file
        self.lock_file = lock_file
        #: Timeout in seconds
        self.timeout = timeout
        super().__init__(f"Timeout ({timeout}s) waiting for lock: {lock_file}")

    def __reduce__(self) -> tuple[type[FileLockTimeout], tuple[str, float]]:
        """Support pickling for multiprocessing."""
        return self.__class__, (self.lock_file, self.timeout)


class FileLockStale(FileLockError):
    """Informational exception for stale lock detection.

    This exception is raised when a stale lock is detected but cannot be
    removed. It's primarily informational and can be caught to log warnings.

    Parameters
    ----------
    lock_file : str
        Path to the stale lock file.
    age_seconds : float
        Age of the lock file in seconds.

    Examples
    --------
    >>> exc = FileLockStale("/tmp/my.lock", 3600.0)
    >>> str(exc)
    'Stale lock (3600.0s old): /tmp/my.lock'
    """

    def __init__(self, lock_file: str, age_seconds: float) -> None:
        #: Path to the stale lock file
        self.lock_file = lock_file
        #: Age in seconds
        self.age_seconds = age_seconds
        super().__init__(f"Stale lock ({age_seconds}s old): {lock_file}")

    def __reduce__(self) -> tuple[type[FileLockStale], tuple[str, float]]:
        """Support pickling for multiprocessing."""
        return self.__class__, (self.lock_file, self.age_seconds)


# =============================================================================
# Context Dataclass
# =============================================================================


@dataclasses.dataclass
class FileLockContext:
    """Internal state container for :class:`FileLock`.

    This dataclass holds all the configuration and runtime state for a file
    lock. It's separated from the lock class to allow easier testing and
    to support potential future features like lock serialization.

    Parameters
    ----------
    lock_file : str
        Absolute path to the lock file.
    timeout : float, default=-1.0
        Timeout for lock acquisition. -1 means wait forever.
    poll_interval : float, default=0.05
        Interval between acquisition attempts in seconds.
    stale_timeout : float, default=300.0
        Age in seconds after which a lock is considered stale.
    mode : int, default=0o644
        File permission mode for the lock file.
    lock_file_fd : int or None
        File descriptor when lock is held, None otherwise.
    lock_counter : int, default=0
        Reentrant lock counter (number of times acquired).

    Examples
    --------
    >>> ctx = FileLockContext("/tmp/my.lock")
    >>> ctx.is_locked
    False
    >>> ctx.lock_counter
    0
    """

    lock_file: str
    timeout: float = -1.0
    poll_interval: float = 0.05
    stale_timeout: float = 300.0
    mode: int = 0o644
    lock_file_fd: int | None = dataclasses.field(default=None, repr=False)
    lock_counter: int = 0

    @property
    def is_locked(self) -> bool:
        """Check if the lock is currently held.

        Returns
        -------
        bool
            True if the lock is held, False otherwise.
        """
        return self.lock_file_fd is not None


# =============================================================================
# Return Proxies
# =============================================================================


class AcquireReturnProxy:
    """Context manager proxy returned by :meth:`FileLock.acquire`.

    This proxy allows the acquire/release pattern to be used with context
    managers while still supporting explicit acquire() calls.

    Parameters
    ----------
    lock : FileLock
        The lock instance this proxy wraps.

    Examples
    --------
    >>> import tempfile
    >>> import pathlib
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...     lock = FileLock(lock_path)
    ...     with lock.acquire():  # Returns AcquireReturnProxy
    ...         pass  # Lock is held
    ...     lock.is_locked
    False
    """

    def __init__(self, lock: FileLock) -> None:
        self._lock = lock

    def __enter__(self) -> FileLock:
        """Enter context manager, returning the lock."""
        return self._lock

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, releasing the lock."""
        self._lock.release()


class AsyncAcquireReturnProxy:
    """Async context manager proxy returned by :meth:`AsyncFileLock.acquire`.

    Parameters
    ----------
    lock : AsyncFileLock
        The async lock instance this proxy wraps.

    Examples
    --------
    >>> async def example():
    ...     import tempfile
    ...     import pathlib
    ...     with tempfile.TemporaryDirectory() as tmpdir:
    ...         lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...         lock = AsyncFileLock(lock_path)
    ...         proxy = await lock.acquire()
    ...         async with proxy:
    ...             pass  # Lock is held
    ...         return lock.is_locked
    >>> asyncio.run(example())
    False
    """

    def __init__(self, lock: AsyncFileLock) -> None:
        self._lock = lock

    async def __aenter__(self) -> AsyncFileLock:
        """Enter async context manager, returning the lock."""
        return self._lock

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, releasing the lock."""
        await self._lock.release()


# =============================================================================
# FileLock (Synchronous)
# =============================================================================


class FileLock(contextlib.ContextDecorator):
    """Portable file-based lock using atomic file creation.

    This lock uses the SoftFileLock pattern where lock acquisition is
    achieved through atomic file creation with ``os.O_CREAT | os.O_EXCL``.
    This is portable across platforms and doesn't require OS-level locking.

    The lock is reentrant: the same thread can acquire it multiple times,
    and must release it the same number of times.

    Parameters
    ----------
    lock_file : str or PathLike
        Path to the lock file. Parent directory must exist.
    timeout : float, default=-1.0
        Maximum time to wait for lock acquisition in seconds.
        Use -1 for infinite wait, 0 for non-blocking.
    poll_interval : float, default=0.05
        Time between acquisition attempts in seconds.
    stale_timeout : float, default=300.0
        Locks older than this (in seconds) are considered stale and
        may be removed automatically. Default is 5 minutes.
    mode : int, default=0o644
        File permission mode for the lock file.

    Attributes
    ----------
    lock_file : str
        Path to the lock file.
    is_locked : bool
        Whether the lock is currently held.

    Examples
    --------
    Context manager usage:

    >>> import tempfile
    >>> import pathlib
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...     with FileLock(lock_path):
    ...         # Critical section
    ...         pass

    Explicit acquire/release:

    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...     lock = FileLock(lock_path)
    ...     lock.acquire()  # doctest: +ELLIPSIS
    ...     try:
    ...         pass  # Critical section
    ...     finally:
    ...         lock.release()
    <...AcquireReturnProxy object at ...>

    Non-blocking try-acquire:

    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...     lock = FileLock(lock_path, timeout=0)
    ...     try:
    ...         with lock:
    ...             pass  # Got the lock
    ...     except FileLockTimeout:
    ...         pass  # Lock was held by another process

    See Also
    --------
    AsyncFileLock : Async version of this lock.
    """

    def __init__(
        self,
        lock_file: str | os.PathLike[str],
        timeout: float = -1.0,
        poll_interval: float = 0.05,
        stale_timeout: float = 300.0,
        mode: int = 0o644,
    ) -> None:
        self._context = FileLockContext(
            lock_file=os.fspath(lock_file),
            timeout=timeout,
            poll_interval=poll_interval,
            stale_timeout=stale_timeout,
            mode=mode,
        )

    @property
    def lock_file(self) -> str:
        """Return the path to the lock file."""
        return self._context.lock_file

    @property
    def is_locked(self) -> bool:
        """Check if the lock is currently held by this instance."""
        return self._context.is_locked

    @property
    def lock_counter(self) -> int:
        """Return the number of times this lock has been acquired."""
        return self._context.lock_counter

    def _acquire(self) -> None:
        """Low-level lock acquisition using os.O_CREAT | os.O_EXCL.

        Raises
        ------
        FileExistsError
            If the lock file already exists (lock is held).
        """
        fd = os.open(
            self._context.lock_file,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            self._context.mode,
        )
        self._context.lock_file_fd = fd
        # Write PID for debugging stale locks
        os.write(fd, str(os.getpid()).encode())

    def _release(self) -> None:
        """Low-level lock release: close fd and remove file."""
        fd = self._context.lock_file_fd
        if fd is not None:
            os.close(fd)
            self._context.lock_file_fd = None
            pathlib.Path(self._context.lock_file).unlink(missing_ok=True)

    def _is_stale(self) -> bool:
        """Check if the existing lock file is stale.

        Returns
        -------
        bool
            True if the lock is stale (older than stale_timeout).
        """
        try:
            mtime = pathlib.Path(self._context.lock_file).stat().st_mtime
            age = time.time() - mtime
        except OSError:
            return True
        else:
            return age > self._context.stale_timeout

    def _remove_stale_lock(self) -> bool:
        """Try to remove a stale lock file.

        Returns
        -------
        bool
            True if the stale lock was removed, False otherwise.
        """
        if self._is_stale():
            try:
                pathlib.Path(self._context.lock_file).unlink()
            except OSError:
                pass
            else:
                return True
        return False

    def acquire(
        self,
        timeout: float | None = None,
        poll_interval: float | None = None,
        *,
        blocking: bool = True,
    ) -> AcquireReturnProxy:
        """Acquire the file lock.

        Parameters
        ----------
        timeout : float, optional
            Override the default timeout for this acquisition.
        poll_interval : float, optional
            Override the default poll interval for this acquisition.
        blocking : bool, default=True
            If False, equivalent to timeout=0.

        Returns
        -------
        AcquireReturnProxy
            A context manager that releases the lock on exit.

        Raises
        ------
        FileLockTimeout
            If the lock cannot be acquired within the timeout.

        Examples
        --------
        >>> import tempfile
        >>> import pathlib
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
        ...     lock = FileLock(lock_path)
        ...     with lock.acquire(timeout=5.0):
        ...         pass  # Lock held
        """
        # Handle non-blocking mode
        if not blocking:
            timeout = 0

        # Use instance defaults if not overridden
        if timeout is None:
            timeout = self._context.timeout
        if poll_interval is None:
            poll_interval = self._context.poll_interval

        # Reentrant: if already locked, just increment counter
        if self._context.lock_file_fd is not None:
            self._context.lock_counter += 1
            return AcquireReturnProxy(self)

        start_time = time.perf_counter()

        while True:
            try:
                self._acquire()
                self._context.lock_counter = 1
                return AcquireReturnProxy(self)
            except FileExistsError:
                pass

            # Check for stale lock
            if self._remove_stale_lock():
                continue  # Retry immediately after removing stale lock

            # Check timeout
            elapsed = time.perf_counter() - start_time
            if timeout >= 0 and elapsed >= timeout:
                raise FileLockTimeout(self._context.lock_file, timeout)

            # Wait before retrying
            time.sleep(poll_interval)

    def release(self, force: bool = False) -> None:
        """Release the file lock.

        Parameters
        ----------
        force : bool, default=False
            If True, release the lock even if counter > 1.

        Notes
        -----
        For reentrant locks, each acquire() must be matched by a release().
        Use force=True to release regardless of the counter.

        Examples
        --------
        >>> import tempfile
        >>> import pathlib
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     lock_path = pathlib.Path(tmpdir) / "my.lock"
        ...     lock = FileLock(lock_path)
        ...     lock.acquire()  # doctest: +ELLIPSIS
        ...     lock.lock_counter
        ...     lock.release()
        ...     lock.is_locked
        <...AcquireReturnProxy object at ...>
        1
        False
        """
        if self._context.lock_file_fd is None:
            return

        if force:
            self._context.lock_counter = 0
            self._release()
        else:
            self._context.lock_counter -= 1
            if self._context.lock_counter <= 0:
                self._context.lock_counter = 0
                self._release()

    def __enter__(self) -> Self:
        """Enter context manager, acquiring the lock."""
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, releasing the lock."""
        self.release()

    def __repr__(self) -> str:
        """Return a string representation of the lock."""
        state = "locked" if self.is_locked else "unlocked"
        return f"<FileLock({self.lock_file!r}, {state})>"


# =============================================================================
# AsyncFileLock
# =============================================================================


class AsyncFileLock:
    """Async file lock wrapping :class:`FileLock` with async polling.

    This class provides an async interface to the underlying :class:`FileLock`,
    using ``asyncio.sleep`` instead of blocking ``time.sleep`` during
    acquisition polling. This allows other coroutines to run while waiting
    for the lock.

    Parameters
    ----------
    lock_file : str or PathLike
        Path to the lock file. Parent directory must exist.
    timeout : float, default=-1.0
        Maximum time to wait for lock acquisition in seconds.
        Use -1 for infinite wait, 0 for non-blocking.
    poll_interval : float, default=0.05
        Time between acquisition attempts in seconds.
    stale_timeout : float, default=300.0
        Locks older than this (in seconds) are considered stale.
    mode : int, default=0o644
        File permission mode for the lock file.

    Examples
    --------
    Async context manager:

    >>> async def example():
    ...     import tempfile
    ...     import pathlib
    ...     with tempfile.TemporaryDirectory() as tmpdir:
    ...         lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...         async with AsyncFileLock(lock_path) as lock:
    ...             return lock.is_locked
    >>> asyncio.run(example())
    True

    Explicit acquire/release:

    >>> async def example2():
    ...     import tempfile
    ...     import pathlib
    ...     with tempfile.TemporaryDirectory() as tmpdir:
    ...         lock_path = pathlib.Path(tmpdir) / "my.lock"
    ...         lock = AsyncFileLock(lock_path)
    ...         await lock.acquire()
    ...         try:
    ...             return lock.is_locked
    ...         finally:
    ...             await lock.release()
    >>> asyncio.run(example2())
    True

    See Also
    --------
    FileLock : Synchronous version.
    """

    def __init__(
        self,
        lock_file: str | os.PathLike[str],
        timeout: float = -1.0,
        poll_interval: float = 0.05,
        stale_timeout: float = 300.0,
        mode: int = 0o644,
    ) -> None:
        self._sync_lock = FileLock(
            lock_file=lock_file,
            timeout=timeout,
            poll_interval=poll_interval,
            stale_timeout=stale_timeout,
            mode=mode,
        )

    @property
    def lock_file(self) -> str:
        """Return the path to the lock file."""
        return self._sync_lock.lock_file

    @property
    def is_locked(self) -> bool:
        """Check if the lock is currently held by this instance."""
        return self._sync_lock.is_locked

    @property
    def lock_counter(self) -> int:
        """Return the number of times this lock has been acquired."""
        return self._sync_lock.lock_counter

    async def acquire(
        self,
        timeout: float | None = None,
        poll_interval: float | None = None,
        *,
        blocking: bool = True,
    ) -> AsyncAcquireReturnProxy:
        """Acquire the file lock asynchronously.

        Parameters
        ----------
        timeout : float, optional
            Override the default timeout for this acquisition.
        poll_interval : float, optional
            Override the default poll interval for this acquisition.
        blocking : bool, default=True
            If False, equivalent to timeout=0.

        Returns
        -------
        AsyncAcquireReturnProxy
            An async context manager that releases the lock on exit.

        Raises
        ------
        FileLockTimeout
            If the lock cannot be acquired within the timeout.
        """
        if not blocking:
            timeout = 0

        ctx = self._sync_lock._context
        if timeout is None:
            timeout = ctx.timeout
        if poll_interval is None:
            poll_interval = ctx.poll_interval

        # Reentrant
        if ctx.lock_file_fd is not None:
            ctx.lock_counter += 1
            return AsyncAcquireReturnProxy(self)

        start_time = time.perf_counter()

        while True:
            try:
                self._sync_lock._acquire()
                ctx.lock_counter = 1
                return AsyncAcquireReturnProxy(self)
            except FileExistsError:
                pass

            # Check for stale lock
            if self._sync_lock._remove_stale_lock():
                continue

            # Check timeout
            elapsed = time.perf_counter() - start_time
            if timeout >= 0 and elapsed >= timeout:
                raise FileLockTimeout(ctx.lock_file, timeout)

            # Async sleep to allow other coroutines to run
            await asyncio.sleep(poll_interval)

    async def release(self, force: bool = False) -> None:
        """Release the file lock.

        Parameters
        ----------
        force : bool, default=False
            If True, release the lock even if counter > 1.
        """
        self._sync_lock.release(force=force)

    async def __aenter__(self) -> Self:
        """Enter async context manager, acquiring the lock."""
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, releasing the lock."""
        await self.release()

    def __repr__(self) -> str:
        """Return a string representation of the lock."""
        state = "locked" if self.is_locked else "unlocked"
        return f"<AsyncFileLock({self.lock_file!r}, {state})>"


# =============================================================================
# Convenience Functions
# =============================================================================


def atomic_init(
    path: str | os.PathLike[str],
    init_fn: t.Callable[[], None],
    marker_name: str = ".initialized",
    timeout: float = 60.0,
    poll_interval: float = 0.05,
    stale_timeout: float = 300.0,
) -> bool:
    """Atomically initialize a resource using the two-file pattern.

    This function coordinates one-time initialization across multiple processes
    using a combination of a lock file and a marker file:

    - **Lock file**: Temporary file held during initialization, deleted after.
    - **Marker file**: Permanent file indicating initialization is complete.

    This pattern is useful for expensive one-time setup like cloning
    repositories, building caches, or creating database schemas.

    Parameters
    ----------
    path : str or PathLike
        Directory where the marker file will be created.
    init_fn : callable
        Function to call for initialization. Called only if not already
        initialized. Must be idempotent in case of partial failure.
    marker_name : str, default=".initialized"
        Name of the marker file within ``path``.
    timeout : float, default=60.0
        Maximum time to wait for another process to finish initialization.
    poll_interval : float, default=0.05
        Time between lock acquisition attempts.
    stale_timeout : float, default=300.0
        Time after which an orphaned lock is considered stale.

    Returns
    -------
    bool
        True if this call performed initialization, False if another
        process did or had already done it.

    Raises
    ------
    FileLockTimeout
        If initialization by another process doesn't complete within timeout.

    Examples
    --------
    >>> import tempfile
    >>> import pathlib
    >>> def expensive_init():
    ...     pass  # One-time setup
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     resource_path = pathlib.Path(tmpdir) / "myresource"
    ...     resource_path.mkdir()
    ...     # First call does initialization
    ...     first = atomic_init(resource_path, expensive_init)
    ...     # Second call sees marker and skips
    ...     second = atomic_init(resource_path, expensive_init)
    ...     first, second
    (True, False)

    With cleanup on partial failure:

    >>> def init_with_cleanup():
    ...     import pathlib
    ...     import tempfile
    ...     with tempfile.TemporaryDirectory() as tmpdir:
    ...         path = pathlib.Path(tmpdir) / "repo"
    ...         path.mkdir()
    ...         def do_init():
    ...             (path / "data.txt").write_text("hello")
    ...         atomic_init(path, do_init)
    ...         return (path / "data.txt").exists()
    >>> init_with_cleanup()
    True

    See Also
    --------
    async_atomic_init : Async version of this function.
    """
    path = pathlib.Path(path)
    marker = path / marker_name
    lock_path = path.parent / f".{path.name}.lock"

    # Fast path: already initialized
    if marker.exists():
        return False

    lock = FileLock(
        lock_path,
        timeout=timeout,
        poll_interval=poll_interval,
        stale_timeout=stale_timeout,
    )

    with lock:
        # Double-check after acquiring lock
        if marker.exists():
            return False

        # Clean partial state if needed
        if path.exists() and not marker.exists():
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)

        # Perform initialization
        init_fn()

        # Mark as complete
        marker.touch()
        return True


async def async_atomic_init(
    path: str | os.PathLike[str],
    init_fn: t.Callable[[], None] | t.Callable[[], t.Coroutine[t.Any, t.Any, None]],
    marker_name: str = ".initialized",
    timeout: float = 60.0,
    poll_interval: float = 0.05,
    stale_timeout: float = 300.0,
) -> bool:
    """Atomically initialize a resource asynchronously.

    Async version of :func:`atomic_init`. Supports both sync and async
    ``init_fn`` callables.

    Parameters
    ----------
    path : str or PathLike
        Directory where the marker file will be created.
    init_fn : callable
        Sync or async function to call for initialization.
    marker_name : str, default=".initialized"
        Name of the marker file within ``path``.
    timeout : float, default=60.0
        Maximum time to wait for another process to finish initialization.
    poll_interval : float, default=0.05
        Time between lock acquisition attempts.
    stale_timeout : float, default=300.0
        Time after which an orphaned lock is considered stale.

    Returns
    -------
    bool
        True if this call performed initialization, False otherwise.

    Raises
    ------
    FileLockTimeout
        If initialization by another process doesn't complete within timeout.

    Examples
    --------
    >>> async def example():
    ...     import tempfile
    ...     import pathlib
    ...     async def async_init():
    ...         await asyncio.sleep(0)  # Simulate async work
    ...     with tempfile.TemporaryDirectory() as tmpdir:
    ...         path = pathlib.Path(tmpdir) / "resource"
    ...         path.mkdir()
    ...         result = await async_atomic_init(path, async_init)
    ...         return result
    >>> asyncio.run(example())
    True

    See Also
    --------
    atomic_init : Synchronous version.
    """
    import inspect

    path = pathlib.Path(path)
    marker = path / marker_name
    lock_path = path.parent / f".{path.name}.lock"

    # Fast path
    if marker.exists():
        return False

    lock = AsyncFileLock(
        lock_path,
        timeout=timeout,
        poll_interval=poll_interval,
        stale_timeout=stale_timeout,
    )

    async with lock:
        if marker.exists():
            return False

        if path.exists() and not marker.exists():
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)

        # Handle both sync and async init functions
        result = init_fn()
        if inspect.iscoroutine(result):
            await result

        marker.touch()
        return True
