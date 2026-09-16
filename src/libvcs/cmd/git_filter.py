"""Typed model for git ``--filter=<spec>`` partial-clone filters.

Wraps the filter grammar documented in ``list-objects-filter-options.c``:
``blob:none``, ``blob:limit=<n>[kmg]``, ``tree:<depth>``,
``object:type=<tag|commit|tree|blob>``, ``sparse:oid=<blob-ish>``, ``auto``,
and ``combine:<a>+<b>`` (sub-specs %-encoded).

Each filter is a frozen :func:`dataclasses.dataclass` that renders its git
spec via :meth:`__str__`. :func:`parse_filter` is the inverse (string ->
model) and :func:`from_mapping` builds a filter from config-style data (for
example, YAML: ``{kind: "blob:limit", size: "1m"}``).
"""

from __future__ import annotations

import dataclasses
import re
import typing as t
from collections.abc import Mapping, Sequence

#: Characters git's combine-filter grammar reserves and requires %-encoded
#: (``list-objects-filter-options.c``): the listed punctuation, backtick,
#: ``+``, ``%``, and any byte <= 0x20.
_COMBINE_RESERVED_CHARS = frozenset("~!@#$^&*()[]{}\\;\",<>?'`+%")

_BLOB_LIMIT_RE = re.compile(r"^\d+[kmgKMG]?$")
_OBJECT_TYPES = ("tag", "commit", "tree", "blob")
ObjectTypeLiteral = t.Literal["tag", "commit", "tree", "blob"]


def _encode_combine_part(spec: str) -> str:
    """%-encode one sub-spec for use inside a ``combine:`` filter."""
    out: list[str] = []
    for ch in spec:
        if ch in _COMBINE_RESERVED_CHARS or ord(ch) <= 0x20:
            out.extend(f"%{b:02X}" for b in ch.encode())
        else:
            out.append(ch)
    return "".join(out)


def _decode_combine_part(spec: str) -> str:
    """Reverse :func:`_encode_combine_part`."""
    out = bytearray()
    i = 0
    data = spec.encode()
    while i < len(data):
        byte = data[i]
        if byte == 0x25 and i + 2 < len(data):  # ``%``
            out.append(int(data[i + 1 : i + 3], 16))
            i += 3
        else:
            out.append(byte)
            i += 1
    return out.decode()


@dataclasses.dataclass(frozen=True)
class BlobNone:
    """``blob:none`` -- omit all blob objects."""

    kind: t.ClassVar[str] = "blob:none"

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return "blob:none"


@dataclasses.dataclass(frozen=True)
class BlobLimit:
    """``blob:limit=<n>[kmg]`` -- omit blobs larger than ``size``."""

    size: int | str

    kind: t.ClassVar[str] = "blob:limit"

    def __post_init__(self) -> None:
        """Validate ``size`` against git's ``<n>[kmg]`` grammar."""
        if isinstance(self.size, bool) or (
            isinstance(self.size, int) and self.size < 0
        ):
            msg = f"blob:limit size must be a non-negative int or str: {self.size!r}"
            raise ValueError(msg)
        if isinstance(self.size, str) and not _BLOB_LIMIT_RE.match(self.size):
            msg = f"invalid blob:limit size: {self.size!r} (expected e.g. '1k', '1m')"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return f"blob:limit={self.size}"


@dataclasses.dataclass(frozen=True)
class TreeDepth:
    """``tree:<depth>`` -- omit trees/blobs beyond ``depth``."""

    depth: int

    kind: t.ClassVar[str] = "tree"

    def __post_init__(self) -> None:
        """Validate ``depth`` is a non-negative ``int`` (``bool`` excluded)."""
        if (
            isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth < 0
        ):
            msg = f"tree depth must be an int >= 0: {self.depth!r}"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return f"tree:{self.depth}"


@dataclasses.dataclass(frozen=True)
class ObjectType:
    """``object:type=<tag|commit|tree|blob>`` -- omit objects not of this type."""

    object_type: ObjectTypeLiteral

    kind: t.ClassVar[str] = "object:type"

    def __post_init__(self) -> None:
        """Validate ``object_type`` is one of git's known object types."""
        if self.object_type not in _OBJECT_TYPES:
            msg = (
                f"invalid object:type: {self.object_type!r} "
                f"(expected one of {_OBJECT_TYPES})"
            )
            raise ValueError(msg)

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return f"object:type={self.object_type}"


@dataclasses.dataclass(frozen=True)
class SparseOid:
    """``sparse:oid=<blob-ish>`` -- use a sparse-checkout spec blob.

    Note: ``sparse:path=`` was dropped by git; only ``sparse:oid=`` remains.
    """

    oid: str

    kind: t.ClassVar[str] = "sparse:oid"

    def __post_init__(self) -> None:
        """Validate ``oid`` is non-empty."""
        if not self.oid:
            msg = "sparse:oid requires a non-empty blob-ish"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return f"sparse:oid={self.oid}"


