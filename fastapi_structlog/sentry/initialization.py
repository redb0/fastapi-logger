"""Sentry configuration module."""
import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .settings import SentrySettings


def setup_sentry(
    settings_: SentrySettings,
    *,
    release: Optional[str] = None,
    app_slug: Optional[str] = None,
    version: Optional[str] = None,
    service_integration: Optional[Integration] = None,
) -> None:
    """Configuration of Sentry settings.

    Args:
        settings_ (SentrySettings): Sentry settings.
        release (Optional[str]): Release version. Defaults to None.
        app_slug (Optional[str]): Name of the application. Defaults to None.
        version (Optional[str]): Version. Defaults to None.
        service_integration (Optional[Integration]): Integration for inter-service
            interaction. Defaults to None.
    """
    release = release or f'{app_slug}@{version}'

    if not settings_.dsn:
        logger = logging.getLogger('init_sentry')
        logger.warning(
            '\x1b[33;20mSentry is not configured! Missing DSN!\x1b[0m',
        )
        return

    integrations: list[Integration] = [
        StarletteIntegration(transaction_style='url'),
        FastApiIntegration(transaction_style='url'),
    ]
    if settings_.log_integration:
        integrations.append(LoggingIntegration(
            event_level=settings_.log_integration_event_level,
            level=settings_.log_integration_level,
        ))
    if settings_.sql_integration:
        integrations.append(SqlalchemyIntegration())

    if service_integration:
        integrations.append(service_integration)

    sentry_sdk.init(
        dsn=str(settings_.dsn) if settings_.dsn else None,
        release=release,
        integrations=integrations,
        **settings_.model_dump(exclude={'dsn'}, by_alias=True),
    )
