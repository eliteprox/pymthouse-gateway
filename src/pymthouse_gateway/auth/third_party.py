"""OIDC third-party initiated login helpers (server-side parsing).

Per the OIDC third-party initiate spec, identity providers may redirect users
to an integrator URL with ``iss`` and optional ``login_hint`` /
``target_link_uri`` parameters. This module exposes a small parser that
integrators can wire into their own backends without dragging in the rest of
the SDK auth machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from ..errors import AuthError


@dataclass(frozen=True)
class ThirdPartyInitiateRequest:
    iss: str
    """Issuer that initiated the login."""

    login_hint: str | None = None
    """Optional username/subject hint provided by the IdP."""

    target_link_uri: str | None = None
    """Where the integrator should send the user after login."""

    raw_query: dict[str, list[str]] | None = None
    """Raw parsed query for debugging / extension."""


def parse_third_party_initiate_url(
    url: str,
    *,
    expected_issuer: str | None = None,
) -> ThirdPartyInitiateRequest:
    """Parse a third-party initiate URL and validate ``iss``.

    ``expected_issuer`` is optional but recommended; if set, the function
    raises :class:`AuthError` when ``iss`` does not match.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    iss_values = qs.get("iss") or []
    if not iss_values:
        raise AuthError("Third-party initiate URL missing required 'iss' query parameter")
    iss = iss_values[0]
    if expected_issuer and iss.rstrip("/") != expected_issuer.rstrip("/"):
        raise AuthError(
            f"Third-party initiate iss '{iss}' does not match expected issuer "
            f"'{expected_issuer}'"
        )
    return ThirdPartyInitiateRequest(
        iss=iss,
        login_hint=(qs.get("login_hint") or [None])[0],
        target_link_uri=(qs.get("target_link_uri") or [None])[0],
        raw_query=qs,
    )
