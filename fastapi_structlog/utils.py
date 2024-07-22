from types import GenericAlias
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo


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
