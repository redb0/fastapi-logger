"""SQLModel Base Model module."""

from types import GenericAlias
from typing import Any

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseSettingsModel(BaseSettings):
    """Base model for settings."""
    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_ignore_empty=True,
        env_nested_delimiter='__',
        extra='ignore',
    )

    @model_validator(mode='before')
    @classmethod
    def _check_sub_settings_unset(cls, values: dict[str, Any]) -> dict[str, Any]:
        sub_settings_unset = []
        for name, field in cls.model_fields.items():
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
