import dataclasses
from typing import Any, Optional, Union

import pytest

from libvcs._internal.query_list import QueryList


@dataclasses.dataclass
class Obj:
    test: int
    fruit: list[str] = dataclasses.field(default_factory=list)


@pytest.mark.parametrize(
    "items,filter_expr,expected_result",
    [
        [[Obj(test=1)], None, [Obj(test=1)]],
        [[Obj(test=1)], dict(test=1), [Obj(test=1)]],
        [[Obj(test=1)], dict(test=2), []],
        [
            [Obj(test=2, fruit=["apple"])],
            dict(fruit__in="apple"),
            QueryList([Obj(test=2, fruit=["apple"])]),
        ],
        [[{"test": 1}], None, [{"test": 1}]],
        [[{"test": 1}], None, QueryList([{"test": 1}])],
        [[{"fruit": "apple"}], None, QueryList([{"fruit": "apple"}])],
        [
            [{"fruit": "apple", "banana": object()}],
            None,
            QueryList([{"fruit": "apple", "banana": object()}]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__eq="apple"),
            QueryList([{"fruit": "apple", "banana": object()}]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__eq="notmatch"),
            QueryList([]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__exact="apple"),
            QueryList([{"fruit": "apple", "banana": object()}]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__exact="notmatch"),
            QueryList([]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__iexact="Apple"),
            QueryList([{"fruit": "apple", "banana": object()}]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit__iexact="Notmatch"),
            QueryList([]),
        ],
        [
            [{"fruit": "apple", "banana": object()}],
            dict(fruit="notmatch"),
            QueryList([]),
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit="apple"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__in="app"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__icontains="App"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__contains="app"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__regex=r"app.*"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__iregex=r"App.*"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__startswith="a"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__istartswith="AP"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__startswith="z"),
            [],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__endswith="le"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__iendswith="LE"),
            [{"fruit": "apple"}],
        ],
        [
            [{"fruit": "apple"}, {"fruit": "mango"}],
            dict(fruit__endswith="z"),
            [],
        ],
        [
            [
                {"fruit": "apple"},
                {"fruit": "mango"},
                {"fruit": "banana"},
                {"fruit": "kiwi"},
            ],
            dict(fruit__in=["apple", "mango"]),
            [{"fruit": "apple"}, {"fruit": "mango"}],
        ],
        [
            [
                {"fruit": "apple"},
                {"fruit": "mango"},
                {"fruit": "banana"},
                {"fruit": "kiwi"},
            ],
            dict(fruit__nin=["apple", "mango"]),
            [{"fruit": "banana"}, {"fruit": "kiwi"}],
        ],
        [
            [
                {"place": "book store", "city": "Tampa", "state": "Florida"},
                {"place": "coffee shop", "city": "Tampa", "state": "Florida"},
                {
                    "place": "chinese restaurant",
                    "city": "ybor city",
                    "state": "Florida",
                },
                {
                    "place": "walt disney world",
                    "city": "Lake Buena Vista",
                    "state": "Florida",
                },
            ],
            dict(city="Tampa", state="Florida"),
            [
                {"place": "book store", "city": "Tampa", "state": "Florida"},
                {"place": "coffee shop", "city": "Tampa", "state": "Florida"},
            ],
        ],
        [
            [
                {"place": "book store", "city": "Tampa", "state": "Florida"},
                {"place": "coffee shop", "city": "Tampa", "state": "Florida"},
                {
                    "place": "chinese restaurant",
                    "city": "ybor city",
                    "state": "Florida",
                },
                {
                    "place": "walt disney world",
                    "city": "Lake Buena Vista",
                    "state": "Florida",
                },
            ],
            dict(place__contains="coffee", state="Florida"),
            [
                {"place": "coffee shop", "city": "Tampa", "state": "Florida"},
            ],
        ],
        [
            [
                {
                    "place": "Largo",
                    "city": "Tampa",
                    "state": "Florida",
                    "foods": {"fruit": ["banana", "orange"], "breakfast": "cereal"},
                },
                {
                    "place": "Chicago suburbs",
                    "city": "Elmhurst",
                    "state": "Illinois",
                    "foods": {"fruit": ["apple", "cantelope"], "breakfast": "waffles"},
                },
            ],
            dict(foods__fruit__contains="banana"),
            [
                {
                    "place": "Largo",
                    "city": "Tampa",
                    "state": "Florida",
                    "foods": {"fruit": ["banana", "orange"], "breakfast": "cereal"},
                },
            ],
        ],
        [
            [
                {
                    "place": "Largo",
                    "city": "Tampa",
                    "state": "Florida",
                    "foods": {"fruit": ["banana", "orange"], "breakfast": "cereal"},
                },
                {
                    "place": "Chicago suburbs",
                    "city": "Elmhurst",
                    "state": "Illinois",
                    "foods": {"fruit": ["apple", "cantelope"], "breakfast": "waffles"},
                },
            ],
            dict(foods__breakfast="cereal"),
            [
                {
                    "place": "Largo",
                    "city": "Tampa",
                    "state": "Florida",
                    "foods": {"fruit": ["banana", "orange"], "breakfast": "cereal"},
                },
            ],
        ],
        [[1, 2, 3, 4, 5], None, QueryList([1, 2, 3, 4, 5])],
        [[1, 2, 3, 4, 5], [1], QueryList([1])],
        [[1, 2, 3, 4, 5], [1, 4], QueryList([1, 4])],
        [[1, 2, 3, 4, 5], lambda val: 1 == val, QueryList([1])],
        [[1, 2, 3, 4, 5], lambda val: 2 == val, QueryList([2])],
    ],
)
def test_filter(
    items: list[dict[str, Any]],
    filter_expr: Optional[dict[str, Union[str, list[str]]]],
    expected_result: Union[QueryList[Any], list[dict[str, Any]]],
) -> None:
    qs = QueryList(items)
    if filter_expr is not None:
        if isinstance(filter_expr, dict):
            assert qs.filter(**filter_expr) == expected_result
        else:
            assert qs.filter(filter_expr) == expected_result
    else:
        assert qs.filter() == expected_result
