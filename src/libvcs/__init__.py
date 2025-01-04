"""Project package for libvcs."""

from __future__ import annotations

import logging

from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseSync
from .sync.git import GitSync
from .sync.hg import HgSync
from .sync.svn import SvnSync

__all__ = [
    "BaseSync",
    "CmdLoggingAdapter",
    "GitSync",
    "HgSync",
    "SvnSync",
]

logger = logging.getLogger(__name__)
