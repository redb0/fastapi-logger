"""Configuration Module."""

from enum import Enum
from typing import Literal, Optional, Union

from pydantic import Field, FilePath, SecretStr, field_validator
from sqlalchemy.engine.url import URL
from sqlalchemy.engine.url import make_url as make_url_

from fastapi_structlog.base import BaseSettingsModel


class LogType(Enum):
    """Type of logging."""
    CONSOLE = 'console'
    INTERNAL = 'internal'
    SYSLOG = 'syslog'
    FILE = 'file'


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = 'get'
    DELETE = 'delete'
    POST = 'post'
    PUT = 'put'
    PATCH = 'patch'
    OPTIONS = 'options'
    HEAD = 'head'


class SysLogSettings(BaseSettingsModel):
    """Syslog Server configuration."""
    host: Optional[str] = Field(
        default=None,
        description='Syslog server address',
    )
    port: int = Field(
        default=6514,
        description='Syslog server port',
    )


class DBSettings(BaseSettingsModel):
    """Database configuration for logging."""

    is_async: bool = True

    url: Optional[Union[str, URL]] = Field(
        default=None,
        description='Database connection string',
    )

    user: str = Field(
        default='postgres',
        description='User who will be used to connect to the database',
    )
    password: Optional[SecretStr] = Field(
        default=None,
        description='Database password',
    )
    host: str = Field(
        default='localhost',
        description='Database address',
    )
    port: int = Field(
        default=5432,
        description='Database port',
    )
    name: str = Field(
        default='postgres',
        description='Database name',
    )

    def make_url(self) -> URL:  # noqa: D102
        if self.url:
            return make_url_(self.url)

        return URL.create(
            drivername='asyncpg' if self.is_async else 'psycopg2',
            username=self.user,
            password=self.password._secret_value if self.password else None,
            host=self.host,
            port=self.port,
            database=self.name,
        )


class LogSettings(BaseSettingsModel):
    """Logging configuration.

    Attributes:
        logger (str): Name of the logger
        log_level (str): Logging level (see https://docs.python.org/3/library/logging.html#logging-levels)
        json_logs (bool): The flag that activates logging in json format,
            by default ``True``. If the value is set to ``False``,
            the logs will be adapted to `stdout`.
        traceback_as_str (bool): Logging of the traceback in string form,
            by default ``True``. If the value is set to ``False``, the traceback
            will be converted to json format. It only works when the
            ``json_logs`` parameter is active.
        filename (Path | str | None): The name of the file. It is not set by default.
        when (Literal["S", "M", "H", "D", "W"]): The interval of writing to the file.
            See :class:`logging.handlers.TimedRotatingFileHandler`.
        backup_count (int): The number of saved files, by default 1.
            See :class:`logging.handlers.TimedRotatingFileHandler`.
        debug (bool): DEBUG mode, default is ``False``. If the value is
            set to ``True``, the DEBUG logging level will be set forcibly.
        event_key (str): New name for the key ``event``.
            See :class:`structlog.processors.EventRenamer`.
    """

    logger: str = 'default'
    log_level: str = 'INFO'
    json_logs: bool = True
    traceback_as_str: bool = True
    filename: Optional[FilePath] = Field(
        default=None,
        description='Path to the log file with the name and extension',
    )
    when: Literal['S', 'M', 'H', 'D', 'W'] = 'D'
    backup_count: int = 1
    debug: bool = False
    event_key: str = 'message'

    enable: bool = Field(
        default=False,
        description='Enable logging',
    )
    methods: list[HTTPMethod] = Field(
        default=[i.value for i in HTTPMethod],
        description='Log messages in a structured format',
    )
    types: list[LogType] = Field(
        default=[LogType.CONSOLE],
        description='Type of logging',
    )
    ttl: int = Field(
        default=90,
        description=(
            'Number of days to store the log entry. Applies only to the Internal type'
        ),
    )

    syslog: SysLogSettings
    db: DBSettings

    _env_prefix: Optional[str] = None

    @field_validator('methods', mode='before')
    @classmethod
    def _create_methods(cls, value: Union[str, list[str], list[HTTPMethod]]) -> list[HTTPMethod]:
        if isinstance(value, str):
            return [HTTPMethod(i.strip().lower()) for i in value.strip('[]').split(',')]
        return [HTTPMethod(i.strip().lower()) if isinstance(i, str) else i for i in value]

    @field_validator('types', mode='before')
    @classmethod
    def _create_types(cls, value: Union[str, list[str], list[LogType]]) -> list[LogType]:
        if isinstance(value, str):
            return [LogType(i.strip().lower()) for i in value.strip('[]').split(',')]
        return [LogType(i.strip().lower()) if isinstance(i, str) else i for i in value]
