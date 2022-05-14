from os import PathLike
from typing import Union

# via github.com/python/typeshed/blob/5df8de7/stdlib/_typeshed/__init__.pyi#L115-L118

#: :class:`os.PathLike` or :func:`str`
StrPath = Union[str, PathLike[str]]  # stable
#: :class:`os.PathLike`, :func:`str` or :term:`bytes-like object`
StrOrBytesPath = Union[str, bytes, PathLike[str], PathLike[bytes]]  # stable