@dataclasses.dataclass(frozen=True)
class Auto:
    """``auto`` -- let the server decide (git >= 2.54, clone/fetch only).

    Cannot be combined with other filters (see :class:`Combine`).
    """

    kind: t.ClassVar[str] = "auto"

    def __str__(self) -> str:
        """Render as a git filter spec."""
        return "auto"


#: A filter with no sub-filters (every kind besides :class:`Combine`).
SimpleGitFilter: t.TypeAlias = (
    BlobNone | BlobLimit | TreeDepth | ObjectType | SparseOid | Auto
)


@dataclasses.dataclass(frozen=True)
class Combine:
    """``combine:<a>[+<b>...]`` -- intersect one or more filters.

    Sub-specs are %-encoded per git's combine-filter grammar. ``Auto`` and
    nested ``Combine`` filters are rejected -- git's grammar does not define
    combine-of-combine, and ``auto`` cannot be combined with anything.
    """

    filters: tuple[GitFilter, ...]

    kind: t.ClassVar[str] = "combine"

    def __post_init__(self) -> None:
        """Validate there are >= 1 combinable (non-auto, non-nested) filters.

        git accepts a single sub-filter (``combine:blob:none``).
        """
        if not self.filters:
            msg = "combine requires at least 1 filter"
            raise ValueError(msg)
        for f in self.filters:
            # Compared by `.kind` (not `isinstance`) so an invalid *value*
            # (an incompatible filter kind) raises ValueError, not TypeError.
            if f.kind == Auto.kind:
                msg = "auto cannot be combined with other filters"
                raise ValueError(msg)
            if f.kind == Combine.kind:
                msg = "combine cannot nest another combine"
                raise ValueError(msg)

    def __str__(self) -> str:
        """Render as a git filter spec, %-encoding each sub-spec."""
        parts = (_encode_combine_part(str(f)) for f in self.filters)
        return "combine:" + "+".join(parts)


#: Any filter, simple or combined. Defined after :class:`Combine` since the
#: union is a real runtime expression (not a string), and ``Combine`` uses
#: this same name in its own (string, future-annotated) field annotation.
GitFilter: t.TypeAlias = SimpleGitFilter | Combine

#: Fields each ``kind`` accepts in :func:`from_mapping`, besides ``kind``.
_MAPPING_FIELDS: dict[str, tuple[str, ...]] = {
    BlobNone.kind: (),
    BlobLimit.kind: ("size",),
    TreeDepth.kind: ("depth",),
    ObjectType.kind: ("object_type",),
    SparseOid.kind: ("oid",),
    Auto.kind: (),
    Combine.kind: ("filters",),
}


def parse_filter(spec: str) -> GitFilter:
    """Parse a git ``--filter=<spec>`` string into a :data:`GitFilter`.

    Inverse of ``str()`` on any filter dataclass in this module.

    Parameters
    ----------
    spec : str
        A git filter spec, e.g. ``"blob:none"`` or ``"tree:0"``.

    Returns
    -------
    GitFilter
        The parsed filter.

    Raises
    ------
    ValueError
        If ``spec`` does not match any known filter grammar.

    Examples
    --------
    >>> parse_filter("blob:none")
    BlobNone()

    >>> parse_filter("tree:3")
    TreeDepth(depth=3)

    >>> str(parse_filter("blob:limit=1k"))
    'blob:limit=1k'
    """
    if spec == "blob:none":
        return BlobNone()
    if spec == "auto":
        return Auto()
    if spec.startswith("blob:limit="):
        return BlobLimit(size=spec.removeprefix("blob:limit="))
    if spec.startswith("tree:"):
        raw_depth = spec.removeprefix("tree:")
        try:
            depth = int(raw_depth)
        except ValueError as exc:
            msg = f"invalid tree depth: {raw_depth!r}"
            raise ValueError(msg) from exc
        return TreeDepth(depth=depth)
    if spec.startswith("object:type="):
        raw_type = spec.removeprefix("object:type=")
        if raw_type not in _OBJECT_TYPES:
            msg = f"invalid object:type: {raw_type!r} (expected one of {_OBJECT_TYPES})"
            raise ValueError(msg)
        return ObjectType(object_type=t.cast("ObjectTypeLiteral", raw_type))
    if spec.startswith("sparse:oid="):
        return SparseOid(oid=spec.removeprefix("sparse:oid="))
    if spec.startswith("combine:"):
        raw_parts = spec.removeprefix("combine:").split("+")
        sub_filters = tuple(
            parse_filter(_decode_combine_part(part)) for part in raw_parts
        )
        return Combine(filters=sub_filters)
    msg = f"unrecognized git filter spec: {spec!r}"
    raise ValueError(msg)


