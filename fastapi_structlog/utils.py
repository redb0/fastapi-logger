from collections.abc import Generator, Iterable, Iterator, MutableMapping
import re
from types import GenericAlias
from typing import Any, Optional, TypeVar

from pydantic import BaseModel
from pydantic.fields import FieldInfo

_T = TypeVar('_T')


def check_sub_settings_unset(
    model_fields: dict[str, FieldInfo],
    values: dict[str, Any],
) -> dict[str, Any]:
    sub_settings_unset = []
    for name, field in model_fields.items():
        if (
            field.annotation
            and isinstance(field.annotation, type)
            and not isinstance(field.annotation, GenericAlias)
            and issubclass(field.annotation, BaseModel)
            and name not in values
        ):
            sub_settings_unset.append(name)
    for sub_settings in sub_settings_unset:
        values[sub_settings] = {}
    return values


def annotated_last(sequence: Iterable[_T]) -> Iterator[tuple[_T, bool]]:
    it = iter(sequence)
    try:
        previous = next(it)
    except StopIteration:
        return
    for current in it:
        yield previous, False
        previous = current
    yield previous, True


def find_by_value(
    dict_: MutableMapping[str, Any],
    key: str,
    *,
    replace: Optional[str] = None,
) -> Generator[Any, Any, None]:
    pattern_re = re.compile(key)
    if hasattr(dict_, 'items'):
        for k, v in dict_.items():
            if isinstance(v, str) and bool(re.search(pattern_re, v)):
                if replace:
                    dict_[k] = re.sub(pattern_re, replace, v)
                yield v
            if isinstance(v, dict):
                for result in find_by_value(v, key, replace=replace):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in find_by_value(d, key, replace=replace):
                        yield result

