"""Auxiliary functions module."""

from typing import Any, Optional
from urllib.parse import quote

from starlette.types import Scope


def get_client_addr(scope: Scope) -> str:
    """Get the client's address.

    Args:
        scope (Scope): Current context.

    Returns:
        str: Client's address in the IP:PORT format.
    """
    client = scope.get('client')
    if not client:
        return ''
    ip, port = client
    return f'{ip}:{port}'


def get_path_with_query_string(scope: Scope) -> str:
    """Get the URL with the substitution of query parameters.

    Args:
        scope (Scope): Current context.

    Returns:
        str: URL with query parameters
    """
    if 'path' not in scope:
        return '-'
    path_with_query_string = quote(scope['path'])
    if raw_query_string := scope['query_string']:
        query_string = raw_query_string.decode('ascii')
        path_with_query_string = f'{path_with_query_string}?{query_string}'
    return path_with_query_string


def get_user_agent(scope: Scope) -> str:
    """Get the user agent.

    Args:
        scope (Scope): Current context.

    Returns:
        str: User-agent or '-' if it is not presented or for exceptions.
    """
    if 'headers' not in scope:
        return '-'
    headers: list[tuple[bytes, bytes]] = scope.get('headers')  # type: ignore[assignment]
    if not headers:
        return '-'
    user_agents = tuple(hdr[1] for hdr in headers if hdr[0] == b'user-agent')
    try:
        # If has multiple User-Agent, then we take the last
        return user_agents[-1].decode('latin1')
    except Exception:  # noqa: BLE001
        return '-'


def find_path_params(
    scope: Scope,
    _: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Find path parameters."""
    return scope.get('path_params')


def find_api_source(
    scope: Scope,
    _: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Find location of endpoint."""
    if 'endpoint' in scope and hasattr(scope['endpoint'], '__globals__'):
        return {
            'package': scope['endpoint'].__globals__.get('__package__'),
            'file': scope['endpoint'].__globals__.get('__file__'),
            'function': getattr(scope['endpoint'], '__name__', None),
        }
    return None


def find_request_info(
    scope: Scope,
    _: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Find information about request."""
    return {
        'method': scope.get('method'),
        'path': get_path_with_query_string(scope),
        'client_addr': get_client_addr(scope),
        'user_agent': get_user_agent(scope),
    }


def find_response_info(
    _: Scope,
    info: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Find information about response."""
    if info:
        return {
            'status_code': info['response']['status'],
        }
    return None
