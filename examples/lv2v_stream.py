"""Start a LiveVideoToVideo stream via PymtHouse OIDC + Livepeer and publish frames.

    uv run python examples/lv2v_stream.py \\
        --base-url https://pymthouse.example.com --client-id app_xxx \\
        --model-id streamdiffusion-sdxl

    By default this opens an asyncio loop, starts the job (with payments + control
    keepalive), sends solid-color test frames like ``python-gateway``'s
    ``examples/write_frames.py``, then closes the job.

    To use NAAP orchestrator discovery::

        --discovery-url https://naap-api.cloudspe.com/v1/discover/orchestrators

    Add ``--discovery-use-signer-bearer`` if that discovery endpoint expects the
    same Authorization header as the signer.

    Quick smoke (URLs only, no media, no asyncio)::

        --urls-only
"""

from __future__ import annotations

import argparse
import asyncio
import warnings
from fractions import Fraction

try:
    from authlib.deprecate import AuthlibDeprecationWarning  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    AuthlibDeprecationWarning = DeprecationWarning

warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)

import av  # noqa: E402
from livepeer_gateway.errors import LivepeerGatewayError  # noqa: E402
from livepeer_gateway.media_publish import MediaPublishConfig, VideoOutputConfig  # noqa: E402

from pymthouse_gateway import (  # noqa: E402
    BrandingConfig,
    ControlConfig,
    ControlMode,
    LivepeerRoutingConfig,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
)


def _solid_rgb_frame(width: int, height: int, rgb: tuple[int, int, int]) -> av.VideoFrame:
    frame = av.VideoFrame(width, height, "rgb24")
    r, g, b = rgb
    frame.planes[0].update(bytes([r, g, b]) * (width * height))
    return frame


def _build_client_and_routing(args: argparse.Namespace) -> PymthouseGatewayClient:
    routing = None
    if args.discovery_url:
        discovery_headers = (
            None
            if args.discovery_use_signer_bearer
            else {"Accept": "application/json"}
        )
        routing = LivepeerRoutingConfig(
            discovery_url=args.discovery_url,
            discovery_headers=discovery_headers,
        )
    return PymthouseGatewayClient(
        config=PymthouseGatewayConfig(base_url=args.base_url, client_id=args.client_id),
        branding=BrandingConfig(product_name="PymtHouse Demo"),
        routing=routing,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start an LV2V job through PymtHouse")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--orchestrator", default=None)
    parser.add_argument(
        "--discovery-url",
        default=None,
        help="Override orchestrator discovery URL (e.g. NAAP v1 discover API).",
    )
    parser.add_argument(
        "--discovery-use-signer-bearer",
        action="store_true",
        help="Send signer Bearer to discovery; default is Accept: application/json only.",
    )
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="Print job URLs and exit (no asyncio, no media; skips payments/keepalive).",
    )
    parser.add_argument("--width", type=int, default=320, help="Frame width (default: 320).")
    parser.add_argument("--height", type=int, default=180, help="Frame height (default: 180).")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second (default: 30).")
    parser.add_argument(
        "--count",
        type=int,
        default=90,
        help="Frames to send (default: 90). Ignored with --urls-only.",
    )
    return parser.parse_args()


async def _async_publish_frames(args: argparse.Namespace) -> None:
    client = _build_client_and_routing(args)
    frame_interval = 1.0 / max(1e-6, args.fps)
    time_base = Fraction(1, int(round(args.fps)))

    job = client.video_to_video(
        model_id=args.model_id,
        orch_url=args.orchestrator,
        start_payments=True,
        control_config=None,
    )
    print("Job started:")
    print(f"  manifest_id:   {job.manifest_id}")
    print(f"  publish_url:   {job.publish_url}")
    print(f"  subscribe_url: {job.subscribe_url}")
    print()

    try:
        media = job.start_media(
            MediaPublishConfig(
                tracks=[VideoOutputConfig(fps=args.fps)],
            )
        )
        for i in range(max(0, args.count)):
            color = (i * 5) % 255
            frame = _solid_rgb_frame(args.width, args.height, (color, 0, 255 - color))
            frame.pts = i
            frame.time_base = time_base
            await media.write_frame(frame)
            await asyncio.sleep(frame_interval)
        print(f"Sent {args.count} frames.", flush=True)
    except LivepeerGatewayError as exc:
        print(f"ERROR: {exc}", flush=True)
    finally:
        await job.close()


def _urls_only_sync(args: argparse.Namespace) -> None:
    client = _build_client_and_routing(args)
    job = client.video_to_video(
        model_id=args.model_id,
        orch_url=args.orchestrator,
        start_payments=False,
        control_config=ControlConfig(mode=ControlMode.DISABLED),
    )
    print("Job started:")
    print(f"  manifest_id:   {job.manifest_id}")
    print(f"  publish_url:   {job.publish_url}")
    print(f"  subscribe_url: {job.subscribe_url}")


def main() -> None:
    args = _parse_args()
    if args.urls_only:
        _urls_only_sync(args)
    else:
        asyncio.run(_async_publish_frames(args))


if __name__ == "__main__":
    main()
