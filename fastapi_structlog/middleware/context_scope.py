"""Module for declaring the current context."""

from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any, Optional

Scope = MutableMapping[str, Any]

current_scope: ContextVar[Optional[Scope]] = ContextVar('current_scope')
