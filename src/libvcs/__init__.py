"""Project package for libvcs."""

from __future__ import annotations

import logging

from .__about__ import __version__
from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseSync, SyncError, SyncResult
from .sync.git import GitSync
from .sync.hg import HgSync
from .sync.svn import SvnSync

__all__ = [
    "BaseSync",
    "CmdLoggingAdapter",
    "GitSync",
    "HgSync",
    "SvnSync",
    "SyncError",
    "SyncResult",
    "__version__",
]

logger = logging.getLogger(__name__)
