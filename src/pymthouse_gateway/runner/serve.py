"""FastAPI/Uvicorn-backed serving for ``Pipeline`` subclasses."""

# NOTE: do *not* use ``from __future__ import annotations`` here; FastAPI relies
# on resolved types in the request handler's ``__annotations__`` and cannot
# resolve the dynamically generated ``InputModel`` if it's a string.

import inspect
import json
import logging
from collections.abc import Callable, Iterable
from typing import Any

from ..branding import BrandingConfig
from .pipeline import Pipeline

_LOG = logging.getLogger(__name__)


def _is_basemodel(t: Any) -> bool:
    try:
        from pydantic import BaseModel  # type: ignore[import-untyped]
    except ImportError:
        return False
    return isinstance(t, type) and issubclass(t, BaseModel)


def _resolve_hints(predict_fn: Any) -> dict[str, Any]:
    """Resolve ``predict``'s annotations even when ``from __future__ import annotations``
    is in effect (which would otherwise leave them as strings)."""
    try:
        return inspect.get_annotations(predict_fn, eval_str=True)
    except Exception:
        # Fallback: use typing.get_type_hints which can also include the class
        # globals when ``predict`` is a method.
        try:
            from typing import get_type_hints

            return get_type_hints(predict_fn)
        except Exception:
            return getattr(predict_fn, "__annotations__", {}) or {}


def _build_input_model(predict_fn: Any, owner_name: str):
    from pydantic import BaseModel, create_model  # type: ignore[import-untyped]

    sig = inspect.signature(predict_fn)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    hints = _resolve_hints(predict_fn)

    if len(params) == 1:
        first = params[0]
        annotation = hints.get(first.name, first.annotation)
        if _is_basemodel(annotation):
            return annotation, True

    fields: dict[str, tuple[Any, Any]] = {}
    for param in params:
        annotation = hints.get(param.name, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = Any
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[param.name] = (annotation, default)
    return create_model(f"{owner_name}Input", __base__=BaseModel, **fields), False


def _format_sse_chunk(item: Any, *, event: str = "message") -> str:
    if isinstance(item, str):
        data = item
    else:
        data = json.dumps(item, separators=(",", ":"))
    out = []
    if event != "message":
        out.append(f"event: {event}\n")
    for line in data.splitlines() or [""]:
        out.append(f"data: {line}\n")
    out.append("\n")
    return "".join(out)


def sse_response(items: Iterable[Any], *, event: str = "message", done_sentinel: bool = True):
    """Convenience: build a FastAPI ``StreamingResponse`` from any iterable."""
    from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]

    def _generator():
        for item in items:
            yield _format_sse_chunk(item, event=event)
        if done_sentinel:
            yield "data: [DONE]\n\n"

    return StreamingResponse(_generator(), media_type="text/event-stream")


def make_app(
    pipeline: Pipeline,
    *,
    branding: BrandingConfig | None = None,
    extra_routes: Callable[[Any], None] | None = None,
):
    """Build a FastAPI app exposing ``pipeline`` over HTTP.

    - ``POST /predict`` — runs ``pipeline.predict(**body)``.
    - ``GET /health`` — readiness probe.
    - If ``predict`` returns a generator/async-generator, the response is
      streamed as ``text/event-stream``.
    - ``extra_routes`` is invoked with the FastAPI app so integrators can mount
      additional routes without subclassing.
    """
    from fastapi import FastAPI, HTTPException  # type: ignore[import-untyped]
    from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]
    from pydantic import BaseModel  # type: ignore[import-untyped]

    branding = branding or BrandingConfig()
    pipeline.setup()
    InputModel, explicit_basemodel = _build_input_model(
        pipeline.predict, type(pipeline).__name__
    )
    return_annotation = inspect.signature(pipeline.predict).return_annotation
    OutputModel = return_annotation if _is_basemodel(return_annotation) else None

    def _call(body: BaseModel) -> Any:
        if explicit_basemodel:
            return pipeline.predict(body)
        return pipeline.predict(**body.model_dump())

    def _handler(body):
        try:
            result = _call(body)
        except HTTPException:
            raise
        except Exception as exc:
            _LOG.exception("predict() failed")
            raise HTTPException(status_code=500, detail="internal error") from exc

        if hasattr(result, "__aiter__"):
            async def _aiter():
                async for item in result:
                    yield _format_sse_chunk(item)
                yield "data: [DONE]\n\n"

            return StreamingResponse(_aiter(), media_type="text/event-stream")

        if inspect.isgenerator(result) or (
            isinstance(result, Iterable)
            and not isinstance(result, (str, bytes, dict, list, BaseModel))
        ):
            return sse_response(result)

        return result

    # Explicit annotation assignment so FastAPI sees the dynamic Pydantic
    # ``InputModel`` even though we use ``from __future__ import annotations``
    # elsewhere in the SDK.
    _handler.__annotations__["body"] = InputModel
    if OutputModel is not None:
        _handler.__annotations__["return"] = OutputModel

    app = FastAPI(
        title=branding.product_name + ": " + type(pipeline).__name__,
        version="0.1.0",
    )
    app.state.pipeline = pipeline
    app.state.branding = branding

    app.add_api_route(
        "/predict",
        _handler,
        methods=["POST"],
        summary="Run one inference",
    )

    @app.get("/health", summary="Liveness probe")
    def handle_health() -> dict:
        return {
            "status": "ready",
            "product": branding.product_name,
            "pipeline": type(pipeline).__name__,
        }

    if extra_routes is not None:
        extra_routes(app)
    return app


def serve(
    pipeline: Pipeline,
    *,
    host: str = "0.0.0.0",
    port: int = 5000,
    branding: BrandingConfig | None = None,
    extra_routes: Callable[[Any], None] | None = None,
) -> None:
    """Run the pipeline as a Uvicorn server on ``host``/``port``."""
    import uvicorn  # type: ignore[import-untyped]

    app = make_app(pipeline, branding=branding, extra_routes=extra_routes)
    uvicorn.run(app, host=host, port=port)
