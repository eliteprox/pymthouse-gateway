"""Top-level configuration objects for the SDK."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_SCOPES = "openid profile sign:job"


@dataclass(frozen=True)
class PymthouseGatewayConfig:
    """High-level SDK configuration.

    ``base_url`` is the PymtHouse origin (e.g. ``https://pymthouse.example.com``).
    The SDK derives the OIDC issuer (``{base_url}/api/v1/oidc``), signer URL
    (``{base_url}/api/signer``), and discovery URL
    (``{base_url}/api/signer/discover-orchestrators``) from it.
    """

    base_url: str
    client_id: str = "pymthouse-sdk"
    scopes: str = DEFAULT_SCOPES
    headless: bool = True
    """When True, default to RFC 8628 device flow; when False use browser PKCE."""

    cache_namespace: str | None = None
    """If set, overrides the cache namespace from BrandingConfig."""

    timeout: float = 15.0
    """HTTP timeout (seconds) for OIDC and PymtHouse Builder calls."""

    allow_insecure_tls: bool = False
    """Disable TLS verification (development only). Mirrors LIVEPEER_ALLOW_INSECURE_TLS."""

    issuer_path: str = "/api/v1/oidc"
    signer_path: str = "/api/signer"
    discovery_path: str = "/api/signer/discover-orchestrators"

    def issuer_url(self) -> str:
        return self.base_url.rstrip("/") + self.issuer_path

    def signer_url(self) -> str:
        return self.base_url.rstrip("/") + self.signer_path

    def discovery_url(self) -> str:
        return self.base_url.rstrip("/") + self.discovery_path


@dataclass(frozen=True)
class LivepeerRoutingConfig:
    """Direct overrides for orchestrator selection / signer routing.

    Any non-None field bypasses PymtHouse-derived defaults. Useful for tests
    and integrators that already know which orchestrator/signer to call.
    """

    orchestrators: Sequence[str] | None = None
    discovery_url: str | None = None
    signer_url: str | None = None
    signer_headers: dict[str, str] | None = None
    discovery_headers: dict[str, str] | None = None
    use_tofu: bool = True
    timeout: float = 5.0
