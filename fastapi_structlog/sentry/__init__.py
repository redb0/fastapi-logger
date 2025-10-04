"""Sentry package.

Provides Sentry configuration functions for quick integration to the application.
"""

from .initialization import setup_sentry
from .settings import Environment, SentrySettings

__all__ = (
    'Environment',
    'SentrySettings',
    'setup_sentry',
)
