"""Configuration Module."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class LogSettings(BaseSettings):
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

    logger: str = "default"
    log_level: str = "INFO"
    json_logs: bool = True
    traceback_as_str: bool = True
    filename: Path | str | None = None
    when: Literal["S", "M", "H", "D", "W"] = "D"
    backup_count: int = 1
    debug: bool = False
    event_key: str = "message"

    _env_prefix: str | None = None
