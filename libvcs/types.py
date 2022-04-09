from os import PathLike

# See also, if this type is baked in in typing in the future
# - https://stackoverflow.com/q/53418046/1396928
# - https://github.com/python/typeshed/issues/5912
# PathLike = TypeVar("PathLike", str, pathlib.Path)
# OptionalPathLike = TypeVar("OptionalPathLike", str, pathlib.Path, None)


StrOrBytesPath = str | bytes | PathLike[str] | PathLike[bytes]  # stable
StrOrPath = str | PathLike[str]  # stable
