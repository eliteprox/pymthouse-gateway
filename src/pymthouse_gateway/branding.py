"""Branding configuration for the SDK.

The SDK is intentionally white-label: integrators can replace product name,
support copy, and the device-flow display strings without forking auth code.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BrandingConfig:
    """Cosmetic / UX configuration for SDK output and HTTP user-agent."""

    product_name: str = "PymtHouse"
    """Displayed in CLI prompts and default user-agent."""

    support_url: str | None = None
    """Optional support link rendered in error/help text."""

    docs_url: str | None = None
    """Optional product docs link."""

    logo_url: str | None = None
    """Optional product logo URL (used by integrators that render UI)."""

    device_login_title: str = "DEVICE AUTHORIZATION"
    """Heading shown by the default device-login printer."""

    device_login_instructions: str | None = None
    """Custom instruction text rendered above the verification URL."""

    user_agent: str | None = None
    """If set, replaces the default ``pymthouse-gateway/<version>`` UA."""

    cache_namespace: str = "pymthouse-gateway"
    """Namespace used to scope the on-disk OAuth token cache."""

    extra_user_agent_tokens: tuple[str, ...] = field(default_factory=tuple)
    """Extra tokens appended to the User-Agent."""

    def effective_user_agent(self, version: str) -> str:
        if self.user_agent:
            return self.user_agent
        base = f"pymthouse-gateway/{version}"
        if self.product_name and self.product_name != "PymtHouse":
            base += f" ({self.product_name})"
        for token in self.extra_user_agent_tokens:
            base += f" {token}"
        return base
