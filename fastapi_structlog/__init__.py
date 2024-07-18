"""Logging library.

Provides a wrapper over the structlog for additional doping in json format,
as well as output of standard logs to the console, configuration via .env
files via pydantic.
"""

import logging.handlers
from typing import Optional, Union

from sqlalchemy.engine.url import URL
from sqlmodel import SQLModel

from fastapi_structlog.base import BaseSettingsModel
from fastapi_structlog.log import (
    DatabaseHandlerFactory,
    FileHandlerFactory,
    LoggerConfigurator,
    SyslogHandlerFactory,
    base_formatter,
)
from fastapi_structlog.settings import LogSettings, LogType


def init_logger(
    env_prefix: Optional[str] = None,
    *,
    model: Optional[type[SQLModel]] = None,
    db_url: Optional[Union[str, URL]] = None,
) -> Optional[logging.handlers.QueueListener]:
    """Initialize the logger with the configuration from the .env file or environment variables.

    Args:
        env_prefix (Optional[str], optional): Prefix of the logger settings. Defaults to None.
        model (Optional[type[SQLModel]], optional): Model to save to the database. Defaults to None.
        db_url (Optional[Union[str, URL]], optional): Database connection string. Defaults to None.

    """
    settings_ = LogSettings(_env_prefix=env_prefix)

    return setup_logger(settings_, model=model, db_url=db_url)


def setup_logger(
    settings_: LogSettings,
    *,
    model: Optional[type[SQLModel]] = None,
    db_url: Optional[Union[str, URL]] = None,
) -> Optional[logging.handlers.QueueListener]:
    """Initialize the logger with the configuration.

    Args:
        settings_ (LogSettings): Logger settings.
        model (Optional[type[SQLModel]], optional): Model to save to the database. Defaults to None.
        db_url (Optional[Union[str, URL]], optional): Database connection string. Defaults to None.

    """
    configurator = LoggerConfigurator(settings_)
    configurator.add_base_handler()
    if settings_.filename:
        configurator.add_handler(
            LogType.FILE,
            FileHandlerFactory().create(
                filename=settings_.filename,
                when=settings_.when,
                backup_count=settings_.backup_count,
            ),
        )
    if settings_.syslog.host:
        configurator.add_handler(
            LogType.SYSLOG,
            SyslogHandlerFactory(formatter=base_formatter(settings_)).create(
                host=settings_.syslog.host,
                port=settings_.syslog.port,
            ),
        )
    if db_url and model:
        configurator.add_handler(
            LogType.INTERNAL,
            DatabaseHandlerFactory().create(
                model=model,
                db_url=db_url,
            ),
        )

    return configurator.setup()


__all__ = (
    'LogSettings',
    'LogType',
    'init_logger',
    'setup_logger',
    'LoggerConfigurator',
    'DatabaseHandlerFactory',
    'SyslogHandlerFactory',
    'StreamHandlerFactory',
    'FileHandlerFactory',
    'HandlerFactory',
    'base_formatter',
    'BaseSettingsModel',
)
