import dataclasses
import re
import traceback
from typing import Any, Callable, Generic, Optional, Protocol, Sequence, TypeVar, Union

T = TypeVar("T", Any, Any)


def keygetter(obj, path):
    """obj, "foods__breakfast", obj['foods']['breakfast']

    >>> keygetter({ "foods": { "breakfast": "cereal" } }, "foods__breakfast")
    'cereal'
    >>> keygetter({ "foods": { "breakfast": "cereal" } }, "foods")
    {'breakfast': 'cereal'}

    """
    try:
        sub_fields = path.split("__")
        dct = obj
        for sub_field in sub_fields:
            dct = dct[sub_field]
        return dct
    except Exception as e:
        traceback.print_exception(e)
    return None


def parse_lookup(obj, path, lookup):
    """Check if field lookup key, e.g. "my__path__contains" has comparator, return val.

    If comparator not used or value not found, return None.

    mykey__endswith("mykey") -> "mykey" else None

    >>> parse_lookup({ "food": "red apple" }, "food__istartswith", "__istartswith")
    'red apple'
    """
    try:
        if path.endswith(lookup):
            if field_name := path.rsplit(lookup)[0]:
                return keygetter(obj, field_name)
    except Exception as e:
        traceback.print_exception(e)
    return None


class LookupProtocol(Protocol):
    """Protocol for :class:`QueryList` filtering operators."""

    def __call__(self, data: Union[list[str], str], rhs: Union[list[str], str]):
        """Callback for :class:`QueryList` filtering operators."""


def lookup_exact(data, rhs):
    return rhs == data


def lookup_iexact(data, rhs):
    return rhs.lower() == data.lower()


def lookup_contains(data, rhs):
    return rhs in data


def lookup_icontains(data, rhs):
    return rhs.lower() in data.lower()


def lookup_startswith(data, rhs):
    return data.startswith(rhs)


def lookup_istartswith(data, rhs):
    return data.lower().startswith(rhs.lower())


def lookup_endswith(data, rhs):
    return data.endswith(rhs)


def lookup_iendswith(data, rhs):
    return data.lower().endswith(rhs.lower())


def lookup_in(data, rhs):
    if isinstance(rhs, list):
        return data in rhs
    return rhs in data


def lookup_nin(data, rhs):
    if isinstance(rhs, list):
        return data not in rhs
    return rhs not in data


def lookup_regex(data, rhs):
    return re.search(rhs, data)


def lookup_iregex(data, rhs):
    return re.search(rhs, data, re.IGNORECASE)


LOOKUP_NAME_MAP: dict[str, LookupProtocol] = {
    "eq": lookup_exact,
    "exact": lookup_exact,
    "iexact": lookup_iexact,
    "contains": lookup_contains,
    "icontains": lookup_icontains,
    "startswith": lookup_startswith,
    "istartswith": lookup_istartswith,
    "endswith": lookup_endswith,
    "iendswith": lookup_iendswith,
    "in": lookup_in,
    "nin": lookup_nin,
    "regex": lookup_regex,
    "iregex": lookup_iregex,
}


@dataclasses.dataclass(eq=False)
class QueryList(Generic[T]):
    """Filter list of object/dicts. For small, local datasets. *Experimental, unstable*.

    :py:func:`dataclasses.dataclass` is only used for ``__repr__`` and pytest comparison
    details.

    >>> query = QueryList(
    ...     [
    ...         {
    ...             "place": "Largo",
    ...             "city": "Tampa",
    ...             "state": "Florida",
    ...             "foods": {"fruit": ["banana", "orange"], "breakfast": "cereal"},
    ...         },
    ...         {
    ...             "place": "Chicago suburbs",
    ...             "city": "Elmhurst",
    ...             "state": "Illinois",
    ...             "foods": {"fruit": ["apple", "cantelope"], "breakfast": "waffles"},
    ...         },
    ...     ]
    ... )
    >>> query.filter(place="Chicago suburbs").data[0]['city']
    'Elmhurst'
    >>> query.filter(place__icontains="chicago").data[0]['city']
    'Elmhurst'
    >>> query.filter(foods__breakfast="waffles").data[0]['city']
    'Elmhurst'
    >>> query.filter(foods__fruit__in="cantelope").data[0]['city']
    'Elmhurst'
    >>> query.filter(foods__fruit__in="orange").data[0]['city']
    'Tampa'
    """

    __slots__ = ("data", "pk_key")
    data: Sequence[T]

    # def __init__(self, data, pk_key: Optional[str] = None):
    #     self.data: Sequence[T] = data
    #     #: Primary key for objects, optional.
    #     #: Use for .get(), .items()
    #     self.pk_key: Optional[Any] = pk_key

    def items(self):
        data: Sequence[T]

        if self.pk_key is None:
            raise Exception("items() require a pk_key exists")
        return [(getattr(item, self.pk_key), item) for item in self.data]

    def __eq__(self, other):
        data = other
        if hasattr(data, "data"):
            data = getattr(data, "data")

        if not isinstance(self.data, list) or not isinstance(data, list):
            return False

        if len(self.data) == len(data):
            for (a, b) in zip(self.data, data):
                if isinstance(a, dict):
                    a_keys = a.keys()
                    if a.keys == b.keys():
                        for key in a_keys:
                            if abs(a[key] - b[key]) > 1:
                                return False
                else:
                    if a != b:
                        return False

            return True
        return False

    def filter(self, matcher: Optional[Union[Callable[[T], bool], T]] = None, **kwargs):
        def filter_lookup(obj) -> bool:
            for path, v in kwargs.items():
                try:
                    lhs, op = path.rsplit("__", 1)

                    if op not in LOOKUP_NAME_MAP:
                        raise ValueError(f"{op} not in LOOKUP_NAME_MAP")
                except ValueError:
                    lhs = path
                    op = "exact"

                assert op in LOOKUP_NAME_MAP
                path = lhs
                data = keygetter(obj, path)

                if not LOOKUP_NAME_MAP[op](data, v):
                    return False

            return True

        if callable(matcher):
            _filter = matcher
        elif matcher is not None:

            def val_match(obj):
                if isinstance(matcher, list):
                    return obj in matcher
                else:
                    return obj == matcher

            _filter = val_match
        else:
            _filter = filter_lookup

        return self.__class__(data=[k for k in self.data if _filter(k)])
