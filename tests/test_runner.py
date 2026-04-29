"""Smoke tests for the optional FastAPI runner."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from pymthouse_gateway.runner import Pipeline, make_app, sse_response  # noqa: E402


class _Hello(Pipeline):
    def predict(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}


class _HelloIn(BaseModel):
    name: str = "world"


class _HelloOut(BaseModel):
    message: str


class _HelloTyped(Pipeline):
    def predict(self, body: _HelloIn) -> _HelloOut:
        return _HelloOut(message=f"hi {body.name}")


def test_health_route_includes_branding():
    app = make_app(_Hello())
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["pipeline"] == "_Hello"


def test_predict_bare_args():
    app = make_app(_Hello())
    client = TestClient(app)
    resp = client.post("/predict", json={"name": "py"})
    assert resp.status_code == 200
    assert resp.json() == {"message": "hello, py"}


def test_predict_pydantic_model():
    app = make_app(_HelloTyped())
    client = TestClient(app)
    resp = client.post("/predict", json={"name": "py"})
    assert resp.status_code == 200
    assert resp.json() == {"message": "hi py"}


def test_sse_response_helper_emits_done():
    import asyncio

    items: Iterator[dict] = iter([{"x": 1}])
    response = sse_response(items)

    async def _drain() -> str:
        out: list[str] = []
        async for piece in response.body_iterator:  # type: ignore[attr-defined]
            if isinstance(piece, bytes):
                out.append(piece.decode())
            else:
                out.append(piece)
        return "".join(out)

    chunks = asyncio.run(_drain())
    assert 'data: {"x":1}' in chunks
    assert "data: [DONE]" in chunks


def test_sse_streaming_predict_auto_detects_generator():
    class _Gen(Pipeline):
        def predict(self, name: str = "world"):
            yield {"message": f"hello, {name}"}

    app = make_app(_Gen())
    client = TestClient(app)
    with client.stream("POST", "/predict", json={"name": "py"}) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = "".join(resp.iter_text())
    assert 'data: {"message":"hello, py"}' in body
    assert "data: [DONE]" in body
