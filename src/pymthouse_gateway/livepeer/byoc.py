"""Branded BYOC wrappers — start, batch process, and SSE streaming.

The ``BYOCProcessRequest`` / ``process_byoc`` / ``stream_byoc`` API mirrors
upstream commit ``ff32e434422b794296456a1d0e8e4de5525bda57`` so PymtHouse
callers get the same shape with PymtHouse auth automatically applied.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..auth.tokens import TokenSource
from ..config import LivepeerRoutingConfig, PymthouseGatewayConfig
from . import _byoc_process
from .resolver import resolve_livepeer_routing


@dataclass(frozen=True)
class BYOCRequest:
    """Live BYOC stream request (delegates to ``BYOCJobRequest`` upstream)."""

    capability: str
    request_id: str | None = None
    stream_id: str | None = None
    request: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    timeout_seconds: int = 30
    enable_video_ingress: bool = True
    enable_video_egress: bool = True
    enable_data_output: bool = False
    stream_start_endpoint: str = "/ai/stream/start"
    stream_payment_endpoint: str = "/ai/stream/payment"


@dataclass(frozen=True)
class BYOCProcessRequest:
    """Batch BYOC ``/process/request/{route}`` request."""

    capability: str
    route: str = "predict"
    request_id: str | None = None
    request: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    timeout_seconds: int = 30
    request_endpoint: str = "/process/request"
    stream_payment_endpoint: str = "/ai/stream/payment"


@dataclass(frozen=True)
class BYOCJobResult:
    raw: Any

    @property
    def job_id(self) -> str:
        return self.raw.job_id

    @property
    def capability(self) -> str:
        return self.raw.capability

    async def stop(self) -> Any:
        return await self.raw.stop()

    async def close(self) -> None:
        await self.raw.close()


@dataclass(frozen=True)
class BYOCProcessResponse:
    raw: Any

    @property
    def status_code(self) -> int:
        return self.raw.status_code

    @property
    def headers(self) -> dict[str, str]:
        return self.raw.headers

    @property
    def body(self) -> Any:
        return self.raw.body

    @property
    def job_id(self) -> str:
        return self.raw.job_id

    @property
    def capability(self) -> str:
        return self.raw.capability

    @property
    def orchestrator_url(self) -> str:
        return self.raw.orchestrator_url


@dataclass(frozen=True)
class BYOCProcessStream:
    raw: Any

    @property
    def events(self) -> Any:
        return self.raw.events

    @property
    def job_id(self) -> str:
        return self.raw.job_id

    @property
    def capability(self) -> str:
        return self.raw.capability

    @property
    def orchestrator_url(self) -> str:
        return self.raw.orchestrator_url


def _resolve(
    pymthouse_config: PymthouseGatewayConfig | None,
    token_source: TokenSource | None,
    routing: LivepeerRoutingConfig | None,
    user_agent: str | None,
):
    routing = routing or LivepeerRoutingConfig()
    resolution = resolve_livepeer_routing(
        pymthouse_config,
        token_source,
        signer_url=routing.signer_url,
        signer_headers=routing.signer_headers,
        discovery_url=routing.discovery_url,
        discovery_headers=routing.discovery_headers,
        user_agent=user_agent,
    )
    return routing, resolution


def start_byoc(
    req: BYOCRequest,
    *,
    pymthouse_config: PymthouseGatewayConfig | None = None,
    token_source: TokenSource | None = None,
    routing: LivepeerRoutingConfig | None = None,
    orch_url: Sequence[str] | str | None = None,
    user_agent: str | None = None,
) -> BYOCJobResult:
    """Start a live BYOC stream job, applying PymtHouse auth."""
    from livepeer_gateway import BYOCJobRequest, start_byoc_job  # type: ignore[import-untyped]

    routing, resolution = _resolve(pymthouse_config, token_source, routing, user_agent)
    effective_orch_url = orch_url
    if effective_orch_url is None and routing.orchestrators is not None:
        effective_orch_url = list(routing.orchestrators)

    upstream_req = BYOCJobRequest(
        capability=req.capability,
        request_id=req.request_id,
        stream_id=req.stream_id,
        request=req.request,
        parameters=req.parameters,
        body=req.body,
        timeout_seconds=req.timeout_seconds,
        enable_video_ingress=req.enable_video_ingress,
        enable_video_egress=req.enable_video_egress,
        enable_data_output=req.enable_data_output,
        stream_start_endpoint=req.stream_start_endpoint,
        stream_payment_endpoint=req.stream_payment_endpoint,
    )
    job = start_byoc_job(
        effective_orch_url,
        upstream_req,
        signer_url=resolution.signer_url,
        signer_headers=resolution.signer_headers,
        discovery_url=resolution.discovery_url,
        discovery_headers=resolution.discovery_headers,
        use_tofu=routing.use_tofu,
    )
    return BYOCJobResult(raw=job)


def process_byoc(
    req: BYOCProcessRequest,
    *,
    pymthouse_config: PymthouseGatewayConfig | None = None,
    token_source: TokenSource | None = None,
    routing: LivepeerRoutingConfig | None = None,
    orch_url: Sequence[str] | str | None = None,
    user_agent: str | None = None,
) -> BYOCProcessResponse:
    """Send a signed BYOC ``/process/request/{route}`` request.

    Implementation ports the API shape from upstream commit
    ``ff32e434422b794296456a1d0e8e4de5525bda57`` so PymtHouse callers see the
    same surface even though the pinned ``livepeer-gateway`` predates it.
    """
    routing, resolution = _resolve(pymthouse_config, token_source, routing, user_agent)
    effective_orch_url = orch_url
    if effective_orch_url is None and routing.orchestrators is not None:
        effective_orch_url = list(routing.orchestrators)

    response = _byoc_process.native_process_byoc_request(
        effective_orch_url,
        capability=req.capability,
        route=req.route,
        request_id=req.request_id,
        request=req.request,
        parameters=req.parameters,
        body=req.body,
        timeout_seconds=req.timeout_seconds,
        request_endpoint=req.request_endpoint,
        stream_payment_endpoint=req.stream_payment_endpoint,
        signer_url=resolution.signer_url,
        signer_headers=resolution.signer_headers,
        discovery_url=resolution.discovery_url,
        discovery_headers=resolution.discovery_headers,
        use_tofu=routing.use_tofu,
    )
    return BYOCProcessResponse(raw=response)


def stream_byoc(
    req: BYOCProcessRequest,
    *,
    pymthouse_config: PymthouseGatewayConfig | None = None,
    token_source: TokenSource | None = None,
    routing: LivepeerRoutingConfig | None = None,
    orch_url: Sequence[str] | str | None = None,
    user_agent: str | None = None,
) -> BYOCProcessStream:
    """Stream a BYOC ``/process/request/{route}`` SSE response.

    Returns a :class:`BYOCProcessStream` whose ``.events`` is a
    :class:`pymthouse_gateway.sse.SSEClient` async iterator. Emits a final
    ``[DONE]`` sentinel when the worker terminates the stream.
    """
    routing, resolution = _resolve(pymthouse_config, token_source, routing, user_agent)
    effective_orch_url = orch_url
    if effective_orch_url is None and routing.orchestrators is not None:
        effective_orch_url = list(routing.orchestrators)

    stream = _byoc_process.native_stream_byoc_request(
        effective_orch_url,
        capability=req.capability,
        route=req.route,
        request_id=req.request_id,
        request=req.request,
        parameters=req.parameters,
        body=req.body,
        timeout_seconds=req.timeout_seconds,
        request_endpoint=req.request_endpoint,
        stream_payment_endpoint=req.stream_payment_endpoint,
        signer_url=resolution.signer_url,
        signer_headers=resolution.signer_headers,
        discovery_url=resolution.discovery_url,
        discovery_headers=resolution.discovery_headers,
        use_tofu=routing.use_tofu,
    )
    return BYOCProcessStream(raw=stream)
