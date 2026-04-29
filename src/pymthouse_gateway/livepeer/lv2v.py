"""Branded LV2V wrapper around livepeer_gateway.start_lv2v."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..auth.tokens import TokenSource
from ..config import LivepeerRoutingConfig, PymthouseGatewayConfig
from .resolver import resolve_livepeer_routing


@dataclass(frozen=True)
class LiveVideoToVideoJob:
    """Wrapper that exposes the underlying ``livepeer_gateway.LiveVideoToVideo``.

    Use ``raw`` for advanced control (control channel, payment task, etc.).
    """

    raw: Any

    @property
    def manifest_id(self) -> str | None:
        return getattr(self.raw, "manifest_id", None)

    @property
    def publish_url(self) -> str | None:
        return getattr(self.raw, "publish_url", None)

    @property
    def subscribe_url(self) -> str | None:
        return getattr(self.raw, "subscribe_url", None)

    @property
    def control(self) -> Any:
        return getattr(self.raw, "control", None)

    @property
    def events(self) -> Any:
        return getattr(self.raw, "events", None)

    def media_output(self, **kwargs: Any) -> Any:
        return self.raw.media_output(**kwargs)

    def start_media(self, config: Any) -> Any:
        return self.raw.start_media(config)

    def start_payment_sender(self) -> Any:
        return self.raw.start_payment_sender()

    async def close(self) -> None:
        await self.raw.close()


def video_to_video(
    *,
    model_id: str,
    pymthouse_config: PymthouseGatewayConfig | None = None,
    token_source: TokenSource | None = None,
    routing: LivepeerRoutingConfig | None = None,
    orch_url: Sequence[str] | str | None = None,
    request_id: str | None = None,
    params: dict[str, Any] | None = None,
    stream_id: str | None = None,
    start_payments: bool = True,
    user_agent: str | None = None,
    control_config: Any | None = None,
) -> LiveVideoToVideoJob:
    """Start an LV2V job using PymtHouse auth + ``livepeer_gateway.start_lv2v``.

    Either ``pymthouse_config`` (with ``token_source``) must be provided, or
    ``routing`` must specify an explicit signer URL.

    ``control_config`` is passed through to ``livepeer_gateway.start_lv2v`` (e.g.
    ``ControlConfig(mode=ControlMode.DISABLED)`` to skip control keepalives when
    no asyncio loop is running).
    """
    from livepeer_gateway import StartJobRequest, start_lv2v  # type: ignore[import-untyped]

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

    effective_orch_url = orch_url
    if effective_orch_url is None and routing.orchestrators is not None:
        effective_orch_url = list(routing.orchestrators)

    req = StartJobRequest(
        request_id=request_id,
        model_id=model_id,
        params=params,
        stream_id=stream_id,
    )
    job = start_lv2v(
        effective_orch_url,
        req,
        start_payments=start_payments,
        signer_url=resolution.signer_url,
        signer_headers=resolution.signer_headers,
        discovery_url=resolution.discovery_url,
        discovery_headers=resolution.discovery_headers,
        use_tofu=routing.use_tofu,
        timeout=routing.timeout,
        control_config=control_config,
    )
    return LiveVideoToVideoJob(raw=job)
