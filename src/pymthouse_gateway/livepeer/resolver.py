"""Resolve PymtHouse base URL → signer / discovery / headers.

This is the SDK-side equivalent of the OAuth branch's ``_resolve_billing``
helper but reusable across LV2V, BYOC, and the BYOC process/SSE wrappers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..auth.oidc import probe_oidc
from ..auth.tokens import TokenSource
from ..config import PymthouseGatewayConfig
from ..errors import ResolverError

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class LivepeerResolution:
    signer_url: str | None
    discovery_url: str | None
    signer_headers: dict[str, str] | None
    discovery_headers: dict[str, str] | None


def resolve_livepeer_routing(
    config: PymthouseGatewayConfig | None,
    token_source: TokenSource | None,
    *,
    signer_url: str | None = None,
    signer_headers: dict[str, str] | None = None,
    discovery_url: str | None = None,
    discovery_headers: dict[str, str] | None = None,
    user_agent: str | None = None,
) -> LivepeerResolution:
    """Compute signer/discovery routing using PymtHouse defaults + overrides.

    Resolution order, mirroring the OAuth branch:

    1. If ``signer_url`` is explicitly provided, do not touch it.
    2. Else, if ``config`` is provided, probe its OIDC issuer:

       * If OIDC is reachable, derive ``signer_url`` and ``discovery_url`` from
         ``config`` and add a Bearer header from ``token_source``.
       * If not, treat ``config.base_url`` as a direct signer base URL.

    3. If a discovery URL is set but ``discovery_headers`` is None and signer
       headers exist, copy signer headers into discovery (Bearer flows through
       discovery GETs).
    """
    resolved_signer_url = signer_url
    resolved_signer_headers = signer_headers
    resolved_discovery_url = discovery_url
    resolved_discovery_headers = discovery_headers

    if not resolved_signer_url and config is not None:
        issuer = config.issuer_url()
        if probe_oidc(
            issuer,
            timeout=config.timeout,
            user_agent=user_agent,
            allow_insecure_tls=config.allow_insecure_tls,
        ):
            if token_source is None:
                raise ResolverError(
                    "OIDC discovery succeeded but no token source was provided; "
                    "pass a TokenSource (or call client.login()) before starting jobs."
                )
            resolved_signer_url = config.signer_url()
            resolved_signer_headers = dict(token_source.authorization_header())
            if resolved_discovery_url is None:
                resolved_discovery_url = config.discovery_url()
        else:
            _LOG.info(
                "No OIDC discovery at %s; treating PymtHouse base URL as a "
                "direct signer base.",
                issuer,
            )
            resolved_signer_url = config.base_url.rstrip("/")

    if (
        resolved_discovery_url is not None
        and resolved_discovery_headers is None
        and resolved_signer_headers is not None
    ):
        resolved_discovery_headers = dict(resolved_signer_headers)

    return LivepeerResolution(
        signer_url=resolved_signer_url,
        discovery_url=resolved_discovery_url,
        signer_headers=resolved_signer_headers,
        discovery_headers=resolved_discovery_headers,
    )
