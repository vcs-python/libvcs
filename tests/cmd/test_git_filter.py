"""Tests for typed Git partial-clone filters."""

from __future__ import annotations

import dataclasses
import typing as t

import pytest

from libvcs.cmd.git_filter import (
    Auto,
    BlobLimit,
    BlobNone,
    Combine,
    GitFilter,
    ObjectType,
    SparseOid,
    TreeDepth,
    coerce_filter,
    filter_specs,
    from_mapping,
    parse_filter,
)


class FilterFixture(t.NamedTuple):
    """Canonical filter model and spec pair."""

    test_id: str
    model: GitFilter
    spec: str


FILTER_FIXTURES = [
    FilterFixture("blob-none", BlobNone(), "blob:none"),
    FilterFixture("blob-limit-int", BlobLimit(1024), "blob:limit=1024"),
    FilterFixture("blob-limit-numeric-string", BlobLimit("001024"), "blob:limit=1024"),
    FilterFixture("blob-limit-unit", BlobLimit("4m"), "blob:limit=4m"),
    FilterFixture("tree-depth", TreeDepth(2), "tree:2"),
    FilterFixture("object-type", ObjectType("commit"), "object:type=commit"),
    FilterFixture(
        "sparse-oid", SparseOid("refs/filters/base"), "sparse:oid=refs/filters/base"
    ),
    FilterFixture("auto", Auto(), "auto"),
    FilterFixture(
        "combine",
        Combine((BlobNone(), TreeDepth(1))),
        "combine:blob:none+tree:1",
    ),
    FilterFixture(
        "combine-escaped",
        Combine((SparseOid("refs/filters/a b+c"),)),
        "combine:sparse:oid=refs/filters/a%20b%2Bc",
    ),
]


@pytest.mark.parametrize(
    ("model", "spec"),
    [(fixture.model, fixture.spec) for fixture in FILTER_FIXTURES],
    ids=[fixture.test_id for fixture in FILTER_FIXTURES],
)
def test_filter_canonical_round_trip(
    model: GitFilter,
    spec: str,
) -> None:
    """Each model serializes to one canonical spec and parses back."""
    assert filter_specs(model) == (spec,)
    assert parse_filter(spec) == model
    assert coerce_filter(spec) == model


@pytest.mark.parametrize(
    ("mapping", "expected"),
    [
        ({"kind": "blob:none"}, BlobNone()),
        ({"kind": "blob:limit", "limit": "5k"}, BlobLimit("5k")),
        ({"kind": "tree", "depth": 3}, TreeDepth(3)),
        ({"kind": "object:type", "type": "tag"}, ObjectType("tag")),
        (
            {"kind": "sparse:oid", "oid": "refs/filters/base"},
            SparseOid("refs/filters/base"),
        ),
        ({"kind": "auto"}, Auto()),
        (
            {
                "kind": "combine",
                "filters": [
                    {"kind": "blob:none"},
                    {"kind": "tree", "depth": 2},
                ],
            },
            Combine((BlobNone(), TreeDepth(2))),
        ),
    ],
)
def test_filter_from_mapping(
    mapping: dict[str, object],
    expected: GitFilter,
) -> None:
    """Kind-tagged mappings produce typed filters."""
    assert from_mapping(mapping) == expected
    assert coerce_filter(mapping) == expected


def test_filter_sequence_is_a_combine_model_but_preserves_command_flags() -> None:
    """Coercion combines a sequence while command serialization keeps its items."""
    value = ["blob:none", {"kind": "tree", "depth": 2}]

    assert coerce_filter(value) == Combine((BlobNone(), TreeDepth(2)))
    assert filter_specs(value) == ("blob:none", "tree:2")


def test_filter_models_are_immutable() -> None:
    """Filter values cannot change after validation."""
    value = BlobLimit(10)

    with pytest.raises(dataclasses.FrozenInstanceError):
        value.limit = 20  # type: ignore[misc]


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (lambda: BlobLimit(True), "limit"),
        (lambda: BlobLimit(-1), "limit"),
        (lambda: BlobLimit("1t"), "limit"),
        (lambda: BlobLimit("18446744073709551616"), "limit"),
        (lambda: TreeDepth(False), "depth"),
        (lambda: TreeDepth(-1), "depth"),
        (lambda: ObjectType(t.cast(t.Any, "delta")), "type"),
        (lambda: SparseOid(""), "oid"),
        (lambda: SparseOid("bad\nref"), "oid"),
        (lambda: Combine(()), "filters"),
        (lambda: Combine((Auto(),)), "auto"),
    ],
)
def test_filter_model_rejects_invalid_fields(
    factory: t.Callable[[], object],
    match: str,
) -> None:
    """Direct model construction enforces the Git grammar."""
    with pytest.raises(ValueError, match=match):
        factory()


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (None, "filter"),
        ([], "nonempty"),
        (["blob:none", "auto"], r"filter\[1\].*auto"),
        (["blob:none", "wat"], r"filter\[1\]"),
        ({"kind": "blob:none", "depth": 1}, "depth"),
        ({"kind": "blob:limit"}, "limit"),
        ({"kind": "tree", "limit": 1}, "limit"),
        ({"kind": "unknown"}, "kind"),
        ({"kind": "combine", "filters": []}, "filters"),
        ({"kind": "combine", "filters": "blob:none"}, "filters"),
    ],
)
def test_filter_coercion_rejects_invalid_config(
    value: object,
    match: str,
) -> None:
    """Config errors name the bad field or list item."""
    with pytest.raises(ValueError, match=match):
        coerce_filter(value)


@pytest.mark.parametrize(
    "spec",
    [
        "",
        "blob:limit=-1",
        "blob:limit=true",
        "tree:-1",
        "object:type=delta",
        "sparse:oid=",
        "blob:none\n",
        "sparse:oid=bad\x00ref",
        "combine:",
        "combine:+blob:none",
        "combine:blob:none+",
        "combine:auto",
        "combine:blob%",
        "combine:blob%2",
        "combine:blob%zz",
        "combine:blob:none tree:1",
        "combine:sparse:oid=bad%00ref",
    ],
)
def test_parse_filter_rejects_malformed_specs(spec: str) -> None:
    """Malformed filter specs fail without consulting Git."""
    with pytest.raises(ValueError):
        parse_filter(spec)


def test_filter_specs_treats_none_as_no_filter() -> None:
    """Only the optional command serializer accepts None."""
    assert filter_specs(None) == ()


def test_filter_recursion_is_bounded() -> None:
    """Nested config cannot recurse without limit."""
    value: dict[str, object] = {"kind": "blob:none"}
    for _ in range(40):
        value = {"kind": "combine", "filters": [value]}

    with pytest.raises(ValueError, match="nesting"):
        coerce_filter(value)
