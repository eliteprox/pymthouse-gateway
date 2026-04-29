"""Wire up custom plugins, transport hooks, and a media protocol."""

from __future__ import annotations

from pymthouse_gateway import (
    HookedTransport,
    HttpExchange,
    HttpRequest,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
    TransportHook,
)
from pymthouse_gateway.media import TrickleMediaProtocol


class TracingHook(TransportHook):
    def on_request(self, request: HttpRequest) -> None:
        print(f"-> {request.method} {request.url}")

    def on_response(self, exchange: HttpExchange) -> None:
        if exchange.response is not None:
            print(f"<- {exchange.response.status_code} {exchange.request.url}")

    def on_error(self, exchange: HttpExchange) -> None:
        print(f"!! error: {exchange.error}")


def main() -> None:
    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(
            base_url="https://pymthouse.example.com",
            client_id="app_demo",
        ),
    )
    client.plugins.register_media_protocol(TrickleMediaProtocol())

    transport = HookedTransport(hooks=[TracingHook()], user_agent="example-client/1.0")
    print("Plugin registry has", sum(1 for _ in client.plugins.media_protocols()), "media protocol(s).")
    transport.close()


if __name__ == "__main__":
    main()
