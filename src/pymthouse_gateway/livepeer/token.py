"""PymtHouse-flavored gateway token helpers (extends upstream parse_token).

Upstream ``livepeer_gateway.parse_token`` understands ``orchestrators``,
``signer``, ``signer_headers``, ``discovery``, ``discovery_headers``. We add
support for an optional ``billing`` field (mirroring ``feat/byoc-oauth2``)
without forking the upstream module.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from ..errors import PymthouseGatewayError


def parse_session_token(token: str) -> dict[str, Any]:
    """Parse a base64-encoded JSON session token.

    Returns a dict with optional keys:

    - ``orchestrators`` (list[str] | None)
    - ``signer`` (str | None)
    - ``signer_headers`` (dict[str, str] | None)
    - ``discovery`` (str | None)
    - ``discovery_headers`` (dict[str, str] | None)
    - ``billing`` (str | None)
    """
    try:
        decoded = base64.b64decode(token, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PymthouseGatewayError(
            "Invalid token: expected base64-encoded JSON"
        ) from exc

    try:
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PymthouseGatewayError(
            "Invalid token: expected UTF-8 JSON payload"
        ) from exc

    if not isinstance(payload, dict):
        raise PymthouseGatewayError("Invalid token: payload must be a JSON object")

    def _str_or_none(key: str) -> str | None:
        v = payload.get(key)
        if v is None:
            return None
        if not isinstance(v, str):
            raise PymthouseGatewayError(f"Invalid token: {key} must be a string")
        return v

    def _is_str_dict(v: object) -> bool:
        return isinstance(v, dict) and all(
            isinstance(k, str) and isinstance(val, str) for k, val in v.items()
        )

    signer_headers = payload.get("signer_headers")
    discovery_headers = payload.get("discovery_headers")
    if signer_headers is not None and not _is_str_dict(signer_headers):
        raise PymthouseGatewayError(
            "Invalid token: signer_headers must be a {string: string} object"
        )
    if discovery_headers is not None and not _is_str_dict(discovery_headers):
        raise PymthouseGatewayError(
            "Invalid token: discovery_headers must be a {string: string} object"
        )

    orchestrators = payload.get("orchestrators")
    normalized_orchestrators: list[str] | None = None
    if orchestrators is not None:
        if not isinstance(orchestrators, list):
            raise PymthouseGatewayError(
                "Invalid token: orchestrators must be an array of strings"
            )
        normalized_orchestrators = []
        for item in orchestrators:
            if not isinstance(item, str) or not item.strip():
                raise PymthouseGatewayError(
                    "Invalid token: orchestrators must contain only non-empty strings"
                )
            normalized_orchestrators.append(item.strip())

    return {
        "orchestrators": normalized_orchestrators,
        "signer": _str_or_none("signer"),
        "discovery": _str_or_none("discovery"),
        "signer_headers": signer_headers,
        "discovery_headers": discovery_headers,
        "billing": _str_or_none("billing"),
    }


def build_session_token(
    *,
    orchestrators: list[str] | None = None,
    signer: str | None = None,
    signer_headers: dict[str, str] | None = None,
    discovery: str | None = None,
    discovery_headers: dict[str, str] | None = None,
    billing: str | None = None,
) -> str:
    """Build a base64-encoded session token compatible with parse_session_token."""
    payload: dict[str, Any] = {}
    if orchestrators is not None:
        payload["orchestrators"] = list(orchestrators)
    if signer is not None:
        payload["signer"] = signer
    if signer_headers is not None:
        payload["signer_headers"] = dict(signer_headers)
    if discovery is not None:
        payload["discovery"] = discovery
    if discovery_headers is not None:
        payload["discovery_headers"] = dict(discovery_headers)
    if billing is not None:
        payload["billing"] = billing
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
