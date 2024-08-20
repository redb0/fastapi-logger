from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from starlette.middleware import Middleware

import structlog
import uvicorn
from asgi_correlation_id.middleware import CorrelationIdMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field
from starsessions import InMemoryStore, SessionAutoloadMiddleware, SessionMiddleware

from fastapi_structlog import BaseSettingsModel, LogSettings, setup_logger
from fastapi_structlog.db_handler import LogModel
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)


class Settings(BaseSettingsModel):
    log: LogSettings


settings = Settings()


class LogWithUser(LogModel, table=True):
    user_id: Optional[int] = Field(
        default=None,
        title='User ID',
    )
    login: Optional[str] = Field(
        default=None,
        title='User login',
    )
    login_type: Optional[str] = Field(
        default=None,
        title='User login type',
    )
    name: Optional[str] = Field(
        default=None,
        title='User name',
    )
    item_id: Optional[int] = Field(
        default=None,
        title='item_id',
    )


engine = create_async_engine(settings.log.db.make_url())

queue_listener = setup_logger(
    settings.log,
    model=LogWithUser,
    db_url=settings.log.db.make_url(),
    search_paths = {
        'user_id': ['session', 'user_id'],
        'login': ['session', 'username'],
        'login_type': ['session', 'login_type'],
        'name': ['session', 'name'],
        'item_id': ['structlog_context', 'path_params', 'item_id'],
    },
    available_loggers=['api.access'],
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(LogWithUser.metadata.create_all)

    if queue_listener:
        queue_listener.start()

    yield

    if queue_listener:
        queue_listener.stop()


app = FastAPI(
    title='Example API',
    version='1.0.0',
    middleware=[
        Middleware(
            SessionMiddleware,
            store=InMemoryStore(),
            rolling=True,
            lifetime=10 * 60,
            cookie_https_only=False,
        ),
        Middleware(SessionAutoloadMiddleware),

        Middleware(CurrentScopeSetMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(StructlogMiddleware),
        Middleware(AccessLogMiddleware),
    ],
    lifespan=lifespan,
)


@app.get('/')
async def test(request: Request) -> str:
    logger.info('Test API')

    request.session['name'] = 'Foo Bar'
    request.session['username'] = 'foo_bar'

    return 'OK'


@app.post('/foo/{item_id}')
def foo(
    item_id: int,
    item: dict[str, str],
    bar: str = Query(),
    password: str = Query(),
    baz: str = Query(),
) -> dict[str, str]:
    return item | {'item_id': str(item_id), 'bar': bar, 'password': password, 'baz': baz}


def main() -> None:
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
        reload=False,
        access_log=False,
    )


if __name__ == '__main__':
    main()
