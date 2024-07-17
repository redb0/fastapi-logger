"""Access logging middleware module."""
import http
import logging
import os
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from enum import IntEnum
from math import log2
from typing import Any, Optional, Protocol, TypedDict, cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

import structlog
from typing_extensions import Self

from fastapi_structlog.middleware.utils import get_client_addr, get_path_with_query_string

from .context_scope import current_scope


class HTTPStatusProtocol(Protocol):
    """Protocol for listing HTTP statuses."""
    value: int
    name: str
    phrase: str
    description: str


class HTTPStatusBase(IntEnum):
    """Base enumeration class for HTTP statuses.

    Allows you to set two additional parameters.
    """
    def __new__(cls, value: int, *_: tuple[Any, ...]) -> Self:  # noqa: D102
        obj = int.__new__(cls, value)
        obj._value_ = value
        return obj

    def __init__(self, value: int, phrase: str='', description: str='') -> None:
        super().__init__()
        self._value_ = value

        self.phrase = phrase
        self.description = description

    @classmethod
    def get(cls, value: int) -> Self:
        """Get status by code.

        Args:
            value (int): HTTP code.

        """
        return cast(Self, cls._value2member_map_[value])

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if value is not None and not isinstance(value, int):
            msg = f'The argument must be None or of type int, but not {type(value)}'
            raise ValueError(msg)
        value = value if value is not None else 0
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._name_ = 'UNKNOWN'
        obj.phrase = '-'
        obj.description = ''
        return obj


def extend_enum_http_status(
    parent_enum: Iterable[HTTPStatusProtocol],
) -> Callable[[type[HTTPStatusBase]], HTTPStatusBase]:
    """Decorator of the enumeration extension."""

    def wrapper(extended_enum: type[HTTPStatusBase]) -> HTTPStatusBase:
        """Combine two enumerations into one."""
        joined: dict[str, tuple[int, str, str]] = {}
        for item in parent_enum:
            joined[item.name] = item.value, item.phrase, item.description
        # expression has type "HTTPStatusBase", variable has type "HTTPStatusProtocol"
        for item in extended_enum:  # type: ignore[assignment]
            joined[item.name] = item.value, item.phrase, item.description
        return HTTPStatusBase(extended_enum.__name__, joined)  # type: ignore[arg-type]

    return wrapper


@extend_enum_http_status(http.HTTPStatus)
class HTTPStatus(HTTPStatusBase):
    """Enum HTTP statuses.

    Additionally, the 499 status is added when the client closes the connection.
    """
    CLIENT_CLOSED_REQUEST = (
        499,
        'Client Closed Request',
        'Used when the client has closed the request before the server could send a response.',
    )


class AccessInfo(TypedDict, total=False):
    """Access information with timestamps."""
    response: Message
    start_time: float
    end_time: float


class AccessLogMiddleware:
    """Access logging middleware."""
    DEFAULT_FORMAT = '%(client_addr)s - "%(request_line)s" %(status_code)s %(L)ss - "%(a)s"'

    def __init__(  # noqa: PLR0913
        self,
        app: ASGIApp,
        format_: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        methods: Optional[Sequence[str]] = None,
        session_key: Optional[str] = 'session',
    ) -> None:
        self.app = app
        self.format = format_ or self.DEFAULT_FORMAT
        self.logger = logger or logging.getLogger('api.access')
        self.methods = set(methods) if methods else None
        self.session_key = session_key

        if not structlog.is_configured():
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

            self.logger.warning(
                '\x1b[33;20mStructlog is not configured! A standard logger will be used!\x1b[0m',
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # noqa: D102
        current_scope.set(scope)

        skipped_method = self.methods and scope['method'] not in self.methods
        if scope['type'] != 'http' or skipped_method:  # pragma: no cover
            await self.app(scope, receive, send)
            return

        info = AccessInfo(response={})

        async def send_wrapper(response: Message) -> None:
            if response['type'] == 'http.response.start':
                info['response'] = response

            await send(response)

        request = {
            'method': scope['method'],
            'path': get_path_with_query_string(scope),
            'client_addr': get_client_addr(scope),
        }
        structlog.contextvars.bind_contextvars(request=request)

        if self.session_key and self.session_key in scope:
            structlog.contextvars.bind_contextvars(session=scope.get(self.session_key))

        try:
            info['start_time'] = time.perf_counter()
            await self.app(scope, receive, send_wrapper)
            return
        except Exception as exc:
            info['response']['status'] = 500
            raise exc
        finally:
            info['end_time'] = time.perf_counter()

            response = {
                'status_code': info['response']['status'],
            }
            structlog.contextvars.bind_contextvars(response=response)

            self.logger.info(self.format, AccessLogAtoms(scope=scope, info=info))


class AccessLogAtoms(dict[str, Any]):
    """Logging attributes."""
    def __init__(self, scope: Scope, info: AccessInfo) -> None:
        for name, value in scope['headers']:
            self[f"{{{name.decode('latin1').lower()}}}i"] = value.decode('latin1')
        for name, value in info['response'].get('headers', []):
            name_str = name.decode('latin1').lower()
            if name_str == 'content-length':
                value_ = self._human_size(int(value.decode('latin1')))
            else:
                value_ = value
            self[f'{{{name_str}}}o'] = value_.decode('latin1')

        protocol = f"HTTP/{scope['http_version']}"

        status = cast(int, info['response'].get('status', 0))
        status_phrase = HTTPStatus.get(status).phrase

        path = scope['root_path'] + scope['path']
        full_path = get_path_with_query_string(scope)
        request_line = f"{scope['method']} {path} {protocol}"
        full_request_line = f"{scope['method']} {full_path} {protocol}"

        request_time = info['end_time'] - info['start_time']
        client_addr = get_client_addr(scope)
        self.update(
            {
                'h': client_addr,
                'client_addr': client_addr,
                'l': '-',
                'u': '-',  # Not available on ASGI.
                't': time.strftime('[%d/%b/%Y:%H:%M:%S %z]'),
                'r': request_line,
                'request_line': full_request_line,
                'R': full_request_line,
                'm': scope['method'],
                'U': scope['path'],
                'q': scope['query_string'].decode(),
                'H': protocol,
                's': status,
                'status_code': f'{status} {status_phrase}',
                'st': status_phrase,
                'B': self['{Content-Length}o'],
                'b': self['{Content-Length}o'],
                'f': self['{Referer}i'],
                'a': self['{User-Agent}i'],
                'T': int(request_time),
                'M': int(request_time * 1_000),
                'D': int(request_time * 1_000_000),
                'L': f'{request_time:.6f}',
                'p': f'<{os.getpid()}>',
                'session': scope.get('session'),
            },
        )

    def __getitem__(self, key: str) -> Any:  # noqa: D105, ANN401
        try:
            if key.startswith('{'):
                return super().__getitem__(key.lower())
            return super().__getitem__(key)
        except KeyError:
            return '-'

    @staticmethod
    def _human_size(size: int, decimal_places: int=2) -> bytes:
        _suffixes = ('bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
        order = int(log2(size) / 10) if size else 0
        human_size = f'{size / (1 << (order * 10)):.{decimal_places}f} {_suffixes[order]}'
        return human_size.encode()
