"""Exception hierarchy for the PymtHouse gateway SDK."""

from __future__ import annotations


class PymthouseGatewayError(Exception):
    """Base error for the PymtHouse Python SDK."""


class ConfigError(PymthouseGatewayError):
    """Raised when configuration is invalid or incomplete."""


class AuthError(PymthouseGatewayError):
    """Base error for authentication issues."""


class OIDCDiscoveryError(AuthError):
    """The OIDC discovery document could not be loaded or parsed."""


class DeviceFlowError(AuthError):
    """RFC 8628 device flow failed (denied, expired, slow_down exhausted, etc)."""


class BrowserLoginError(AuthError):
    """Browser-based authorization-code + PKCE login failed."""


class TokenRefreshError(AuthError):
    """Refreshing an OAuth token failed."""


class ResolverError(PymthouseGatewayError):
    """Resolving a billing/PymtHouse base URL into signer/discovery failed."""


class SSEError(PymthouseGatewayError):
    """SSE client or parser error."""
