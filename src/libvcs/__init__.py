"""Project package for libvcs."""

from __future__ import annotations

import logging

from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseSync, SyncError, SyncResult
from .sync.git import GitSync
from .sync.hg import HgSync
from .sync.svn import SvnSync

from .__about__ import __version__

__all__ = [
    "__version__",
    "BaseSync",
    "CmdLoggingAdapter",
    "GitSync",
    "HgSync",
    "SvnSync",
    "SyncError",
    "SyncResult",
]

logger = logging.getLogger(__name__)
