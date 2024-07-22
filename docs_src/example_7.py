from typing import Any

import structlog
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_structlog.sentry import SentrySettings, setup_sentry
from fastapi_structlog.utils import check_sub_settings_unset

logger = structlog.get_logger()

class MySettings(SentrySettings):
    debug: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_ignore_empty=True,
        env_nested_delimiter='__',
        extra='ignore',
    )
    sentry: MySettings

    @model_validator(mode='before')
    @classmethod
    def _check_sub_settings_unset(cls, values: dict[str, Any]) -> dict[str, Any]:
        return check_sub_settings_unset(cls.model_fields, values)


def main() -> None:
    settings = Settings()

    setup_sentry(settings.sentry, release='example_api@1.0')

    logger.info(f'{settings.sentry.dsn = }')
    logger.info(f'{settings.sentry.debug = }')


if __name__ == '__main__':
    main()
