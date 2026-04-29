from __future__ import annotations

from pymthouse_gateway import (
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
    StaticTokenSource,
)
from pymthouse_gateway.auth.cache import load_cached_token, save_cached_token


def _make_client(**kwargs):
    return PymthouseGatewayClient(
        config=PymthouseGatewayConfig(base_url="https://pymthouse.example.com"),
        token_source=StaticTokenSource(access_token="static"),
        **kwargs,
    )


def test_logout_clears_for_issuer():
    client = _make_client()
    issuer = client.config.issuer_url()
    save_cached_token(
        issuer,
        {"access_token": "abc"},
        client_id=client.config.client_id,
        scopes=client.config.scopes,
    )
    client.logout()
    assert (
        load_cached_token(
            issuer,
            client_id=client.config.client_id,
            scopes=client.config.scopes,
        )
        is None
    )


def test_logout_all_returns_count():
    client = _make_client()
    save_cached_token(
        "https://a.example/oidc",
        {"access_token": "a"},
        client_id=client.config.client_id,
        scopes=client.config.scopes,
    )
    save_cached_token(
        "https://b.example/oidc",
        {"access_token": "b"},
        client_id=client.config.client_id,
        scopes=client.config.scopes,
    )
    cleared = client.logout_all()
    assert cleared == 2
