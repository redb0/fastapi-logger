"""Log handler module."""

from collections.abc import Collection
from logging import Logger
from typing import Optional, Union

import structlog
from structlog.processors import CallsiteParameter
from structlog.typing import EventDict, ProcessorReturnValue, WrappedLogger


def drop_color_message_key(
    _: WrappedLogger,
    __: str,
    event_dict: EventDict,
) -> ProcessorReturnValue:
    """Remove the `color_message` key from the event list, if it exists.

    This eliminates the need for double registration of the uvicorn
    message in the additional `color_message` field.
    """
    _ = event_dict.pop('color_message', None)
    return event_dict


def sanitize_authorization_token(
    _: WrappedLogger,
    __: str,
    event_dict: EventDict,
) -> ProcessorReturnValue:
    """Delete the authorization token."""
    if headers := event_dict.get('http', {}).get('headers'):
        _ = headers.pop('authorization', None)
    return event_dict


def decode_bytes(
    _: WrappedLogger,
    __: str,
    event_dict: bytes,
) -> ProcessorReturnValue:
    """Decoding the event dictionary as bytes.

    It is necessary when using `orjson` as a serializer in
    `structlog.processors.JSONRenderer'.
    """
    return event_dict.decode()


class CallsiteParameterAdderInKey(structlog.processors.CallsiteParameterAdder):
    """Wrapper for :class:`structlog.processors.CallsiteParameterAdder`.

    Adds the `key` parameter, which can be used to set the key for
    logging parameters. An additional nesting level for this key
    will be created in `event_dict`.
    """
    def __init__(
        self,
        parameters: Collection[CallsiteParameter] = set(CallsiteParameter),
        additional_ignores: Optional[list[str]] = None,
        *,
        key: Optional[str] = None,
    ) -> None:
        self.key = key
        additional_ignores = additional_ignores or []
        super().__init__(parameters, [*additional_ignores, __name__.split('.')[0]])

    def __call__(self, logger: Logger, name: str, event_dict: EventDict) -> EventDict:  # noqa: D102
        event_dict = super().__call__(logger, name, event_dict)
        if self.key:
            event_dict[self.key] = {}
            for parameter, _ in self._active_handlers:
                if parameter.value in event_dict:
                    event_dict[self.key][parameter.value] = event_dict.pop(parameter.value)
        return event_dict


def add_app_context() -> structlog.processors.CallsiteParameterAdder:
    """Add the module name, line number, and function name to the `source` key."""
    return CallsiteParameterAdderInKey(
        {
            structlog.processors.CallsiteParameter.MODULE,
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.LINENO,
        },
        key='source',
    )


class ORJSONRenderer(structlog.processors.JSONRenderer):
    """Wrapper over JSONRenderer to use orjson.

    Decodes a string of bytes received after serialization.
    """
    def __call__(  # noqa: D102
        self, _: WrappedLogger, __: str, event_dict: EventDict,
    ) -> Union[str, bytes]:
        result = self._dumps(event_dict, **self._dumps_kw)
        if isinstance(result, bytes):
            return result.decode()
        return result
