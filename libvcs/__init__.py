# -*- coding: utf-8 -*-
"""Repo package for libvcs.

libvcs
~~~~~~

"""
from __future__ import absolute_import, print_function, unicode_literals

import logging

from .base import RepoLoggingAdapter, VCSRepo
from .git import Git
from .hg import Mercurial
from .svn import Subversion

__all__ = ['Git', 'Mercurial', 'Subversion', 'VCSRepo', 'RepoLoggingAdapter']

logger = logging.getLogger(__name__)
