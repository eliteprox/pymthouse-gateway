"""Plugin / extension protocols."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TokenHook(Protocol):
    """Callbacks fired around the OAuth/device flow lifecycle."""

    def on_device_code(
        self,
        verification_url: str,
        user_code: str,
        expires_in: int,
    ) -> None: ...

    def on_token_refreshed(self, token: dict[str, Any]) -> None: ...

    def on_logout(self, cache_key: str | None) -> None: ...


@runtime_checkable
class MediaProtocol(Protocol):
    """Pluggable media protocol (e.g. trickle, WHIP, WHEP)."""

    name: str

    def prepare_ingress(self, job: Any) -> Any: ...

    def prepare_egress(self, job: Any) -> Any: ...


@runtime_checkable
class GatewayPlugin(Protocol):
    """Generic plugin invoked once when the SDK client is constructed."""

    name: str

    def configure(self, client: Any) -> None: ...
