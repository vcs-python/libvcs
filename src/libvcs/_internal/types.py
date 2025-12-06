"""Internal type annotations.

Notes
-----
:class:`StrPath` and :class:`StrOrBytesPath` is based on `typeshed's`_.

.. _typeshed's: https://github.com/python/typeshed/blob/5df8de7/stdlib/_typeshed/__init__.pyi#L115-L118
"""  # E501

from __future__ import annotations

import typing as t
from os import PathLike

StrPath: t.TypeAlias = str | PathLike[str]  # stable
""":class:`os.PathLike` or :class:`str`"""

StrOrBytesPath: t.TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]
""":class:`os.PathLike`, :class:`str` or bytes-like object"""


VCSLiteral = t.Literal["git", "svn", "hg"]
"""UNSTABLE: Literal of built-in VCS aliases"""
