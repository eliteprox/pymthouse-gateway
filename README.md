# pymthouse-gateway

Brandable Python SDK for streaming and accessing Livepeer network capabilities
through [PymtHouse](https://pymthouse.com) — OIDC + remote signer + BYOC
batch/SSE — built on top of [`livepeer-gateway`][livepeer-gateway].

`pymthouse-gateway` wraps the upstream gateway transport (pinned to a specific
git commit in `uv.lock`) and adds:

- OIDC device + browser PKCE login, refresh, and logout (RFC 8628 / RFC 8707)
- An XDG-style on-disk OAuth token cache namespaced per integrator
- A high-level `PymthouseGatewayClient` that resolves issuer / signer /
  discovery URLs and bearer headers from your PymtHouse base URL
- LV2V (`video_to_video`) and BYOC (`start_byoc`, `process_byoc`,
  `stream_byoc`) wrappers with PymtHouse auth applied automatically
- A pure-async SSE client (`SSEClient`, `SSEEvent`, `parse_sse_lines`)
- Optional FastAPI/Uvicorn-based runner (`pymthouse_gateway.runner`) for BYOC
  capability workers, including SSE auto-detection
- Lightweight extension points: `TransportHook`, `TokenHook`, `MediaProtocol`,
  `GatewayPlugin`, `BrandingConfig`

## Install

```bash
uv sync --extra dev --extra runner
```

`uv.lock` pins `livepeer-gateway` to commit
`766ee55d9c9d7dff888aa3667a1f8719ba31d273` (branch **`feat/remote-signer-byoc`**
on [`eliteprox/python-gateway`][livepeer-gateway]) so builds are reproducible.

## Quick start

### Device login

```python
from pymthouse_gateway import (
    BrandingConfig,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
)

client = PymthouseGatewayClient(
    config=PymthouseGatewayConfig(
        base_url="https://pymthouse.example.com",
        client_id="app_...",
    ),
    branding=BrandingConfig(product_name="Acme Video"),
)

access_token = client.login()  # device flow by default; PYMTHOUSE_GATEWAY_AUTH_BROWSER=1 for PKCE
```

### LV2V stream

```python
job = client.video_to_video(model_id="streamdiffusion-sdxl")
async with job.media_output() as output:
    async for packet in output.packets():
        ...
```

### BYOC batch / SSE

```python
from pymthouse_gateway import BYOCProcessRequest

response = client.process_byoc(
    BYOCProcessRequest(capability="hello-world", route="predict", body={"name": "livepeer"})
)
print(response.body)

stream = client.stream_byoc(
    BYOCProcessRequest(capability="hello-world", route="predict-sse", body={"name": "livepeer"})
)
async for event in stream.events:
    if event.data == "[DONE]":
        break
    print(event.event, event.json())
```

### Runner (BYOC capability worker)

```python
from pymthouse_gateway.runner import Pipeline, serve

class HelloWorld(Pipeline):
    def predict(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}

if __name__ == "__main__":
    serve(HelloWorld())
```

If `predict` returns a generator/async-generator, `make_app` automatically
serves it as `text/event-stream` with a `[DONE]` sentinel.

### Logout

```python
client.logout()        # one issuer
client.logout_all()    # entire SDK cache namespace
```

## Branding & customization

`BrandingConfig` controls product name, support URL, device-flow copy, the
HTTP user-agent, and the on-disk cache namespace. `LivepeerRoutingConfig`
overrides signer/discovery routing for tests or direct integrations.

## Third-party initiated login

`pymthouse_gateway.parse_third_party_initiate_url` parses
`{your-app}/login?iss=...&login_hint=...&target_link_uri=...` redirects so
integrator backends can validate the issuer before continuing the flow.

## Server-side warning

This SDK is intended for **public** OIDC clients (`app_...`). Confidential
clients (`m2m_...`) and Builder API M2M flows belong in a server-side
companion package and **must not** be embedded in distributed apps.

## Status

This is a fresh SDK; expect rapid iteration as the BYOC SSE, runner schema
generation, and PymtHouse Builder API integrations land.

[livepeer-gateway]: https://github.com/eliteprox/python-gateway
