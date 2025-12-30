# FileLock - `libvcs._internal.file_lock`

Typed, asyncio-friendly file locking based on [filelock](https://github.com/tox-dev/filelock) patterns.

## Overview

This module provides portable file-based locking using the **SoftFileLock** pattern
(`os.O_CREAT | os.O_EXCL`) for atomic lock acquisition. It supports both synchronous
and asynchronous contexts.

### Key Features

- **Atomic acquisition**: Uses `os.O_CREAT | os.O_EXCL` for race-free lock creation
- **Reentrant locking**: Same thread can acquire lock multiple times
- **Stale lock detection**: Auto-removes locks older than configurable timeout (default 5min)
- **Async support**: {class}`~libvcs._internal.file_lock.AsyncFileLock` with `asyncio.sleep` polling
- **Two-file pattern**: Lock file (temporary) + marker file (permanent)
- **PID tracking**: Writes PID to lock file for debugging

## Quick Start

### Synchronous Usage

```python
from libvcs._internal.file_lock import FileLock

# Context manager (recommended)
with FileLock("/tmp/my.lock"):
    # Critical section - only one process at a time
    pass

# Explicit acquire/release
lock = FileLock("/tmp/my.lock")
lock.acquire()
try:
    # Critical section
    pass
finally:
    lock.release()
```

### Asynchronous Usage

```python
import asyncio
from libvcs._internal.file_lock import AsyncFileLock

async def main():
    async with AsyncFileLock("/tmp/my.lock"):
        # Async critical section
        pass

asyncio.run(main())
```

### Atomic Initialization

The {func}`~libvcs._internal.file_lock.atomic_init` function implements the **two-file pattern**
for coordinating one-time initialization across multiple processes:

```python
from libvcs._internal.file_lock import atomic_init

def expensive_init():
    # One-time setup (e.g., clone repo, build cache)
    pass

# First call does initialization, subsequent calls skip
did_init = atomic_init("/path/to/resource", expensive_init)
```

## API Reference

```{eval-rst}
.. automodule:: libvcs._internal.file_lock
   :members:
   :undoc-members:
   :show-inheritance:
```
