"""Logging library.

Provides a wrapper over the structlog for additional doping in json format,
as well as output of standard logs to the console, configuration via .env
files via pydantic.
"""

from .log import setup_logging
from .settings import LogSettings


def init_logger(env_prefix: str | None = None) -> None:
    """Initialize the logger with the configuration from the .env file or environment variables.

    Args:
        env_prefix (str | None, optional): Prefix of the logger settings. Defaults to None.

    """
    settings_ = LogSettings(_env_prefix=env_prefix)

    setup_logging(
        logger=settings_.logger,
        log_level=settings_.log_level,
        json_logs=settings_.json_logs,
        traceback_as_str=settings_.traceback_as_str,
        filename=settings_.filename,
        when=settings_.when,
        backup_count=settings_.backup_count,
        debug=settings_.debug,
        event_key=settings_.event_key,
    )


__all__ = (
    "setup_logging",
    "LogSettings",
    "init_logger",
)
