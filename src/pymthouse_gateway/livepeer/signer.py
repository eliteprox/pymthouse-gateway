"""Adapter for the upstream LV2V remote signer payment session."""

from __future__ import annotations

from typing import Any


def build_signer_session(
    signer_url: str | None,
    info: Any,
    *,
    signer_headers: dict[str, str] | None = None,
    type: str = "lv2v",
    capabilities: Any = None,
    use_tofu: bool = True,
) -> Any:
    """Construct a ``livepeer_gateway.PaymentSession`` (LV2V) for advanced use.

    Most callers should rely on :func:`pymthouse_gateway.livepeer.video_to_video`
    or BYOC helpers, which build sessions internally.
    """
    from livepeer_gateway import PaymentSession  # type: ignore[import-untyped]

    return PaymentSession(
        signer_url,
        info,
        signer_headers=signer_headers,
        type=type,
        capabilities=capabilities,
        use_tofu=use_tofu,
    )