def from_mapping(data: Mapping[str, t.Any]) -> GitFilter:
    """Build a :data:`GitFilter` from config-style mapping data.

    Parameters
    ----------
    data : Mapping[str, Any]
        A mapping with a ``"kind"`` key naming a filter (one of
        ``"blob:none"``, ``"blob:limit"``, ``"tree"``, ``"object:type"``,
        ``"sparse:oid"``, ``"auto"``, ``"combine"``) plus that filter's
        fields. ``combine`` takes ``"filters"``, a non-empty list of nested
        mappings and/or filter-spec strings.

    Returns
    -------
    GitFilter
        The constructed filter.

    Raises
    ------
    ValueError
        If ``kind`` is missing/unknown, a required field is missing, or a
        field does not belong to that kind.
    TypeError
        If ``data`` is not a mapping.

    Examples
    --------
    >>> from_mapping({"kind": "blob:limit", "size": "1m"})
    BlobLimit(size='1m')

    >>> from_mapping({"kind": "tree", "depth": 0})
    TreeDepth(depth=0)

    A field from another kind is an error, not silently dropped:

    >>> from_mapping({"kind": "blob:none", "size": "1m"})
    Traceback (most recent call last):
    ...
    ValueError: unexpected field for blob:none filter: 'size'
    """
    if not isinstance(data, Mapping):
        msg = f"filter mapping must be a dict, got {type(data).__name__}"
        raise TypeError(msg)

    kind = data.get("kind")
    fields = _MAPPING_FIELDS.get(kind) if isinstance(kind, str) else None
    if fields is None:
        msg = f"unknown filter kind: {kind!r}"
        raise ValueError(msg)
    unexpected = sorted(set(data) - {"kind", *fields})
    if unexpected:
        plural = "s" if len(unexpected) > 1 else ""
        names = ", ".join(repr(name) for name in unexpected)
        msg = f"unexpected field{plural} for {kind} filter: {names}"
        raise ValueError(msg)

    if kind == BlobNone.kind:
        return BlobNone()
    if kind == BlobLimit.kind:
        if "size" not in data:
            msg = "blob:limit filter requires a 'size' field"
            raise ValueError(msg)
        return BlobLimit(size=data["size"])
    if kind == TreeDepth.kind:
        if "depth" not in data:
            msg = "tree filter requires a 'depth' field"
            raise ValueError(msg)
        return TreeDepth(depth=data["depth"])
    if kind == ObjectType.kind:
        if "object_type" not in data:
            msg = "object:type filter requires an 'object_type' field"
            raise ValueError(msg)
        return ObjectType(object_type=t.cast("ObjectTypeLiteral", data["object_type"]))
    if kind == SparseOid.kind:
        if "oid" not in data:
            msg = "sparse:oid filter requires an 'oid' field"
            raise ValueError(msg)
        return SparseOid(oid=data["oid"])
    if kind == Auto.kind:
        return Auto()
    if kind == Combine.kind:
        raw_filters = data.get("filters")
        if not isinstance(raw_filters, (list, tuple)) or not raw_filters:
            msg = "combine filter requires a non-empty 'filters' list"
            raise ValueError(msg)
        return Combine(filters=tuple(coerce_filter(f) for f in raw_filters))

    msg = f"unknown filter kind: {kind!r}"
    raise ValueError(msg)


def coerce_filter(value: GitFilter | str | Mapping[str, t.Any]) -> GitFilter:
    """Coerce a filter spec string, mapping, or model instance to a model.

    Parameters
    ----------
    value : GitFilter | str | Mapping[str, Any]
        A filter spec string (parsed via :func:`parse_filter`), a mapping
        (built via :func:`from_mapping`), or an existing filter instance
        (returned as-is).

    Returns
    -------
    GitFilter
        The coerced filter.
    """
    if isinstance(value, str):
        return parse_filter(value)
    if isinstance(value, Mapping):
        return from_mapping(value)
    if isinstance(
        value, (BlobNone, BlobLimit, TreeDepth, ObjectType, SparseOid, Auto, Combine)
    ):
        return value
    msg = f"cannot coerce {value!r} to a git filter"
    raise TypeError(msg)


def filter_specs(
    value: GitFilter | str | Sequence[GitFilter | str] | None,
) -> list[str]:
    """Normalize a filter argument into a list of ``--filter=`` spec strings.

    Handles the three shapes :class:`~libvcs.cmd.git.Git` methods accept: a
    single model instance, a single spec string, or a sequence of either.
    Plain strings are passed through unparsed (rendered as-is) so callers can
    hand git a spec this module doesn't model yet.

    Parameters
    ----------
    value : GitFilter | str | Sequence[GitFilter | str] | None

    Returns
    -------
    list[str]
        Zero or more spec strings, one per ``--filter=`` flag to emit.

    Examples
    --------
    >>> filter_specs(None)
    []

    >>> filter_specs("blob:none")
    ['blob:none']

    >>> filter_specs(BlobNone())
    ['blob:none']

    >>> filter_specs([BlobLimit(size="1m"), TreeDepth(depth=3)])
    ['blob:limit=1m', 'tree:3']
    """
    if value is None:
        return []
    # A `str` is itself a `Sequence[str]`: handle it (and single models) first,
    # or "blob:none" would iterate into one flag per character.
    if isinstance(value, str) or dataclasses.is_dataclass(value):
        return [str(value)]
    return [str(item) for item in value]
