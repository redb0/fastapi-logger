"""Module for declaring the current context."""

from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

Scope = MutableMapping[str, Any]

current_scope: ContextVar[Scope | None] = ContextVar("current_scope")
