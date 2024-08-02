from collections.abc import Iterable, Iterator
from types import GenericAlias
from typing import Any, TypeVar

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
