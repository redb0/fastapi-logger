from fastapi import FastAPI
from starlette.middleware import Middleware

import structlog
import uvicorn
from asgi_correlation_id.middleware import CorrelationIdMiddleware

from fastapi_structlog import BaseSettingsModel, LogSettings, setup_logger
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)
from fastapi_structlog.sentry import SentrySettings, setup_sentry


class Settings(BaseSettingsModel):
    log: LogSettings
    sentry: SentrySettings


settings = Settings()
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


@app.get('/info')
def info() -> str:
    logger.info('Call API info')
    return 'OK'


def main() -> None:
    setup_logger(settings.log)
    setup_sentry(settings.sentry, release='example_api@1.0')

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
