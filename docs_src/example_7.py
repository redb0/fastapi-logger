import structlog

from fastapi_structlog.sentry import SentrySettings, setup_sentry

logger = structlog.get_logger()

class MySettings(SentrySettings):
    debug: bool = False


def main() -> None:
    settings = MySettings()

    setup_sentry(settings)

    logger.info(f'{settings.dsn = }')
    logger.info(f'{settings.debug = }')


if __name__ == '__main__':
    main()
