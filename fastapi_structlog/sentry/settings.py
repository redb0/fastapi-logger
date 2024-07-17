"""Sentry configuration."""
import logging
from enum import Enum
from typing import Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Environment options."""
    PROD = 'prod'
    PREVIEW = 'preview'
    TEST = 'test'
    DEV = 'dev'


class SentrySettings(BaseSettings):
    """Sentry configuration.

    Args:
        dsn (Optional[AnyHttpUrl]): Sentry dsn.
        env (Optional[Environment]): Environment.
        traces_sample_rate (float): Uniform sample rate.
            See. https://docs.sentry.io/platforms/python/configuration/sampling/#configuring-the-transaction-sample-rate.
        _env_prefix (Optional[str]): prefix of the settings for the .ini file
            (needed only to get rid of the listing error when using
            `Sentry Settings(_and_prefix=...)`)

    """

    dsn: Optional[AnyHttpUrl] = None
    env: Optional[Environment] = Field(default=None, alias='environment')
    traces_sample_rate: float = 1.0

    log_integration: bool = Field(default=True, exclude=True)
    log_integration_event_level: Optional[int] = Field(default=None, exclude=True)
    log_integration_level: Optional[int] = Field(default=None, exclude=True)
    sql_integration: bool = Field(default=True, exclude=True)

    _env_prefix: Optional[str] = None

    @field_validator('env', mode='before')
    @classmethod
    def _enum_upper(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            value = value.lower()
        return value

    @field_validator('log_integration_event_level', 'log_integration_level', mode='before')
    @classmethod
    def _set_log_level(cls, value: Optional[str]) -> Optional[int]:
        if isinstance(value, str):
            try:
                level = logging.getLevelName(value.upper())
                if isinstance(level, int):
                    return level
            except KeyError as error:
                msg = 'Incorrect logging level'
                raise ValueError(msg) from error
        return None

    @property
    def is_prod(self) -> bool:
        """The environment is a productive environment.

        Returns:
            bool: ``True`` if the environment is a productive environment, otherwise ``False``
        """
        return self.env is Environment.PROD
