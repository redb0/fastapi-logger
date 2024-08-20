"""Logging library.

Provides a wrapper over the structlog for additional doping in json format,
as well as output of standard logs to the console, configuration via .env
files via pydantic.
"""

import logging
import logging.handlers
from collections.abc import Callable, Sequence
from typing import Any, Optional, Union

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


def setup_logger(  # noqa: PLR0913
    settings_: LogSettings,
    *,
    model: Optional[type[SQLModel]] = None,
    db_url: Optional[Union[str, URL]] = None,
    key_aliases: Optional[dict[str, list[str]]] = None,
    key_handlers: Optional[dict[str, Callable[[Any, logging.LogRecord], Any]]] = None,
    search_paths: Optional[dict[str, list[str]]] = None,
    available_loggers: Optional[Sequence[str]] = None,
) -> Optional[logging.handlers.QueueListener]:
    """Initialize the logger with the configuration.

    Args:
        settings_ (LogSettings): Logger settings.
        model (Optional[type[SQLModel]], optional): Model to save to the database.
            Defaults to `None`.
        db_url (Optional[Union[str, URL]], optional): Database connection string.
            Defaults to `None`.
        key_aliases (Optional[dict[str, list[str]]], optional): Aliases for model
            attributes. By default, `None`, that is, the search is performed only
            by model attributes and base aliases.
        key_handlers (Optional[dict[str, Callable[[Any, logging.LogRecord], Any]]], optional):
            Handlers for model attribute values. This is a function that takes a
            found value and a log record and returns a new value.
        search_paths (Optional[dict[str, list[str]]], optional): Search paths
            for model attributes. This can be useful when searching for
            attributes in nested log structures.
        available_loggers (Optional[Sequence[str]], optional): Names of the
            loggers that will be included in the database.
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
                key_aliases=key_aliases,
                search_paths=search_paths,
                key_handlers=key_handlers,
                available_loggers=available_loggers,
            ),
        )

    if not settings_.enable:
        logging.disable()

    return configurator.setup()


__all__ = (
    'LogSettings',
    'LogType',
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
