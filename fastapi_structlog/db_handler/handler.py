"""Module of the logging handler to the database."""

import asyncio
import datetime
import logging
import logging.handlers
from abc import abstractmethod
from typing import Any, Generic, Optional, TypeVar, Union, cast

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

T_ = TypeVar('T_', bound=SQLModel)


class QueueHandler(logging.handlers.QueueHandler):
    """Handler for sending a message to the queue.

    Removes the conversion to a string in the base class.
    """
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            self.enqueue(record)
        except Exception:  # noqa: BLE001
            self.handleError(record)


class BaseDatabaseHandler(logging.Handler, Generic[T_]):
    """Base class of the handler for logging into the database."""
    def __init__(
        self,
        db_url: Union[str, URL],
        model: type[T_],
        level: Union[int, str] = 0,
        loop: Optional[asyncio.AbstractEventLoop]=None,
    ) -> None:
        super().__init__(level)
        self.model = model

        self.db_url = make_url(db_url)
        self._loop = loop

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
        message = self.construct_message(record)
        if self.db_url.drivername == 'postgresql+asyncpg':
            self.loop.run_until_complete(self._async_emit(message))
        else:
            self._sync_emit(message)

    async def _async_emit(self, record: T_) -> None:
        _engine = create_async_engine(self.db_url)
        async with AsyncSession(bind=_engine) as session:
            session.add(record)
            await session.commit()

    def _sync_emit(self, record: T_) -> None:
        _engine = create_engine(self.db_url)
        with Session(bind=_engine) as session:
            session.add(record)
            session.commit()


class DatabaseHandler(BaseDatabaseHandler[T_]):
    """Handler for logging into the database."""
    def construct_message(self, record: logging.LogRecord) -> T_:
        """Generate data to save to the database from LogRecord."""
        message: dict[str, Any] = {
            'request_id': None,
            'client_address': None,
            'timestamp': datetime.datetime.fromtimestamp(record.created),
            'session': None,
            'method': None,
            'path': None,
            'status_code': None,
            'message': self.format(record),
        }

        if isinstance(record.msg, dict):
            message['request_id'] = record.msg.get('request_id')
            message['session'] = record.msg.get('session')
            request = cast(dict[str, Any], record.msg.get('request', {}))

            message['method'] = request.get('method')
            message['path'] = request.get('path')
            message['client_address'] = request.get('client_addr')

        if isinstance(record.args, dict):
            message['request_id'] = message['request_id'] or record.args.get('{x-request-id}i')
            method = record.args.get('m')
            protocol = record.args.get('H')
            full_path = cast(str, record.args.get('request_line'))
            if method and protocol and full_path:
                full_path = full_path.lstrip(method).rstrip(protocol).strip()
            message['method'] = message['method'] or method
            message['path'] = message['path'] or full_path
            message['client_address'] = message['client_address'] or record.args.get('client_addr')
            message['status_code'] = record.args.get('s')
            message['session'] = record.args.get('session')

        if message['session'] and '__metadata__' in message['session']:
            message['session'].pop('__metadata__')

        return self.model.model_validate(message)
