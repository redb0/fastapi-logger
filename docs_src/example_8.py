from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware import Middleware

import structlog
import uvicorn
from asgi_correlation_id.middleware import CorrelationIdMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from starsessions import InMemoryStore, SessionAutoloadMiddleware, SessionMiddleware

from fastapi_structlog import BaseSettingsModel, LogSettings, setup_logger
from fastapi_structlog.db_handler import LogModel
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)

DB_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/postgres_test'


class Settings(BaseSettingsModel):
    log: LogSettings


settings = Settings()


class Log(LogModel, table=True):
    """Log table."""


engine = create_async_engine(DB_URL)

queue_listener = setup_logger(
    settings.log,
    model=Log,
    db_url=DB_URL,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Log.metadata.create_all)

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
