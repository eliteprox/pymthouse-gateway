from __future__ import annotations

import pytest

from pymthouse_gateway import (
    BrandingConfig,
    ConfigError,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
)


def test_config_derives_paths():
    config = PymthouseGatewayConfig(base_url="https://pymthouse.example.com")
    assert config.issuer_url() == "https://pymthouse.example.com/api/v1/oidc"
    assert config.signer_url() == "https://pymthouse.example.com/api/signer"
    assert (
        config.discovery_url()
        == "https://pymthouse.example.com/api/signer/discover-orchestrators"
    )


def test_config_strips_trailing_slash():
    config = PymthouseGatewayConfig(base_url="https://pymthouse.example.com/")
    assert config.issuer_url() == "https://pymthouse.example.com/api/v1/oidc"


def test_client_requires_base_url():
    with pytest.raises(ConfigError):
        PymthouseGatewayClient(config=PymthouseGatewayConfig(base_url=""))


def test_branding_user_agent_defaults():
    branding = BrandingConfig(product_name="PymtHouse")
    assert branding.effective_user_agent("0.1.0") == "pymthouse-gateway/0.1.0"


def test_branding_user_agent_custom_product():
    branding = BrandingConfig(
        product_name="Acme",
        extra_user_agent_tokens=("acme/1.0",),
    )
    assert "Acme" in branding.effective_user_agent("0.1.0")
    assert "acme/1.0" in branding.effective_user_agent("0.1.0")


def test_branding_user_agent_explicit_override():
    branding = BrandingConfig(user_agent="custom-ua/9")
    assert branding.effective_user_agent("0.1.0") == "custom-ua/9"
