from typing import Any

from fastapi import FastAPI

import structlog
import uvicorn

from fastapi_structlog import BaseSettingsModel, LogSettings, setup_logger


class Settings(BaseSettingsModel):
    log: LogSettings


settings = Settings()
logger = structlog.get_logger()

app = FastAPI(title='Example API', version='1.0.0')

@app.get('/')
def warning() -> str:
    logger.warning('Test warning', test='TEST')
    return 'OK'


@app.get('/info')
def info() -> str:
    logger.info('Call API info')
    return 'OK'


@app.get('/uncaught-error')
def uncaught_error() -> None:
    msg = 'Unhandled exception'
    raise ValueError(msg)


@app.get('/error')
def error() -> str:
    my_dict: dict[Any, Any] = {}
    try:
        my_dict['key']
    except KeyError:
        logger.exception('Getting the missing key')
    return 'OK'


def main() -> None:
    setup_logger(settings.log)

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
