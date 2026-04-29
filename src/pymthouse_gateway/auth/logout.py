"""Logout helpers — clear cached tokens by base URL or wipe all."""

from __future__ import annotations

from .cache import (
    DEFAULT_CLIENT_ID,
    DEFAULT_NAMESPACE,
    DEFAULT_SCOPES,
    clear_all_cached_tokens,
    clear_cached_token,
)


def logout(
    base_url: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> None:
    """Remove the cached token for ``base_url`` (no-op if absent)."""
    clear_cached_token(
        base_url,
        namespace=namespace,
        client_id=client_id,
        scopes=scopes,
    )


def logout_all(namespace: str = DEFAULT_NAMESPACE) -> int:
    """Remove every cached token in ``namespace`` and return the count."""
    return clear_all_cached_tokens(namespace=namespace)
