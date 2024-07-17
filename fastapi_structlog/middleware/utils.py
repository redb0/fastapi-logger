"""Auxiliary functions module."""

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
    path_with_query_string = quote(scope['path'])
    if raw_query_string := scope['query_string']:
        query_string = raw_query_string.decode('ascii')
        path_with_query_string = f'{path_with_query_string}?{query_string}'
    return path_with_query_string
