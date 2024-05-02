"""Sentry configuration."""
import logging
from enum import StrEnum, auto

from pydantic import AnyHttpUrl, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class Environment(StrEnum):
    """Environment options."""
    PROD = auto()
    PREVIEW = auto()
    TEST = auto()
    DEV = auto()


class SentrySettings(BaseSettings):
    """Sentry configuration.

    Args:
        dsn (AnyHttpUrl | None): Sentry dsn.
        env (Environment | str | None): Environment.
        traces_sample_rate (float): Uniform sample rate.
            See. https://docs.sentry.io/platforms/python/configuration/sampling/#configuring-the-transaction-sample-rate.
        _env_prefix (str | None): prefix of the settings for the .ini file
            (needed only to get rid of the listing error when using
            `Sentry Settings(_and_prefix=...)`)

    """

    dsn: AnyHttpUrl | None = None
    env: Environment | None = Field(default=None, alias="environment")
    traces_sample_rate: float = 1.0

    log_integration: bool = Field(default=True, exclude=True)
    log_integration_event_level: int | None = Field(default=None, exclude=True)
    log_integration_level: int | None = Field(default=None, exclude=True)
    sql_integration: bool = Field(default=True, exclude=True)

    _env_prefix: str | None = None

    @field_validator("env", mode="before")
    @classmethod
    def _enum_upper(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.lower()
        return value

    @field_validator("log_integration_event_level", "log_integration_level", mode="before")
    @classmethod
    def _set_log_level(cls, value: str | None, info: ValidationInfo) -> int | None:
        mapping = logging.getLevelNamesMapping()
        if isinstance(value, str):
            try:
                return mapping[value.upper()]
            except KeyError as error:
                msg = (
                    f"{info.field_name} expects one of the values "
                    f"{', '.join(map(repr, mapping.keys()))}, got {value}"
                )
                raise ValueError(msg) from error
        return value

    @property
    def is_prod(self) -> bool:
        """The environment is a productive environment.

        Returns:
            bool: ``True`` if the environment is a productive environment, otherwise ``False``
        """
        return self.env is Environment.PROD
