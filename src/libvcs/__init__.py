"""Project package for libvcs."""

from __future__ import annotations

import logging

from .__about__ import __version__
from ._internal.run import CmdLoggingAdapter
from .sync.base import (
    BaseSync,
    RecoveryToken,
    SyncConflict,
    SyncError,
    SyncPolicy,
    SyncResult,
    SyncTarget,
    WorkingCopyPosition,
)
from .sync.git import GitOptions, GitSync
from .sync.hg import HgOptions, HgSync
from .sync.svn import SvnOptions, SvnSync

__all__ = [
    "BaseSync",
    "CmdLoggingAdapter",
    "GitOptions",
    "GitSync",
    "HgOptions",
    "HgSync",
    "RecoveryToken",
    "SvnOptions",
    "SvnSync",
    "SyncConflict",
    "SyncError",
    "SyncPolicy",
    "SyncResult",
    "SyncTarget",
    "WorkingCopyPosition",
    "__version__",
]

logger = logging.getLogger(__name__)
