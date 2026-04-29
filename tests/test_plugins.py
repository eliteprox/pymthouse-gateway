from __future__ import annotations

from pymthouse_gateway import (
    HookedTransport,
    HttpExchange,
    HttpRequest,
    PluginRegistry,
    TransportHook,
)
from pymthouse_gateway.media import TrickleMediaProtocol


class _Recording(TransportHook):
    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []
        self.responses: list[HttpExchange] = []
        self.errors: list[HttpExchange] = []

    def on_request(self, request: HttpRequest) -> None:
        self.requests.append(request)

    def on_response(self, exchange: HttpExchange) -> None:
        self.responses.append(exchange)

    def on_error(self, exchange: HttpExchange) -> None:
        self.errors.append(exchange)


def test_plugin_registry_registers_media_protocol():
    registry = PluginRegistry()
    proto = TrickleMediaProtocol()
    registry.register_media_protocol(proto)
    assert registry.media_protocol("trickle") is proto
    assert list(registry.media_protocols()) == [proto]


def test_hooked_transport_runs_request_hooks(httpx_mock):
    httpx_mock.add_response(
        url="https://example.test/echo",
        json={"ok": True},
    )
    hook = _Recording()
    with HookedTransport(hooks=[hook], user_agent="t/1.0") as t:
        resp = t.request("GET", "https://example.test/echo")
    assert resp.status_code == 200
    assert resp.body == {"ok": True}
    assert len(hook.requests) == 1
    assert hook.requests[0].method == "GET"
    assert len(hook.responses) == 1
    assert hook.responses[0].response is not None
