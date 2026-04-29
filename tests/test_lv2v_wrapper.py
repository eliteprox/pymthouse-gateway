"""Verify the LV2V wrapper forwards resolved auth into livepeer_gateway.start_lv2v."""

from __future__ import annotations

from unittest.mock import patch

from livepeer_gateway import ControlConfig, ControlMode  # type: ignore[import-untyped]

from pymthouse_gateway import (
    LivepeerRoutingConfig,
    PymthouseGatewayConfig,
    StaticTokenSource,
    video_to_video,
)


class _FakeJob:
    manifest_id = "m"


def test_video_to_video_forwards_resolution():
    captured = {}

    def fake_start_lv2v(orch_url, req, **kwargs):
        captured["orch_url"] = orch_url
        captured["req"] = req
        captured["kwargs"] = kwargs
        return _FakeJob()

    config = PymthouseGatewayConfig(base_url="https://pymthouse.example.com")
    with (
        patch("pymthouse_gateway.livepeer.resolver.probe_oidc", return_value=True),
        patch("livepeer_gateway.start_lv2v", fake_start_lv2v),
    ):
        job = video_to_video(
            model_id="streamdiffusion-sdxl",
            pymthouse_config=config,
            token_source=StaticTokenSource(access_token="bearer-xyz"),
        )

    assert job.manifest_id == "m"
    kwargs = captured["kwargs"]
    assert kwargs["signer_url"] == config.signer_url()
    assert kwargs["discovery_url"] == config.discovery_url()
    assert kwargs["signer_headers"] == {"Authorization": "Bearer bearer-xyz"}
    assert kwargs["discovery_headers"] == {"Authorization": "Bearer bearer-xyz"}
    assert kwargs.get("control_config") is None
    assert captured["req"].model_id == "streamdiffusion-sdxl"


def test_video_to_video_forwards_control_config():
    captured = {}

    def fake_start_lv2v(orch_url, req, **kwargs):
        captured["kwargs"] = kwargs
        return _FakeJob()

    routing = LivepeerRoutingConfig(
        signer_url="https://signer.override",
        discovery_url="https://disc.override",
    )
    cc = ControlConfig(mode=ControlMode.DISABLED)
    with patch("livepeer_gateway.start_lv2v", fake_start_lv2v):
        video_to_video(
            model_id="noop",
            routing=routing,
            orch_url=["https://orch.example"],
            control_config=cc,
        )

    assert captured["kwargs"]["control_config"] is cc


def test_video_to_video_explicit_routing_skips_oidc():
    captured = {}

    def fake_start_lv2v(orch_url, req, **kwargs):
        captured["kwargs"] = kwargs
        return _FakeJob()

    routing = LivepeerRoutingConfig(
        signer_url="https://signer.override",
        discovery_url="https://disc.override",
    )
    with patch("livepeer_gateway.start_lv2v", fake_start_lv2v):
        video_to_video(
            model_id="noop",
            routing=routing,
            orch_url=["https://orch.example"],
        )

    kwargs = captured["kwargs"]
    assert kwargs["signer_url"] == "https://signer.override"
    assert kwargs["discovery_url"] == "https://disc.override"
