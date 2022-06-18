"""Internal :term:`type annotations <annotation>`

Notes
-----

:class:`StrPath` and :class:`StrOrBytesPath` is based on `typeshed's`_.

.. _typeshed's: https://github.com/python/typeshed/blob/5df8de7/stdlib/_typeshed/__init__.pyi#L115-L118
"""  # NOQA E501
from os import PathLike
from typing import Literal, Union

from typing_extensions import TypeAlias

StrPath: TypeAlias = Union[str, PathLike[str]]  # stable
""":class:`os.PathLike` or :class:`str`"""

StrOrBytesPath: TypeAlias = Union[str, bytes, PathLike[str], PathLike[bytes]]  # stable
""":class:`os.PathLike`, :class:`str` or :term:`bytes-like object`"""


VCSLiteral = Literal["git", "svn", "hg"]
"""UNSTABLE: Literal of built-in VCS aliases"""
