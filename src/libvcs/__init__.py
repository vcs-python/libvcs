"""Project package for libvcs."""
import logging

from ._internal.run import CmdLoggingAdapter
from .sync.base import BaseProject
from .sync.git import GitProject
from .sync.hg import MercurialProject
from .sync.svn import SubversionProject

__all__ = [
    "GitProject",
    "MercurialProject",
    "SubversionProject",
    "BaseProject",
    "CmdLoggingAdapter",
]

logger = logging.getLogger(__name__)
