from __future__ import annotations

from unittest.mock import patch

import pytest

from pymthouse_gateway import (
    PymthouseGatewayConfig,
    ResolverError,
    StaticTokenSource,
    resolve_livepeer_routing,
)


def _config() -> PymthouseGatewayConfig:
    return PymthouseGatewayConfig(base_url="https://pymthouse.example.com")


def test_resolves_oidc_to_signer_and_discovery():
    config = _config()
    source = StaticTokenSource(access_token="bearer-abc")
    with patch("pymthouse_gateway.livepeer.resolver.probe_oidc", return_value=True):
        resolution = resolve_livepeer_routing(config, source)
    assert resolution.signer_url == config.signer_url()
    assert resolution.discovery_url == config.discovery_url()
    assert resolution.signer_headers == {"Authorization": "Bearer bearer-abc"}
    # Discovery inherits signer headers when not explicitly set.
    assert resolution.discovery_headers == {"Authorization": "Bearer bearer-abc"}


def test_non_oidc_base_treated_as_direct_signer():
    config = _config()
    source = StaticTokenSource(access_token="bearer-abc")
    with patch("pymthouse_gateway.livepeer.resolver.probe_oidc", return_value=False):
        resolution = resolve_livepeer_routing(config, source)
    assert resolution.signer_url == config.base_url.rstrip("/")
    assert resolution.discovery_url is None
    assert resolution.signer_headers is None


def test_oidc_without_token_source_raises():
    config = _config()
    with patch("pymthouse_gateway.livepeer.resolver.probe_oidc", return_value=True):
        with pytest.raises(ResolverError):
            resolve_livepeer_routing(config, None)


def test_explicit_signer_url_bypasses_probe():
    resolution = resolve_livepeer_routing(
        _config(),
        None,
        signer_url="https://override.signer/api",
    )
    assert resolution.signer_url == "https://override.signer/api"
    # No discovery copy because no signer headers were set.
    assert resolution.discovery_headers is None


def test_discovery_headers_preserved_when_explicit():
    resolution = resolve_livepeer_routing(
        None,
        None,
        signer_url="https://signer",
        signer_headers={"Authorization": "Bearer x"},
        discovery_url="https://disc",
        discovery_headers={"x-foo": "y"},
    )
    assert resolution.discovery_headers == {"x-foo": "y"}
