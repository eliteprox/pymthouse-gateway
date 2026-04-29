from __future__ import annotations

import pytest

from pymthouse_gateway import AuthError, parse_third_party_initiate_url


def test_parses_iss_and_target_link_uri():
    url = (
        "https://app.example/login?iss=https%3A%2F%2Fpymthouse.example"
        "&login_hint=alice%40example.com"
        "&target_link_uri=https%3A%2F%2Fapp.example%2Fpost"
    )
    req = parse_third_party_initiate_url(url)
    assert req.iss == "https://pymthouse.example"
    assert req.login_hint == "alice@example.com"
    assert req.target_link_uri == "https://app.example/post"


def test_missing_iss_raises():
    with pytest.raises(AuthError):
        parse_third_party_initiate_url("https://app.example/login?foo=bar")


def test_expected_issuer_mismatch_raises():
    url = "https://app.example/login?iss=https%3A%2F%2Fpymthouse.example"
    with pytest.raises(AuthError):
        parse_third_party_initiate_url(url, expected_issuer="https://other.example")


def test_expected_issuer_match_succeeds():
    url = "https://app.example/login?iss=https%3A%2F%2Fpymthouse.example"
    req = parse_third_party_initiate_url(url, expected_issuer="https://pymthouse.example")
    assert req.iss == "https://pymthouse.example"
