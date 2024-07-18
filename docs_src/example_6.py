import asyncio

from fastapi import FastAPI
from starlette.middleware import Middleware

import httpx
import sentry_sdk
import structlog
import uvicorn
from asgi_correlation_id.middleware import CorrelationIdMiddleware

from fastapi_structlog import init_logger
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)
from fastapi_structlog.sentry import init_sentry

logger = structlog.get_logger()

app = FastAPI(
    title='Example API',
    version='1.0.0',
    middleware=[
        Middleware(CurrentScopeSetMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(StructlogMiddleware),
        Middleware(AccessLogMiddleware),
    ],
)


@sentry_sdk.trace
async def call_api() -> int:
    url = 'https://www.python.org/'
    logger.info('Getting data', url=url)
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    await asyncio.sleep(10)
    logger.info('Data collection is completed', status_code=r.status_code)
    return r.status_code


@sentry_sdk.trace
async def serialize(res: int) -> int:
    logger.info('Data serialization')
    await asyncio.sleep(5)
    logger.info('Data serialization is complete')
    return res


@app.get('/')
async def test_sentry() -> str:
    logger.info('Test Sentry')
    res = await call_api()
    await serialize(res)
    logger.info('Test Sentry is complete')
    return 'Test Sentry'


def main() -> None:
    init_logger(env_prefix='LOG__')
    init_sentry(release='example_api@1.0')

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
        reload=False,
        access_log=False,
        log_config={
            'version': 1,
            'disable_existing_loggers': False,
        },
    )


if __name__ == '__main__':
    main()
