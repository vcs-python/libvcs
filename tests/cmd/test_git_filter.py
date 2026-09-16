"""Tests for libvcs.cmd.git_filter."""

from __future__ import annotations

import typing as t

import pytest

from libvcs.cmd.git_filter import (
    Auto,
    BlobLimit,
    BlobNone,
    Combine,
    ObjectType,
    SparseOid,
    TreeDepth,
    filter_specs,
    from_mapping,
    parse_filter,
)


class RoundTripFixture(t.NamedTuple):
    """Parameters for :func:`test_parse_filter_round_trip`."""

    test_id: str
    spec: str


ROUND_TRIP_FIXTURES: list[RoundTripFixture] = [
    RoundTripFixture(test_id="blob-none", spec="blob:none"),
    RoundTripFixture(test_id="blob-limit", spec="blob:limit=1k"),
    RoundTripFixture(test_id="tree-depth", spec="tree:0"),
    RoundTripFixture(test_id="object-type", spec="object:type=blob"),
    RoundTripFixture(test_id="auto", spec="auto"),
    RoundTripFixture(
        test_id="combine-needs-percent-encoding",
        # sparse:oid's blob-ish contains `~` (reserved) and `:` (part of the
        # grammar, not reserved) -- `~` must round-trip through %-encoding.
        spec="combine:blob:none+sparse:oid=HEAD%7E1:.gitfilter",
    ),
    RoundTripFixture(test_id="combine-single", spec="combine:blob:none"),
]


@pytest.mark.parametrize(
    list(RoundTripFixture._fields),
    ROUND_TRIP_FIXTURES,
    ids=[f.test_id for f in ROUND_TRIP_FIXTURES],
)
def test_parse_filter_round_trip(test_id: str, spec: str) -> None:
    """str(parse_filter(spec)) reproduces the original spec exactly."""
    assert str(parse_filter(spec)) == spec


class InvalidSpecFixture(t.NamedTuple):
    """Parameters for :func:`test_parse_filter_rejects_invalid`."""

    test_id: str
    spec: str


INVALID_SPEC_FIXTURES: list[InvalidSpecFixture] = [
    InvalidSpecFixture(test_id="blob-none-typo", spec="blob:nonee"),
    InvalidSpecFixture(test_id="blob-limit-bad-size", spec="blob:limit=lots"),
    InvalidSpecFixture(test_id="tree-non-numeric", spec="tree:abc"),
    InvalidSpecFixture(test_id="object-type-bogus", spec="object:type=nope"),
    InvalidSpecFixture(test_id="unrecognized-kind", spec="widget:none"),
]


@pytest.mark.parametrize(
    list(InvalidSpecFixture._fields),
    INVALID_SPEC_FIXTURES,
    ids=[f.test_id for f in INVALID_SPEC_FIXTURES],
)
def test_parse_filter_rejects_invalid(test_id: str, spec: str) -> None:
    """parse_filter raises ValueError on grammar violations, not silent accept."""
    with pytest.raises(ValueError, match=r".+"):
        parse_filter(spec)


class FromMappingFixture(t.NamedTuple):
    """Parameters for :func:`test_from_mapping`."""

    test_id: str
    mapping: dict[str, t.Any]
    expected: t.Any


FROM_MAPPING_FIXTURES: list[FromMappingFixture] = [
    FromMappingFixture(
        test_id="blob-none",
        mapping={"kind": "blob:none"},
        expected=BlobNone(),
    ),
    FromMappingFixture(
        test_id="blob-limit",
        mapping={"kind": "blob:limit", "size": "1m"},
        expected=BlobLimit(size="1m"),
    ),
    FromMappingFixture(
        test_id="tree",
        mapping={"kind": "tree", "depth": 3},
        expected=TreeDepth(depth=3),
    ),
    FromMappingFixture(
        test_id="object-type",
        mapping={"kind": "object:type", "object_type": "blob"},
        expected=ObjectType(object_type="blob"),
    ),
    FromMappingFixture(
        test_id="sparse-oid",
        mapping={"kind": "sparse:oid", "oid": "HEAD"},
        expected=SparseOid(oid="HEAD"),
    ),
    FromMappingFixture(
        test_id="auto",
        mapping={"kind": "auto"},
        expected=Auto(),
    ),
    FromMappingFixture(
        test_id="combine-of-strings-and-mappings",
        mapping={
            "kind": "combine",
            "filters": ["blob:none", {"kind": "tree", "depth": 1}],
        },
        expected=Combine(filters=(BlobNone(), TreeDepth(depth=1))),
    ),
]


