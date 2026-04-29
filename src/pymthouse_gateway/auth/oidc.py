"""OIDC discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ..errors import OIDCDiscoveryError
from ._http import build_oauth2_client


@dataclass(frozen=True)
class OIDCConfig:
    """Parsed OIDC discovery document (only the fields the SDK needs)."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    device_authorization_endpoint: str | None = None
    end_session_endpoint: str | None = None


def _ensure_https_for_display(url: str) -> str:
    """Upgrade http to https for non-localhost URLs so users open secure pages."""
    if not url or not url.startswith("http://"):
        return url
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            return url
        return url.replace("http://", "https://", 1)
    except Exception:
        return url


def discover(
    base_url: str,
    *,
    timeout: float = 15.0,
    user_agent: str | None = None,
    allow_insecure_tls: bool = False,
) -> OIDCConfig:
    """Fetch and parse the OIDC discovery document.

    ``base_url`` should be the OIDC *issuer* base (e.g.
    ``https://pymthouse.example.com/api/v1/oidc``). Discovery is read from
    ``{base_url}/.well-known/openid-configuration``.
    """
    url = base_url.rstrip("/") + "/.well-known/openid-configuration"
    with build_oauth2_client(
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    ) as client:
        resp = client.request("GET", url, withhold_token=True)
    if resp.status_code >= 400:
        raise OIDCDiscoveryError(
            f"HTTP {resp.status_code} from {url}: {resp.text[:512]}"
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise OIDCDiscoveryError(f"Discovery document at {url} is not JSON") from exc

    try:
        return OIDCConfig(
            issuer=data["issuer"],
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            userinfo_endpoint=data.get("userinfo_endpoint", ""),
            jwks_uri=data.get("jwks_uri", ""),
            device_authorization_endpoint=data.get("device_authorization_endpoint"),
            end_session_endpoint=data.get("end_session_endpoint"),
        )
    except KeyError as exc:
        raise OIDCDiscoveryError(
            f"Discovery document at {url} missing required field {exc!s}"
        ) from exc


def probe_oidc(
    base_url: str,
    *,
    timeout: float = 5.0,
    user_agent: str | None = None,
    allow_insecure_tls: bool = False,
) -> bool:
    """Return True if ``base_url`` exposes an OIDC discovery endpoint."""
    url = base_url.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with build_oauth2_client(
            timeout=timeout,
            user_agent=user_agent,
            allow_insecure_tls=allow_insecure_tls,
        ) as client:
            resp = client.request("GET", url, withhold_token=True)
            return resp.status_code == 200
    except Exception:
        return False
