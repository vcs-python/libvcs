"""Project package for libvcs."""
import logging

from .cmd.core import CmdLoggingAdapter
from .projects.base import BaseProject
from .projects.git import GitProject
from .projects.hg import MercurialProject
from .projects.svn import SubversionProject

__all__ = [
    "GitProject",
    "MercurialProject",
    "SubversionProject",
    "BaseProject",
    "CmdLoggingAdapter",
]

logger = logging.getLogger(__name__)
