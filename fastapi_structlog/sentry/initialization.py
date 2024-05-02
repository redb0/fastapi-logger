"""Sentry configuration module."""
import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from .settings import SentrySettings


def init_sentry(
    *,
    env_prefix: str | None = None,
    release: str | None = None,
    app_slug: str | None = None,
    version: str | None = None,
    service_integration: Integration | None = None,
) -> None:
    """Initializing Sentry with settings from the .env file or environment variables.

    Release is formed either from the explicitly passed `release` argument or in
    the 'app_slug@version` format.

    Args:
        env_prefix (str | None, optional): Sentry Settings prefix. Defaults to None.
        release (str | None): Release. Defaults to None.
        app_slug (str | None): Name of the application. Defaults to None.
        version (str | None): Version. Defaults to None.
        service_integration (Integration | None): Integration for inter-service
            interaction. Defaults to None.

    """
    settings_ = SentrySettings(_env_prefix=env_prefix)
    if settings_.dsn:
        setup_sentry(
            settings_,
            release=release or f"{app_slug}@{version}",
            service_integration=service_integration,
        )


def setup_sentry(
    settings_: SentrySettings,
    *,
    release: str | None = None,
    service_integration: Integration | None = None,
) -> None:
    """Configuration of Sentry settings.

    Args:
        settings_ (SentrySettings): Sentry settings.
        release (str | None, optional): Release version. Defaults to None.
        service_integration (Integration | None): Integration for inter-service
            interaction. Defaults to None.
    """
    integrations: list[Integration] = [
        StarletteIntegration(transaction_style="url"),
        FastApiIntegration(transaction_style="url"),
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
        **settings_.model_dump(exclude={"dsn"}, by_alias=True),
    )
