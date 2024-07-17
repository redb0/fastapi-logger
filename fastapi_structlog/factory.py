"""Logger factory module."""
from logging import Logger, getLogger
from typing import Any, Optional, Union

import structlog

from fastapi_structlog.types_ import typed_property


class LoggerFactory(structlog.stdlib.LoggerFactory):
    """Logger factory."""
    def __init__(self,
                 logger: Union[Logger, str],
                 ignore_frame_names: Optional[list[str]] = None) -> None:
        self.logger = logger
        super().__init__(ignore_frame_names=ignore_frame_names)

    @typed_property[Logger, Union[Logger, str]]
    def logger(self) -> Logger:
        """Get logger."""
        return self._logger

    @logger.setter
    def set_value(self, logger: Union[Logger, str]) -> None:
        """Set logger.

        `logging.getLogger` will be used if a string is passed.
        """
        if isinstance(logger, Logger):
            self._logger = logger
        else:
            self._logger = getLogger(logger)

    def __call__(self, *args: Any) -> Logger:  # noqa: D102, ANN401
        if args:
            return self._logger.getChild(args[0])
        return self._logger
