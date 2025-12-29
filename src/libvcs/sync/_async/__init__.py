"""Async repository synchronization classes.

This module provides async equivalents of the sync classes
in :mod:`libvcs.sync`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

from libvcs.sync._async.git import AsyncGitSync

__all__ = [
    "AsyncGitSync",
]
