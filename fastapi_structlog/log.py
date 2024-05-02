"""Logger configuration module via structlog."""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Literal

import structlog
from structlog.types import Processor

from .factory import LoggerFactory

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

from .custom_processors import (
    ORJSONRenderer,
    add_app_context,
    drop_color_message_key,
    sanitize_authorization_token,
)


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Register any uncaught exception.

    The `KeyboardInterrupt` will remain intact so that users can
    stop using Ctrl+C.
    """
    log = structlog.get_logger()
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def set_handle_exception() -> None:
    """Set logging exception handler."""
    sys.excepthook = handle_exception


def configure_processor(
    *,
    json_logs: bool = True,
    event_key: str = "event",
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
        structlog.processors.TimeStamper(fmt="iso"),
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
    event_key: str = "event",
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


def setup_logging(  # noqa: PLR0913
    *,
    logger: str,
    log_level: str | int = "INFO",
    json_logs: bool = True,
    traceback_as_str: bool = True,
    filename: Path | str | None = None,
    when: Literal["S", "M", "H", "D", "W"] = "D",
    backup_count: int = 1,
    debug: bool = False,
    event_key: str = "event",
) -> None:
    """Configuration logger via structlog.

    Args:
        logger (str): The name of the logger.
        log_level (str | int, optional): Logging level
            (see https://docs.python.org/3/library/logging.html#logging-levels).
            Defaults to `"INFO"`.
        json_logs (bool, optional): The flag that activates logging in json format,
            by default ``True``. If the value is set to ``False``,
            the logs will be adapted to `stdout`.
        traceback_as_str (bool, optional): Logging of the traceback in string form,
            by default ``True``. If the value is set to ``False``, the traceback
            will be converted to json format. It only works when the
            ``json_logs`` parameter is active.
        filename (Path | str | None, optional): The name of the file. It is not set by default.
        when (Literal["S", "M", "H", "D", "W"], optional): The interval of writing to the file.
            See :class:`logging.handlers.TimedRotatingFileHandler`. Defaults to `"D"`.
        backup_count (int, optional):The number of saved files, by default 1.
            See :class:`logging.handlers.TimedRotatingFileHandler`.
        debug (bool, optional): DEBUG mode, default is ``False``. If the value is
            set to ``True``, the DEBUG logging level will be set forcibly.
        event_key (str, optional): New name for the key ``event``.
            See :class:`structlog.processors.EventRenamer`. Defaults to `"event"`.
    """
    shared_processors = configure_processor(
        json_logs=json_logs,
        event_key=event_key,
        traceback_as_str=traceback_as_str,
    )

    configure_structlog(logger, shared_processors)

    log_renderer = configure_renderer(json_logs=json_logs, event_key=event_key)
    formatter = configure_formatter(shared_processors, log_renderer)

    root_logger = logging.getLogger()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    if filename:
        filename = Path(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)

        log_renderer = configure_renderer(
            json_logs=json_logs,
            event_key=event_key,
            in_file=True,
        )
        formatter = configure_formatter(shared_processors, log_renderer)

        timed_rotating_file_handler = TimedRotatingFileHandler(
            filename=filename, when=when, backupCount=backup_count,
        )
        timed_rotating_file_handler.setFormatter(formatter)
        root_logger.addHandler(timed_rotating_file_handler)

    root_logger.setLevel(log_level if not debug else logging.DEBUG)

    for _log in logging.root.manager.loggerDict:
        # Clear the log handlers for all loggers
        # so the messages are caught by our root logger and formatted correctly by structlog
        logging.getLogger(_log).handlers.clear()

    set_handle_exception()
