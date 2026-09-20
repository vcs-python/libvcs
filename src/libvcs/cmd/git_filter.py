"""Typed Git object filters for partial clone and fetch operations."""

# Filter config exposes one predictable ValueError surface for type and value errors.
# ruff: noqa: TRY004

from __future__ import annotations

import dataclasses
import re
import typing as t
from collections.abc import Mapping, Sequence

_MAX_UINT = 2**64 - 1
_MAX_NESTING = 32
_GIT_ULONG_RE = re.compile(
    r"[\t\v\f ]*\+?"
    r"(?P<number>0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)"
    r"(?P<unit>[kKmMgG]?)\Z"
)
_LIMIT_MULTIPLIERS = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}
_OBJECT_TYPES = ("blob", "tree", "commit", "tag")
_RESERVED_NON_WHITESPACE = frozenset("~`!@#$^&*()[]{}\\;'\",<>?")


def _validate_uint(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be an integer"
        raise ValueError(msg)
    if not 0 <= value <= _MAX_UINT:
        msg = f"{field} must be between 0 and {_MAX_UINT}"
        raise ValueError(msg)
    return value


def _parse_git_ulong(value: str, *, field: str) -> int:
    match = _GIT_ULONG_RE.fullmatch(value)
    if match is None:
        msg = f"{field} must use Git unsigned-long syntax"
        raise ValueError(msg)
    raw_number = match.group("number")
    if raw_number.lower().startswith("0x"):
        base = 16
    elif len(raw_number) > 1 and raw_number.startswith("0"):
        base = 8
    else:
        base = 10
    number = int(raw_number, base)
    multiplier = _LIMIT_MULTIPLIERS[match.group("unit").lower()]
    if number > _MAX_UINT // multiplier:
        msg = f"{field} must not exceed {_MAX_UINT}"
        raise ValueError(msg)
    return number * multiplier


def _validate_limit(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        msg = "limit must be an integer or Git unsigned-long string"
        raise ValueError(msg)
    if isinstance(value, int):
        _validate_uint(value, field="limit")
        return
    _parse_git_ulong(value, field="limit")


def _validate_oid(value: object) -> None:
    if not isinstance(value, str) or not value:
        msg = "oid must be a nonempty string"
        raise ValueError(msg)
    if any(character in value for character in ("\x00", "\r", "\n")):
        msg = "oid must not contain NUL or newlines"
        raise ValueError(msg)


@dataclasses.dataclass(frozen=True)
class BlobNone:
    """Omit all blobs until Git needs them."""

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return "blob:none"


@dataclasses.dataclass(frozen=True)
class BlobLimit:
    """Omit blobs at or above a byte limit."""

    limit: int | str
    """Byte count as an integer or Git unsigned-long string."""

    def __post_init__(self) -> None:
        """Validate the limit against Git's unsigned-long grammar."""
        _validate_limit(self.limit)
        if isinstance(self.limit, str) and re.fullmatch(
            r"(?:0|[1-9][0-9]*)", self.limit
        ):
            object.__setattr__(self, "limit", int(self.limit))

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return f"blob:limit={self.limit}"


@dataclasses.dataclass(frozen=True)
class TreeDepth:
    """Omit trees and blobs at or beyond a traversal depth."""

    depth: int
    """Maximum unsigned 64-bit traversal depth."""

    def __post_init__(self) -> None:
        """Validate the traversal depth."""
        _validate_uint(self.depth, field="depth")

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return f"tree:{self.depth}"


@dataclasses.dataclass(frozen=True)
class ObjectType:
    """Include one Git object type."""

    type: t.Literal["blob", "tree", "commit", "tag"]
    """Git object type to include."""

    def __post_init__(self) -> None:
        """Validate the object type."""
        if self.type not in _OBJECT_TYPES:
            msg = "type must be blob, tree, commit, or tag"
            raise ValueError(msg)

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return f"object:type={self.type}"


@dataclasses.dataclass(frozen=True)
class SparseOid:
    """Read sparse-checkout patterns from a Git object."""

    oid: str
    """Object name containing sparse-checkout patterns."""

    def __post_init__(self) -> None:
        """Validate the object name."""
        _validate_oid(self.oid)

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return f"sparse:oid={self.oid}"


@dataclasses.dataclass(frozen=True)
class Auto:
    """Let Git choose the filter from server recommendations."""

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return "auto"


@dataclasses.dataclass(frozen=True)
class Combine:
    """Apply each child filter as one Git combine filter."""

    filters: tuple[GitFilter, ...]
    """Nonempty tuple of child filters."""

    def __post_init__(self) -> None:
        """Validate the child filters."""
        if not isinstance(self.filters, tuple) or not self.filters:
            msg = "filters must be a nonempty tuple"
            raise ValueError(msg)
        for index, child in enumerate(self.filters):
            if not isinstance(child, _FILTER_TYPES):
                msg = f"filters[{index}] must be a Git filter"
                raise ValueError(msg)
            if isinstance(child, Auto):
                msg = f"filters[{index}]: auto cannot be combined"
                raise ValueError(msg)
        stack = [(child, 1) for child in self.filters]
        while stack:
            child, depth = stack.pop()
            if depth > _MAX_NESTING:
                msg = f"filter nesting exceeds {_MAX_NESTING} levels"
                raise ValueError(msg)
            if isinstance(child, Combine):
                stack.extend((nested, depth + 1) for nested in child.filters)

    def to_spec(self) -> str:
        """Return Git's canonical filter specification."""
        return "combine:" + "+".join(
            _encode_subfilter(child.to_spec()) for child in self.filters
        )


GitFilter: t.TypeAlias = (
    BlobNone | BlobLimit | TreeDepth | ObjectType | SparseOid | Auto | Combine
)
"""A validated Git partial-clone filter."""

GitFilterInput: t.TypeAlias = GitFilter | str | Mapping[str, object] | Sequence[object]
"""A filter model, spec, kind-tagged mapping, or nonempty sequence."""

_FILTER_TYPES = (BlobNone, BlobLimit, TreeDepth, ObjectType, SparseOid, Auto, Combine)


def _encode_subfilter(spec: str) -> str:
    encoded: list[str] = []
    for byte in spec.encode():
        character = chr(byte)
        if (
            32 < byte < 127
            and character not in _RESERVED_NON_WHITESPACE
            and character not in "%+"
        ):
            encoded.append(character)
        else:
            encoded.append(f"%{byte:02X}")
    return "".join(encoded)


def _decode_subfilter(spec: str) -> str:
    decoded = bytearray()
    index = 0
    while index < len(spec):
        character = spec[index]
        if character == "%":
            escape = spec[index + 1 : index + 3]
            if len(escape) != 2 or not all(
                c in "0123456789abcdefABCDEF" for c in escape
            ):
                msg = "malformed percent escape in combine filter"
                raise ValueError(msg)
            decoded.append(int(escape, 16))
            index += 3
            continue
        if ord(character) <= 32 or character in _RESERVED_NON_WHITESPACE:
            msg = f"reserved character {character!r} in combine filter"
            raise ValueError(msg)
        decoded.extend(character.encode())
        index += 1
    if 0 in decoded:
        msg = "NUL is not allowed in a filter"
        raise ValueError(msg)
    try:
        return decoded.decode()
    except UnicodeDecodeError as error:
        msg = "combine filter is not valid UTF-8"
        raise ValueError(msg) from error


def _parse_filter(spec: str, *, depth: int) -> GitFilter:
    if depth > _MAX_NESTING:
        msg = f"filter nesting exceeds {_MAX_NESTING} levels"
        raise ValueError(msg)
    if not isinstance(spec, str) or not spec:
        msg = "filter spec must be a nonempty string"
        raise ValueError(msg)
    if any(character in spec for character in ("\x00", "\r", "\n")):
        msg = "filter spec must not contain NUL or newlines"
        raise ValueError(msg)
    if spec == "blob:none":
        return BlobNone()
    if spec.startswith("blob:limit="):
        return BlobLimit(spec.removeprefix("blob:limit="))
    if spec.startswith("tree:"):
        raw_depth = spec.removeprefix("tree:")
        return TreeDepth(_parse_git_ulong(raw_depth, field="depth"))
    if spec.startswith("object:type="):
        raw_type = spec.removeprefix("object:type=")
        if raw_type not in _OBJECT_TYPES:
            msg = "type must be blob, tree, commit, or tag"
            raise ValueError(msg)
        return ObjectType(t.cast(t.Literal["blob", "tree", "commit", "tag"], raw_type))
    if spec.startswith("sparse:oid="):
        return SparseOid(spec.removeprefix("sparse:oid="))
    if spec == "auto":
        return Auto()
    if spec.startswith("combine:"):
        raw_children = spec.removeprefix("combine:").split("+")
        if not raw_children or any(not child for child in raw_children):
            msg = "combine filters must contain nonempty children"
            raise ValueError(msg)
        children: list[GitFilter] = []
        for index, raw_child in enumerate(raw_children):
            try:
                child = _parse_filter(_decode_subfilter(raw_child), depth=depth + 1)
            except ValueError as error:
                msg = f"filters[{index}]: {error}"
                raise ValueError(msg) from None
            if isinstance(child, Auto):
                msg = f"filters[{index}]: auto cannot be combined"
                raise ValueError(msg)
            children.append(child)
        return Combine(tuple(children))
    msg = f"invalid filter spec {spec!r}"
    raise ValueError(msg)


def parse_filter(spec: str) -> GitFilter:
    """Parse one Git filter specification without running Git."""
    return _parse_filter(spec, depth=0)


def _check_mapping_fields(
    value: Mapping[str, object],
    *,
    expected: frozenset[str],
) -> None:
    fields = set(value)
    unexpected = fields - expected
    missing = expected - fields
    if unexpected:
        msg = f"unsupported field {min(unexpected, key=str)!r}"
        raise ValueError(msg)
    if missing:
        msg = f"missing field {min(missing)!r}"
        raise ValueError(msg)


def _from_mapping(value: Mapping[str, object], *, depth: int) -> GitFilter:
    if depth > _MAX_NESTING:
        msg = f"filter nesting exceeds {_MAX_NESTING} levels"
        raise ValueError(msg)
    kind = value.get("kind")
    if not isinstance(kind, str):
        msg = "kind must be a string"
        raise ValueError(msg)
    if kind == "blob:none":
        _check_mapping_fields(value, expected=frozenset(("kind",)))
        return BlobNone()
    if kind == "blob:limit":
        _check_mapping_fields(value, expected=frozenset(("kind", "limit")))
        return BlobLimit(t.cast(int | str, value["limit"]))
    if kind == "tree":
        _check_mapping_fields(value, expected=frozenset(("kind", "depth")))
        return TreeDepth(t.cast(int, value["depth"]))
    if kind == "object:type":
        _check_mapping_fields(value, expected=frozenset(("kind", "type")))
        return ObjectType(
            t.cast(t.Literal["blob", "tree", "commit", "tag"], value["type"])
        )
    if kind == "sparse:oid":
        _check_mapping_fields(value, expected=frozenset(("kind", "oid")))
        return SparseOid(t.cast(str, value["oid"]))
    if kind == "auto":
        _check_mapping_fields(value, expected=frozenset(("kind",)))
        return Auto()
    if kind == "combine":
        _check_mapping_fields(value, expected=frozenset(("kind", "filters")))
        raw_filters = value["filters"]
        if (
            not isinstance(raw_filters, Sequence)
            or isinstance(raw_filters, (str, bytes, bytearray))
            or not raw_filters
        ):
            msg = "filters must be a nonempty sequence"
            raise ValueError(msg)
        filters: list[GitFilter] = []
        for index, raw_filter in enumerate(raw_filters):
            try:
                child = _coerce_filter(raw_filter, depth=depth + 1)
            except ValueError as error:
                msg = f"filters[{index}]: {error}"
                raise ValueError(msg) from None
            if isinstance(child, Auto):
                msg = f"filters[{index}]: auto cannot be combined"
                raise ValueError(msg)
            filters.append(child)
        return Combine(tuple(filters))
    msg = f"unknown kind {kind!r}"
    raise ValueError(msg)


def from_mapping(value: Mapping[str, object]) -> GitFilter:
    """Build one Git filter from a kind-tagged mapping."""
    return _from_mapping(value, depth=0)


def _coerce_filter(value: object, *, depth: int) -> GitFilter:
    if depth > _MAX_NESTING:
        msg = f"filter nesting exceeds {_MAX_NESTING} levels"
        raise ValueError(msg)
    if isinstance(value, _FILTER_TYPES):
        return value
    if isinstance(value, str):
        return _parse_filter(value, depth=depth)
    if isinstance(value, Mapping):
        return _from_mapping(value, depth=depth)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if not value:
            msg = "filter sequence must be nonempty"
            raise ValueError(msg)
        filters: list[GitFilter] = []
        for index, item in enumerate(value):
            try:
                child = _coerce_filter(item, depth=depth + 1)
            except ValueError as error:
                msg = f"filter[{index}]: {error}"
                raise ValueError(msg) from None
            if isinstance(child, Auto):
                msg = f"filter[{index}]: auto cannot be combined"
                raise ValueError(msg)
            filters.append(child)
        return Combine(tuple(filters))
    msg = "filter must be a model, spec string, mapping, or nonempty sequence"
    raise ValueError(msg)


def coerce_filter(value: object) -> GitFilter:
    """Validate and convert one accepted filter value to a model."""
    return _coerce_filter(value, depth=0)


def filter_specs(value: GitFilterInput | None) -> tuple[str, ...]:
    """Return canonical specs, preserving one flag per sequence item."""
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            msg = "filter sequence must be nonempty"
            raise ValueError(msg)
        filters: list[GitFilter] = []
        for index, item in enumerate(value):
            try:
                child = _coerce_filter(item, depth=1)
            except ValueError as error:
                msg = f"filter[{index}]: {error}"
                raise ValueError(msg) from None
            if isinstance(child, Auto):
                msg = f"filter[{index}]: auto cannot be combined"
                raise ValueError(msg)
            filters.append(child)
        return tuple(item.to_spec() for item in filters)
    return (coerce_filter(value).to_spec(),)


__all__ = [
    "Auto",
    "BlobLimit",
    "BlobNone",
    "Combine",
    "GitFilter",
    "GitFilterInput",
    "ObjectType",
    "SparseOid",
    "TreeDepth",
    "coerce_filter",
    "filter_specs",
    "from_mapping",
    "parse_filter",
]
