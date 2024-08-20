"""Module of the basic model."""

from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_structlog.utils import check_sub_settings_unset


class BaseSettingsModel(BaseSettings):
    """Basic model of the settings."""
    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_ignore_empty=True,
        env_nested_delimiter='__',
        extra='ignore',
    )

    @model_validator(mode='before')
    @classmethod
    def _check_sub_settings_unset(cls, values: dict[str, Any]) -> dict[str, Any]:
        return check_sub_settings_unset(cls.model_fields, values)
