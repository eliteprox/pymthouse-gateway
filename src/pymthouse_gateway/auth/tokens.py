"""Token sources: cache + refresh + interactive login orchestration."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from ..branding import BrandingConfig
from ..errors import TokenRefreshError
from ._http import build_oauth2_client
from .browser import login
from .cache import (
    DEFAULT_NAMESPACE,
    clear_cached_token,
    load_cached_token,
    save_cached_token,
)
from .device import device_login
from .oidc import discover

_LOG = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "pymthouse-sdk"
DEFAULT_SCOPES = "openid profile sign:job"


def _normalize_token_expiry(token: dict[str, Any]) -> None:
    """Set absolute ``expires_at`` from ``expires_in`` when the server omits it.

    OAuth token responses include ``expires_in`` (seconds of validity from
    issuance). Persist an absolute epoch in ``expires_at`` so expiry checks do
    not treat ``expires_in`` as a live countdown (which would be wrong after
    the first comparison).

    Mutates ``token`` in place. Leaves ``expires_at`` unchanged when already set.
    """
    if token.get("expires_at") is not None:
        return
    expires_in = token.get("expires_in")
    if expires_in is None:
        return
    try:
        token["expires_at"] = time.time() + float(expires_in)
    except (TypeError, ValueError):
        return


def _is_expired(token: dict[str, Any], skew: int = 30) -> bool:
    """Return True if the access token should be considered expired."""
    expires_at = token.get("expires_at")
    if expires_at is None:
        return True
    try:
        return float(expires_at) <= time.time() + float(skew)
    except (TypeError, ValueError):
        return True


def refresh(
    base_url: str,
    refresh_token: str,
    *,
    client_id: str = DEFAULT_CLIENT_ID,
    timeout: float = 15.0,
    user_agent: Optional[str] = None,
    allow_insecure_tls: bool = False,
) -> dict[str, Any]:
    """Exchange a refresh token for a new token set."""
    config = discover(
        base_url,
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    )
    with build_oauth2_client(
        client_id=client_id,
        token={"refresh_token": refresh_token},
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    ) as client:
        try:
            tokens = client.refresh_token(
                config.token_endpoint,
                refresh_token=refresh_token,
                resource=config.issuer,
            )
            _normalize_token_expiry(tokens)
            return tokens
        except Exception as exc:
            raise TokenRefreshError(f"Refresh failed: {exc}") from exc


def ensure_valid_token(
    base_url: str,
    *,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
    headless: bool = True,
    branding: Optional[BrandingConfig] = None,
    namespace: str = DEFAULT_NAMESPACE,
    on_device_auth: Optional[Callable[[str, str, int], None]] = None,
    timeout: float = 15.0,
    user_agent: Optional[str] = None,
    allow_insecure_tls: bool = False,
) -> dict[str, Any]:
    """Return a valid token, using cache → refresh → interactive login.

    ``headless=True`` (default) uses the device flow; ``headless=False`` uses
    the loopback browser PKCE flow. ``PYMTHOUSE_GATEWAY_AUTH_BROWSER`` (or
    legacy ``LIVEPEER_AUTH_BROWSER``) flips ``headless=True`` to
    ``headless=False`` so CLI users can still force the browser flow.
    """
    if headless and os.environ.get(
        "PYMTHOUSE_GATEWAY_AUTH_BROWSER",
        os.environ.get("LIVEPEER_AUTH_BROWSER", ""),
    ).lower() in ("1", "true", "yes"):
        headless = False

    cached = load_cached_token(
        base_url,
        namespace=namespace,
        client_id=client_id,
        scopes=scopes,
    )

    if cached and not _is_expired(cached):
        _LOG.debug("Using cached OIDC token for %s", base_url)
        return cached

    if cached and cached.get("refresh_token"):
        _LOG.info("Access token expired, refreshing")
        try:
            tokens = refresh(
                base_url,
                cached["refresh_token"],
                client_id=client_id,
                timeout=timeout,
                user_agent=user_agent,
                allow_insecure_tls=allow_insecure_tls,
            )
            _normalize_token_expiry(tokens)
            save_cached_token(
                base_url,
                tokens,
                namespace=namespace,
                client_id=client_id,
                scopes=scopes,
            )
            return tokens
        except TokenRefreshError:
            _LOG.warning(
                "Token refresh failed for %s; falling back to interactive login",
                base_url,
            )
            clear_cached_token(
                base_url,
                namespace=namespace,
                client_id=client_id,
                scopes=scopes,
            )

    if headless:
        tokens = device_login(
            base_url,
            client_id=client_id,
            scopes=scopes,
            branding=branding,
            on_device_auth=on_device_auth,
            timeout=timeout,
            user_agent=user_agent,
            allow_insecure_tls=allow_insecure_tls,
        )
    else:
        tokens = login(
            base_url,
            client_id=client_id,
            scopes=scopes,
            branding=branding,
            timeout=timeout,
            user_agent=user_agent,
            allow_insecure_tls=allow_insecure_tls,
        )
    _normalize_token_expiry(tokens)
    save_cached_token(
        base_url,
        tokens,
        namespace=namespace,
        client_id=client_id,
        scopes=scopes,
    )
    return tokens


@runtime_checkable
class TokenSource(Protocol):
    """A pluggable provider of OAuth access tokens."""

    def get_access_token(self) -> str: ...

    def authorization_header(self) -> dict[str, str]: ...


@dataclass
class StaticTokenSource:
    """A token source that always returns a fixed access token."""

    access_token: str

    def get_access_token(self) -> str:
        return self.access_token

    def authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


@dataclass
class CachedOidcTokenSource:
    """A token source that triggers ``ensure_valid_token`` on demand."""

    base_url: str
    client_id: str = DEFAULT_CLIENT_ID
    scopes: str = DEFAULT_SCOPES
    headless: bool = True
    branding: Optional[BrandingConfig] = None
    namespace: str = DEFAULT_NAMESPACE
    on_device_auth: Optional[Callable[[str, str, int], None]] = None
    timeout: float = 15.0
    user_agent: Optional[str] = None
    allow_insecure_tls: bool = False
    _last_token: Optional[dict[str, Any]] = field(default=None, init=False, repr=False)

    def _refresh(self) -> dict[str, Any]:
        token = ensure_valid_token(
            self.base_url,
            client_id=self.client_id,
            scopes=self.scopes,
            headless=self.headless,
            branding=self.branding,
            namespace=self.namespace,
            on_device_auth=self.on_device_auth,
            timeout=self.timeout,
            user_agent=self.user_agent,
            allow_insecure_tls=self.allow_insecure_tls,
        )
        self._last_token = token
        return token

    def get_access_token(self) -> str:
        if self._last_token is None or _is_expired(self._last_token):
            self._refresh()
        assert self._last_token is not None
        return self._last_token["access_token"]

    def authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}
