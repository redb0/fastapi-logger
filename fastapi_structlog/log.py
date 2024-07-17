"""Logger configuration module via structlog."""
import logging
import logging.handlers
import sys
from abc import abstractmethod
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from queue import SimpleQueue
from types import TracebackType
from typing import Any, Generic, Literal, Optional, TextIO, TypeVar, Union

import structlog
from sqlalchemy.engine.url import URL
from sqlmodel import SQLModel
from structlog.types import Processor

from fastapi_structlog.db_handler.handler import DatabaseHandler, QueueHandler
from fastapi_structlog.exceptions import SysLogConnectionError
from fastapi_structlog.factory import LoggerFactory
from fastapi_structlog.settings import LogSettings, LogType

try:
    from structlog_sentry import SentryProcessor
    find_structlog_sentry = True
except ImportError:
    find_structlog_sentry = False

try:
    import orjson
    find_orjson = True
except ImportError:
    find_orjson = False

from fastapi_structlog.custom_processors import (
    ORJSONRenderer,
    add_app_context,
    drop_color_message_key,
    sanitize_authorization_token,
)

_queue = SimpleQueue[logging.LogRecord]()
T_ = TypeVar('T_', bound=SQLModel)
T2_ = TypeVar('T2_', bound=logging.Handler)


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: Optional[TracebackType],
) -> None:
    """Register any uncaught exception.

    The `KeyboardInterrupt` will remain intact so that users can
    stop using Ctrl+C.
    """
    log = structlog.get_logger()
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log.error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))


def set_handle_exception() -> None:
    """Set logging exception handler."""
    sys.excepthook = handle_exception


