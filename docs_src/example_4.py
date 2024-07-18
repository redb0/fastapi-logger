from pathlib import Path
from typing import Any

import structlog
from pydantic import ValidationInfo, field_validator
from pydantic_settings import SettingsConfigDict

from fastapi_structlog import BaseSettingsModel, LogSettings, setup_logger

logger = structlog.get_logger()

class Settings(BaseSettingsModel):
    project_name: str = 'Example API'
    app_slug: str = 'example-api'
    api_prefix: str = ''
    root_path: str = ''
    openapi_url: str = '/openapi.json'

    debug: bool = False

    log: LogSettings

    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        secrets_dir='/run/secrets' if Path('/run/secrets').exists() else None,
    )

    @field_validator('log', mode='before')
    @classmethod
    def _log_validator(
        cls, log_settings: dict[str, Any], info: ValidationInfo,
    ) -> dict[str, Any]:
        if info.data.get('debug') is True:
            log_settings['level'] = 'DEBUG'
        return log_settings


def main() -> None:
    settings = Settings()

    setup_logger(settings.log)

    logger.info(f'{settings.log.logger = }')
    logger.info(f'{settings.log.log_level = }')
    logger.info(f'{settings.log.json_logs = }')


if __name__ == '__main__':
    main()
