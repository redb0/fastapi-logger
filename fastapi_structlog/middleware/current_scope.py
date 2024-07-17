"""Middleware module for adding the current context."""
from contextvars import ContextVar
from typing import Optional

from starlette.types import ASGIApp, Receive, Scope, Send

from .context_scope import current_scope


class CurrentScopeSetMiddleware:
    """Middleware that adds the current context."""
    def __init__(
        self,
        app: ASGIApp,
        scope_context_var: ContextVar[Optional[Scope]] = current_scope,
    ) -> None:
        self.app = app
        self._scope_context_var: ContextVar[Optional[Scope]] = scope_context_var

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # noqa: D102
        self._scope_context_var.set(scope)

        await self.app(scope, receive, send)
