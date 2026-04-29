"""OIDC authentication for the PymtHouse Python SDK.

Ports OAuth device login, browser PKCE login, refresh, token cache, and logout
from ``eliteprox/python-gateway`` (commit ``abd57bed13e5d6b7a01a3573ebae8cf2a7c84242``)
into a brandable PymtHouse-specific module.
"""

from __future__ import annotations

from .browser import login
from .cache import (
    clear_all_cached_tokens,
    clear_cached_token,
    load_cached_token,
    save_cached_token,
)
from .device import device_login
from .logout import logout, logout_all
from .oidc import OIDCConfig, discover, probe_oidc
from .third_party import ThirdPartyInitiateRequest, parse_third_party_initiate_url
from .tokens import (
    CachedOidcTokenSource,
    StaticTokenSource,
    TokenSource,
    ensure_valid_token,
    refresh,
)

__all__ = [
    "CachedOidcTokenSource",
    "OIDCConfig",
    "StaticTokenSource",
    "ThirdPartyInitiateRequest",
    "TokenSource",
    "clear_all_cached_tokens",
    "clear_cached_token",
    "device_login",
    "discover",
    "ensure_valid_token",
    "load_cached_token",
    "login",
    "logout",
    "logout_all",
    "parse_third_party_initiate_url",
    "probe_oidc",
    "refresh",
    "save_cached_token",
]
