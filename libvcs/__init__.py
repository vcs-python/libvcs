"""Repo package for libvcs."""
import logging

from .cmd.core import CmdLoggingAdapter
from .projects.base import BaseRepo
from .projects.git import GitRepo
from .projects.hg import MercurialRepo
from .projects.svn import SubversionRepo

__all__ = [
    "GitRepo",
    "MercurialRepo",
    "SubversionRepo",
    "BaseRepo",
    "CmdLoggingAdapter",
]

logger = logging.getLogger(__name__)
