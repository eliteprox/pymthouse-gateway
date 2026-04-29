"""Internal helpers for building authlib OAuth2 clients."""

from __future__ import annotations

import os
from typing import Any


def oauth_verify(allow_insecure_tls: bool = False) -> bool:
    """Return whether to verify TLS for OAuth requests.

    Honours the legacy ``LIVEPEER_ALLOW_INSECURE_TLS`` env var as well as the
    PymtHouse-specific ``PYMTHOUSE_GATEWAY_ALLOW_INSECURE_TLS`` for parity.
    """
    if allow_insecure_tls:
        return False
    if os.environ.get("PYMTHOUSE_GATEWAY_ALLOW_INSECURE_TLS"):
        return False
    if os.environ.get("LIVEPEER_ALLOW_INSECURE_TLS"):
        return False
    return True


def build_oauth2_client(
    *,
    client_id: str | None = None,
    scopes: str | None = None,
    redirect_uri: str | None = None,
    token: dict[str, Any] | None = None,
    code_challenge_method: str | None = None,
    timeout: float = 15.0,
    user_agent: str | None = None,
    allow_insecure_tls: bool = False,
):
    """Construct an authlib ``OAuth2Client`` with sensible defaults.

    Imported lazily so that simply importing ``pymthouse_gateway`` does not
    require ``authlib`` if the consumer never authenticates.
    """
    from authlib.integrations.httpx_client import OAuth2Client

    headers = {"Accept": "application/json"}
    if user_agent:
        headers["User-Agent"] = user_agent
    return OAuth2Client(
        client_id=client_id,
        scope=scopes,
        redirect_uri=redirect_uri,
        token=token,
        token_endpoint_auth_method="none",
        code_challenge_method=code_challenge_method,
        timeout=timeout,
        verify=oauth_verify(allow_insecure_tls),
        headers=headers,
    )
