"""Transport hook protocol used by ``HookedTransport`` and friends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class HttpRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Any | None = None


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: Any | None = None


@dataclass
class HttpExchange:
    request: HttpRequest
    response: HttpResponse | None = None
    error: BaseException | None = None


@runtime_checkable
class TransportHook(Protocol):
    """Pluggable HTTP middleware for the SDK transport layer.

    Implementations may mutate ``request`` (e.g. add headers, sign a body) or
    inspect ``response`` for telemetry. Hooks have access to bearer tokens by
    design — only register hooks you trust.
    """

    def on_request(self, request: HttpRequest) -> None: ...

    def on_response(self, exchange: HttpExchange) -> None: ...

    def on_error(self, exchange: HttpExchange) -> None: ...
