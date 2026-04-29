from __future__ import annotations

import pytest

from pymthouse_gateway import (
    PymthouseGatewayError,
    build_session_token,
    parse_session_token,
)


def test_round_trip_full_token():
    token = build_session_token(
        orchestrators=["https://orch1.example", "https://orch2.example"],
        signer="https://signer.example",
        signer_headers={"Authorization": "Bearer abc"},
        discovery="https://discover.example",
        discovery_headers={"x-key": "v"},
        billing="https://pymthouse.example",
    )
    parsed = parse_session_token(token)
    assert parsed["orchestrators"] == ["https://orch1.example", "https://orch2.example"]
    assert parsed["signer"] == "https://signer.example"
    assert parsed["signer_headers"] == {"Authorization": "Bearer abc"}
    assert parsed["discovery"] == "https://discover.example"
    assert parsed["discovery_headers"] == {"x-key": "v"}
    assert parsed["billing"] == "https://pymthouse.example"


def test_empty_token():
    token = build_session_token()
    parsed = parse_session_token(token)
    assert parsed == {
        "orchestrators": None,
        "signer": None,
        "discovery": None,
        "signer_headers": None,
        "discovery_headers": None,
        "billing": None,
    }


def test_rejects_non_base64():
    with pytest.raises(PymthouseGatewayError):
        parse_session_token("not-base64!!!")


def test_rejects_non_object_payload():
    import base64
    import json

    bad = base64.b64encode(json.dumps([1, 2]).encode()).decode()
    with pytest.raises(PymthouseGatewayError):
        parse_session_token(bad)


def test_rejects_blank_orchestrator():
    import base64
    import json

    payload = json.dumps({"orchestrators": ["valid", "  "]}).encode()
    bad = base64.b64encode(payload).decode()
    with pytest.raises(PymthouseGatewayError):
        parse_session_token(bad)
