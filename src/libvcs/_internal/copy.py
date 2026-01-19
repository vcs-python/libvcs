"""Copy utilities with reflink (copy-on-write) support.

This module provides optimized directory copy operations that leverage
filesystem-level copy-on-write (CoW) when available, with automatic
fallback to standard copying on unsupported filesystems.

On Btrfs, XFS, and APFS filesystems, reflink copies are significantly faster
as they only copy metadata - the actual data blocks are shared until modified.
On ext4 and other filesystems, `cp --reflink=auto` silently falls back to
regular copying with no performance penalty.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import typing as t


def copytree_reflink(
    src: pathlib.Path,
    dst: pathlib.Path,
    ignore: t.Callable[..., t.Any] | None = None,
) -> pathlib.Path:
    """Copy directory tree using reflink (CoW) if available, fallback to copytree.

    On Btrfs/XFS/APFS, this is significantly faster as it only copies metadata.
    On ext4 and other filesystems, `cp --reflink=auto` silently falls back to
    regular copy.

    Parameters
    ----------
    src : pathlib.Path
        Source directory to copy.
    dst : pathlib.Path
        Destination directory (must not exist).
    ignore : callable, optional
        Passed to shutil.copytree for fallback. For cp, patterns are applied
        after copy by deleting ignored files.

    Returns
    -------
    pathlib.Path
        The destination path.

    Examples
    --------
    >>> import pathlib
    >>> src = tmp_path / "source"
    >>> src.mkdir()
    >>> (src / "file.txt").write_text("hello")
    5
    >>> dst = tmp_path / "dest"
    >>> result = copytree_reflink(src, dst)
    >>> (result / "file.txt").read_text()
    'hello'

    With ignore patterns:

    >>> import shutil
    >>> src2 = tmp_path / "source2"
    >>> src2.mkdir()
    >>> (src2 / "keep.txt").write_text("keep")
    4
    >>> (src2 / "skip.pyc").write_text("skip")
    4
    >>> dst2 = tmp_path / "dest2"
    >>> result2 = copytree_reflink(src2, dst2, ignore=shutil.ignore_patterns("*.pyc"))
    >>> (result2 / "keep.txt").exists()
    True
    >>> (result2 / "skip.pyc").exists()
    False
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Try cp --reflink=auto (Linux) - silent fallback on unsupported FS
        subprocess.run(
            ["cp", "-a", "--reflink=auto", str(src), str(dst)],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # Fallback to shutil.copytree (Windows, cp not found, etc.)
        return pathlib.Path(shutil.copytree(src, dst, ignore=ignore))
    else:
        # cp succeeded - apply ignore patterns if needed
        if ignore is not None:
            _apply_ignore_patterns(dst, ignore)
        return dst


def _apply_ignore_patterns(
    dst: pathlib.Path,
    ignore: t.Callable[[str, list[str]], t.Iterable[str]],
) -> None:
    """Remove files matching ignore patterns after cp --reflink copy.

    This function walks the destination directory and removes any files or
    directories that match the ignore patterns. This is necessary because
    `cp` doesn't support ignore patterns directly.

    Parameters
    ----------
    dst : pathlib.Path
        Destination directory to clean up.
    ignore : callable
        A callable that takes (directory, names) and returns names to ignore.
        Compatible with shutil.ignore_patterns().
    """
    for root, dirs, files in os.walk(dst, topdown=True):
        root_path = pathlib.Path(root)
        ignored = set(ignore(root, dirs + files))
        for name in ignored:
            target = root_path / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        # Modify dirs in-place to skip ignored directories during walk
        dirs[:] = [d for d in dirs if d not in ignored]
