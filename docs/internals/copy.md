(copy)=

# Copy Utilities

```{module} libvcs._internal.copy
```

Copy utilities with reflink (copy-on-write) support for optimized directory operations.

## Overview

This module provides `copytree_reflink()`, an optimized directory copy function that
leverages filesystem-level copy-on-write (CoW) when available, with automatic fallback
to standard `shutil.copytree()` on unsupported filesystems.

## Why Reflinks?

Traditional file copying reads source bytes and writes them to the destination. On
modern copy-on-write filesystems like **Btrfs**, **XFS**, and **APFS**, reflinks
provide a more efficient alternative:

| Operation | Traditional Copy | Reflink Copy |
|-----------|------------------|--------------|
| Bytes transferred | All file data | Metadata only |
| Time complexity | O(file size) | O(1) |
| Disk usage | 2x original | ~0 (shared blocks) |
| On modification | Original unchanged | CoW creates new blocks |

### Filesystem Support

| Filesystem | Reflink Support | Notes |
|------------|-----------------|-------|
| Btrfs | ✅ Native | Full CoW support |
| XFS | ✅ Native | Requires reflink=1 mount option |
| APFS | ✅ Native | macOS 10.13+ |
| ext4 | ❌ Fallback | Falls back to byte copy |
| NTFS | ❌ Fallback | Windows uses shutil.copytree |

## Usage

```python
from libvcs._internal.copy import copytree_reflink
import pathlib

src = pathlib.Path("/path/to/source")
dst = pathlib.Path("/path/to/destination")

# Simple copy
copytree_reflink(src, dst)

# With ignore patterns
import shutil
copytree_reflink(
    src,
    dst,
    ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
)
```

## API Reference

```{eval-rst}
.. autofunction:: libvcs._internal.copy.copytree_reflink
```

## Implementation Details

### Strategy

The function uses a **reflink-first + fallback** strategy:

1. **Try `cp --reflink=auto`** - On Linux, this command attempts a reflink copy
   and silently falls back to regular copy if the filesystem doesn't support it
2. **Fallback to `shutil.copytree()`** - If `cp` fails (not found, permission issues,
   or Windows), use Python's standard library

### Ignore Patterns

When using ignore patterns with `cp --reflink=auto`, the approach differs from
`shutil.copytree()`:

- **shutil.copytree**: Applies patterns during copy (never copies ignored files)
- **cp --reflink**: Copies everything, then deletes ignored files

This difference is acceptable because:
- The overhead of post-copy deletion is minimal for typical ignore patterns
- The performance gain from reflinks far outweighs this overhead on CoW filesystems

## Use in pytest Fixtures

This module is used by the `*_repo` fixtures in `libvcs.pytest_plugin` to create
isolated test workspaces from cached master copies:

```python
# From pytest_plugin.py
from libvcs._internal.copy import copytree_reflink

@pytest.fixture
def git_repo(...):
    # ...
    copytree_reflink(
        master_copy,
        new_checkout_path,
        ignore=shutil.ignore_patterns(".libvcs_master_initialized"),
    )
    # ...
```

### Benefits for Test Fixtures

1. **Faster on CoW filesystems** - Users on Btrfs/XFS see 10-100x speedup
2. **No regression elsewhere** - ext4/Windows users see no performance change
3. **Safe for writable workspaces** - Tests can modify files; master stays unchanged
4. **Future-proof** - As more systems adopt CoW filesystems, benefits increase
