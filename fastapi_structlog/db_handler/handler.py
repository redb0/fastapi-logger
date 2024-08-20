"""Module of the logging handler to the database."""

import asyncio
import datetime
import logging
import logging.handlers
from abc import abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, Generic, Optional, TypeVar, Union, cast

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_structlog.utils import annotated_last, find_by_value

try:
    import structlog
except ImportError:
    structlog = None  # type: ignore[assignment]

T_ = TypeVar('T_', bound=SQLModel)
_CONTEXT_KEY = 'structlog_context'


class QueueHandler(logging.handlers.QueueHandler):
    """Handler for sending a message to the queue.

    Removes the conversion to a string in the base class.
    """
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        if structlog is not None:
            context = structlog.contextvars.get_contextvars()
        try:
            if isinstance(record.msg, dict):
                record.msg[_CONTEXT_KEY] = context
            if isinstance(record.args, dict):
                record.args[_CONTEXT_KEY] = context
            self.enqueue(record)
        except Exception:  # noqa: BLE001
            self.handleError(record)


class BaseDatabaseHandler(logging.Handler, Generic[T_]):
    """Base class of the handler for logging into the database."""
    def __init__(  # noqa: PLR0913
        self,
        db_url: Union[str, URL],
        model: type[T_],
        level: Union[int, str] = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        key_aliases: Optional[dict[str, list[str]]] = None,
        search_paths: Optional[dict[str, list[str]]] = None,
        key_handlers: Optional[dict[str, Callable[[Any, logging.LogRecord], Any]]] = None,
        available_loggers: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(level)
        self.model = model

        self.db_url = make_url(db_url)
        self._loop = loop

        self.key_aliases = key_aliases or {}
        self.search_paths = search_paths or {}
        self.key_handlers = key_handlers or {}
        self.available_loggers = set(available_loggers) if available_loggers else set()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Get the event loop.

        Necessary for asynchronous execution.
        """
        if self._loop is not None and self._loop.is_running():
            return self._loop
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
        return self._loop

    @abstractmethod
    def construct_message(self, record: logging.LogRecord) -> T_:
        """Generate data to save to the database from LogRecord."""
        raise NotImplementedError

    def emit(self, record: logging.LogRecord) -> None:
        """Save the message in the database."""
        if self.available_loggers and record.name not in self.available_loggers:
            return

        message = self.construct_message(record)
        if self.db_url.drivername == 'postgresql+asyncpg':
            self.loop.run_until_complete(self._async_emit(message))
        else:
            self._sync_emit(message)

    async def _async_emit(self, record: T_) -> None:
        _engine = create_async_engine(self.db_url, poolclass=NullPool)
        async with AsyncSession(bind=_engine) as session:
            session.add(record)
            await session.commit()

    def _sync_emit(self, record: T_) -> None:
        _engine = create_engine(self.db_url, poolclass=NullPool)
        with Session(bind=_engine) as session:
            session.add(record)
            session.commit()


class DatabaseHandler(BaseDatabaseHandler[T_]):
    """Handler for logging into the database."""

    @staticmethod
    def sources(record: logging.LogRecord) -> list[dict[str, Any]]:
        """Sources for searching for values."""
        sources: list[dict[str, Any]] = []
        if isinstance(record.msg, dict):
            sources.append(record.msg)
            sources.append(cast(dict[str, Any], record.msg.get('request', {})))
        if isinstance(record.args, dict):
            sources.append(record.args)
        return sources

    def base_keys(self, record: logging.LogRecord) -> dict[str, Any]:
        """Basic keys and log values."""
        return {
            'timestamp': datetime.datetime.fromtimestamp(record.created),
            'logger': record.name,
            'level': record.levelname,
            'message': self.format(record),
        }

    def get_key_aliases(self) -> dict[str, list[str]]:
        """Basic aliases for log keys."""
        key_aliases = {
            'request_id': ['{x-request-id}i'],
            'method': ['m'],
            'protocol': ['H'],
            'path': ['full_path'],
            'client_address': ['client_addr'],
            'status_code': ['s'],
        }
        key_aliases.update(self.key_aliases)
        return key_aliases

    def construct_message(self, record: logging.LogRecord) -> T_:  # noqa: PLR0912, C901
        """Generate data to save to the database from LogRecord."""
        base = self.base_keys(record)
        key_aliases = self.get_key_aliases()

        sources = self.sources(record)

        data = {}
        for name, field in self.model.model_fields.items():
            # field is FieldInfo from sqlmodel
            if field.primary_key is True:  # type: ignore[attr-defined]
                continue

            if name in base:
                data[name] = base[name]
                continue

            for source in sources:
                value = None
                if name in source:
                    value = source[name]
                elif name in key_aliases:
                    aliases = key_aliases[name]
                    for alias in aliases:
                        if alias in source:
                            value = source[alias]
                            break
                elif name in self.search_paths:
                    data_ = source
                    for key, is_last in annotated_last(self.search_paths[name]):
                        if not is_last:
                            data_ = cast(dict[str, Any], data_.get(key, {}))
                        else:
                            value = data_.get(key)

                if value is not None:
                    data[name] = value
                    break

            if name not in data:
                data[name] = None

            if name in self.key_handlers:
                data[name] = self.key_handlers[name](data[name], record)

        for _ in find_by_value(
            data,
            key=r'(?P<param>password=)(?P<val>.*?)(?P<end>(?:\s|&|$))',
            replace=r'\g<param>*****\g<end>',
        ):
            pass

        return self.model.model_validate(data)
