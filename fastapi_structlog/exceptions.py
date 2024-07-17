"""Exception module."""

class LogError(Exception):
    """Basic exception."""

class SysLogConnectionError(LogError):
    """Syslog connection error."""
