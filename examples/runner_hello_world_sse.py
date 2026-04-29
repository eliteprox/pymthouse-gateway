"""SSE-streaming hello-world BYOC pipeline using the runner.

``predict_sse`` returns a generator, so ``make_app`` automatically serves it as
``text/event-stream`` and appends the ``[DONE]`` sentinel.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import uvicorn
from fastapi import Request
from fastapi.responses import StreamingResponse

from pymthouse_gateway.branding import BrandingConfig
from pymthouse_gateway.runner import Pipeline, make_app, sse_response


class HelloWorld(Pipeline):
    def predict(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}


def _hello_events(name: str) -> Iterator[dict]:
    yield {"message": f"hello, {name}"}
    time.sleep(0.1)
    yield {"message": "tick"}


if __name__ == "__main__":
    app = make_app(HelloWorld(), branding=BrandingConfig(product_name="PymtHouse Demo"))

    @app.post("/predict-sse", summary="Run one streaming inference")
    async def predict_sse(request: Request) -> StreamingResponse:
        body = await request.json()
        name = body.get("name", "world") if isinstance(body, dict) else "world"
        return sse_response(_hello_events(str(name)))

    uvicorn.run(app, host="0.0.0.0", port=5000)
