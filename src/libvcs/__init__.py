"""Project package for libvcs."""

from __future__ import annotations

import logging

from .__about__ import __version__
from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseSync, SyncError, SyncResult, WorkingCopyPosition
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
    "SvnOptions",
    "SvnSync",
    "SyncError",
    "SyncResult",
    "WorkingCopyPosition",
    "__version__",
]

logger = logging.getLogger(__name__)
