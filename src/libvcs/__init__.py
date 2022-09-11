"""Project package for libvcs."""
import logging

from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseSync
from .sync.git import GitSync
from .sync.hg import HgSync
from .sync.svn import SvnSync

__all__ = [
    "GitSync",
    "HgSync",
    "SvnSync",
    "BaseSync",
    "CmdLoggingAdapter",
]

logger = logging.getLogger(__name__)
