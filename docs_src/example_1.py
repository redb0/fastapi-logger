import os

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_structlog import LogSettings, setup_logger

os.environ['LOG__LOGGER'] = 'test-log-lib'
# Writing to the console, disabling json mode
os.environ['LOG__JSON_LOGS'] = 'False'
# Activate debugging mode
os.environ['LOG__DEBUG'] = 'True'
os.environ['LOG__TYPES'] = '["console"]'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_ignore_empty=True,
        env_nested_delimiter='__',
        extra='ignore',
    )
    log: LogSettings


settings = Settings()


setup_logger(settings.log)

log = structlog.get_logger()

def main() -> None:
    try:
        print(f'{1 / 0 = }')
    except ZeroDivisionError:
        log.exception('Error')


if __name__ == '__main__':
    main()