@pytest.mark.parametrize(
    list(FromMappingFixture._fields),
    FROM_MAPPING_FIXTURES,
    ids=[f.test_id for f in FROM_MAPPING_FIXTURES],
)
def test_from_mapping(
    test_id: str,
    mapping: dict[str, t.Any],
    expected: t.Any,
) -> None:
    """from_mapping builds the expected filter model from config-style data."""
    assert from_mapping(mapping) == expected


class InvalidMappingFixture(t.NamedTuple):
    """Parameters for :func:`test_from_mapping_rejects_invalid`."""

    test_id: str
    mapping: dict[str, t.Any]


INVALID_MAPPING_FIXTURES: list[InvalidMappingFixture] = [
    InvalidMappingFixture(test_id="unknown-kind", mapping={"kind": "nope"}),
    InvalidMappingFixture(
        test_id="blob-limit-missing-size",
        mapping={"kind": "blob:limit"},
    ),
    InvalidMappingFixture(
        test_id="blob-limit-bad-size",
        mapping={"kind": "blob:limit", "size": "lots"},
    ),
    InvalidMappingFixture(
        test_id="combine-empty",
        mapping={"kind": "combine", "filters": []},
    ),
    InvalidMappingFixture(
        test_id="tree-depth-bool",
        mapping={"kind": "tree", "depth": True},
    ),
    InvalidMappingFixture(
        test_id="tree-depth-str",
        mapping={"kind": "tree", "depth": "3"},
    ),
    InvalidMappingFixture(
        test_id="field-from-another-kind",
        mapping={"kind": "blob:none", "size": "1m"},
    ),
]


@pytest.mark.parametrize(
    list(InvalidMappingFixture._fields),
    INVALID_MAPPING_FIXTURES,
    ids=[f.test_id for f in INVALID_MAPPING_FIXTURES],
)
def test_from_mapping_rejects_invalid(
    test_id: str,
    mapping: dict[str, t.Any],
) -> None:
    """from_mapping raises ValueError on missing/invalid fields."""
    with pytest.raises(ValueError, match=r".+"):
        from_mapping(mapping)


def test_combine_rejects_auto_member() -> None:
    """`auto` cannot be combined with other filters (git's grammar forbids it)."""
    with pytest.raises(ValueError, match="auto"):
        Combine(filters=(BlobNone(), Auto()))


def test_combine_rejects_nested_combine() -> None:
    """Combine cannot nest another combine."""
    inner = Combine(filters=(BlobNone(), TreeDepth(depth=1)))
    with pytest.raises(ValueError, match="nest"):
        Combine(filters=(inner, BlobNone()))


class FilterSpecsFixture(t.NamedTuple):
    """Parameters for :func:`test_filter_specs`."""

    test_id: str
    value: t.Any
    expected: list[str]


FILTER_SPECS_FIXTURES: list[FilterSpecsFixture] = [
    FilterSpecsFixture(test_id="none", value=None, expected=[]),
    FilterSpecsFixture(
        test_id="bare-string", value="blob:none", expected=["blob:none"]
    ),
    FilterSpecsFixture(
        test_id="single-dataclass",
        value=BlobNone(),
        expected=["blob:none"],
    ),
    FilterSpecsFixture(
        test_id="list-of-dataclasses",
        value=[BlobLimit(size="1m"), TreeDepth(depth=3)],
        expected=["blob:limit=1m", "tree:3"],
    ),
    FilterSpecsFixture(
        test_id="list-of-strings",
        value=["blob:none", "tree:0"],
        expected=["blob:none", "tree:0"],
    ),
]


@pytest.mark.parametrize(
    list(FilterSpecsFixture._fields),
    FILTER_SPECS_FIXTURES,
    ids=[f.test_id for f in FILTER_SPECS_FIXTURES],
)
def test_filter_specs(test_id: str, value: t.Any, expected: list[str]) -> None:
    """filter_specs normalizes None/str/model/sequence into a flat spec list.

    Regression: a bare spec string is itself a `Sequence[str]` -- without a
    string check first, "blob:none" would iterate into nine single-char
    flags instead of one.
    """
    assert filter_specs(value) == expected