def configure_processor(
    *,
    json_logs: bool = True,
    event_key: str = 'event',
    traceback_as_str: bool = True,
) -> list[Processor]:
    """Configure the processor chain.

    Args:
        json_logs (bool, optional): Logging in json format. Defaults to True.
        event_key (str, optional): The key of the main message. Defaults to "event".
        traceback_as_str (bool, optional): Log exceptions in string format. Defaults to True.

    Returns:
        list[Processor]: Processor chain.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        sanitize_authorization_token,
        add_app_context(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.EventRenamer(to=event_key),
    ]
    if find_structlog_sentry:
        shared_processors.insert(3, SentryProcessor(event_level=logging.ERROR))

    if json_logs and not traceback_as_str:
        shared_processors.append(structlog.processors.dict_tracebacks)
    if json_logs and traceback_as_str:
        shared_processors.append(structlog.processors.format_exc_info)

    return shared_processors


def configure_renderer(
    *,
    json_logs: bool = True,
    event_key: str = 'event',
    in_file: bool = False,
) -> list[Processor]:
    """Configure the render processor.

    Args:
        json_logs (bool, optional): Logging in json format. Defaults to True.
        event_key (str, optional): The key of the main message. Defaults to "event".
        in_file (bool, optional): Output to a file. Defaults to False.

    Returns:
        list[Processor]: Render processor chain.
    """
    log_renderer: list[Processor]
    if json_logs and find_orjson:
        log_renderer = [
            ORJSONRenderer(serializer=orjson.dumps, option=orjson.OPT_NON_STR_KEYS),
        ]
    elif json_logs:
        log_renderer = [structlog.processors.JSONRenderer()]
    elif in_file:
        log_renderer = [
            structlog.dev.ConsoleRenderer(
                colors=False,
                event_key=event_key,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]
    else:
        log_renderer = [structlog.dev.ConsoleRenderer(event_key=event_key)]

    return log_renderer


def configure_formatter(
    processors: list[Processor],
    renderer: list[Processor],
) -> structlog.stdlib.ProcessorFormatter:
    """Configure a handler for formatting log entries.

    Args:
        processors (list[Processor]): Processor chain.
        renderer (list[Processor]): Render processor chain.

    Returns:
        structlog.stdlib.ProcessorFormatter: A handler for formatting log entries.
    """
    return structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within
        # structlog.
        foreign_pre_chain=processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *renderer,
        ],
    )


def configure_structlog(logger: str, processors: list[Processor]) -> None:
    """Configure Structlog.

    Args:
        logger (str): The name of the logger.
        processors (list[Processor]): Processor chain.
    """
    log = logging.getLogger(logger)
    shared_processors_configure = processors.copy()
    shared_processors_configure.append(
        # Prepare event dict for `ProcessorFormatter`.
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    )

    structlog.configure(
        processors=shared_processors_configure,
        logger_factory=LoggerFactory(logger=log),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def base_formatter(settings: LogSettings) -> structlog.stdlib.ProcessorFormatter:
    """Create a basic formatter based on the configuration."""
    shared_processors = configure_processor(
        json_logs=settings.json_logs,
        event_key=settings.event_key,
        traceback_as_str=settings.traceback_as_str,
    )

    log_renderer = configure_renderer(
        json_logs=settings.json_logs,
        event_key=settings.event_key,
    )
    return configure_formatter(shared_processors, log_renderer)


class HandlerFactory(Generic[T2_]):
    """An abstract factory for creating logging handlers."""
    def __init__(
        self,
        handler: type[T2_],
        formatter: Optional[structlog.stdlib.ProcessorFormatter] = None,
    ) -> None:
        self.handler = handler
        self.formatter = formatter

    @abstractmethod
    def create_handler(self, **kwargs: Any) -> T2_:  # noqa: ANN401
        """Create a handler."""

    def set_formatter(self, handler: T2_) -> None:
        """Add a formatter."""
        if self.formatter:
            handler.setFormatter(self.formatter)

    def create(self, **kwargs: Any) -> T2_:  # noqa: ANN401, D102
        handler = self.create_handler(**kwargs)
        self.set_formatter(handler)
        return handler


class SyslogHandlerFactory(HandlerFactory[logging.handlers.SysLogHandler]):
    """Factory of handlers for syslog."""
    def __init__(
        self,
        formatter: Optional[structlog.stdlib.ProcessorFormatter] = None,
    ) -> None:
        super().__init__(logging.handlers.SysLogHandler, formatter)

    def create_handler(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **_: Any,  # noqa: ANN401
    ) -> logging.handlers.SysLogHandler:
        """Create a handler."""
        if host is None:
            msg = 'No host is specified to use syslog'
            raise ValueError(msg)
        if port is None:
            msg = 'The port for using syslog is not specified'
            raise ValueError(msg)

        try:
            handler = logging.handlers.SysLogHandler(address=(host, port))
        except OSError as error:
            msg = f'Syslog connection error {host}:{port}'
            raise SysLogConnectionError(msg) from error

        return handler


class StreamHandlerFactory(HandlerFactory['logging.StreamHandler[TextIO]']):
    """Factory of handlers for console."""
    def __init__(
        self,
        formatter: Optional[structlog.stdlib.ProcessorFormatter] = None,
    ) -> None:
        super().__init__(logging.StreamHandler, formatter)

    def create_handler(
        self,
        **_: Any,  # noqa: ANN401
    ) -> 'logging.StreamHandler[TextIO]':
        """Create a handler."""
        return logging.StreamHandler()


class FileHandlerFactory(HandlerFactory[TimedRotatingFileHandler]):
    """Factory of handlers for file."""
    def __init__(
        self,
        formatter: Optional[structlog.stdlib.ProcessorFormatter] = None,
    ) -> None:
        if formatter is None:
            shared_processors = configure_processor(
                json_logs=False,
                event_key='message',
                traceback_as_str=False,
            )
            log_renderer = configure_renderer(
                json_logs=False,
                event_key='message',
                in_file=True,
            )
            formatter = configure_formatter(shared_processors, log_renderer)
        super().__init__(TimedRotatingFileHandler, formatter)

    def create_handler(
        self,
        filename: Optional[str] = None,
        when: Literal['S', 'M', 'H', 'D', 'W'] = 'D',
        backup_count: int = 1,
        **_: Any,  # noqa: ANN401
    ) -> TimedRotatingFileHandler:
        """Create a handler."""
        if not filename:
            msg = 'The path to the log file is not specified when using the file logging type'
            raise ValueError(msg)

        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        return TimedRotatingFileHandler(
            filename=path, when=when, backupCount=backup_count,
        )


class DatabaseHandlerFactory(HandlerFactory[DatabaseHandler[T_]]):
    """Factory of handlers for database."""
    def __init__(
        self,
        formatter: Optional[structlog.stdlib.ProcessorFormatter] = None,
    ) -> None:
        if formatter is None:
            shared_processors = configure_processor(
                json_logs=True,
                event_key='message',
                traceback_as_str=True,
            )
            log_renderer = configure_renderer(
                json_logs=True,
                event_key='message',
            )
            formatter = configure_formatter(shared_processors, log_renderer)
        super().__init__(DatabaseHandler, formatter)

    def create_handler(
        self,
        model: Optional[type[T_]] = None,
        db_url: Optional[Union[str, URL]] = None,
        **_: Any,  # noqa: ANN401
    ) -> DatabaseHandler[T_]:
        """Create a handler."""
        if model is None:
            msg = 'The model argument is required when logging into a database'
            raise ValueError(msg)
        if db_url is None:
            msg = 'The session_maker argument is required when logging into a database'
            raise ValueError(msg)

        return DatabaseHandler(db_url=db_url, model=model)


class LoggerConfigurator:
    """Logger configuration class."""
    def __init__(self, settings: LogSettings) -> None:
        self.settings = settings

        self.handlers: dict[LogType, logging.Handler] = {}

    def add_handler(self, type_: LogType, handler: logging.Handler) -> None:
        """Add a handler."""
        self.handlers[type_] = handler

    def add_base_handler(self) -> None:
        """Add a basic handler for the console."""
        self.add_handler(
            LogType.CONSOLE,
            StreamHandlerFactory(formatter=self.base_formatter).create(),
        )

    @property
    def processors(self) -> list[Processor]:
        """Basic processors."""
        return configure_processor(
            json_logs=self.settings.json_logs,
            event_key=self.settings.event_key,
            traceback_as_str=self.settings.traceback_as_str,
        )

    @property
    def base_formatter(self) -> structlog.stdlib.ProcessorFormatter:
        """Create a basic formatter based on the configuration."""
        return base_formatter(self.settings)

    def setup(self) -> Optional[logging.handlers.QueueListener]:
        """Configure the logger."""
        configure_structlog(self.settings.logger, self.processors)

        root_logger = logging.getLogger()

        handlers: list[logging.Handler] = []

        for type_ in LogType:
            if type_ in self.settings.types:
                handler_ = self.handlers.get(type_)
                if not handler_:
                    msg = f'The handler for {type_.value} not registered'
                    raise ValueError(msg)

                if type_ is LogType.CONSOLE:
                    root_logger.addHandler(handler_)
                else:
                    handlers.append(handler_)

        if handlers:
            queue_handler = QueueHandler(_queue)
            root_logger.addHandler(queue_handler)

        root_logger.setLevel(self.settings.log_level if not self.settings.debug else logging.DEBUG)

        for _log in logging.root.manager.loggerDict:
            logging.getLogger(_log).handlers.clear()

        set_handle_exception()

        if handlers:
            return logging.handlers.QueueListener(_queue, *handlers)

        return None
