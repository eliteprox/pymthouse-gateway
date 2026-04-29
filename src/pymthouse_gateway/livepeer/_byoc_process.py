"""Native BYOC ``/process/request/{route}`` implementation.

Upstream commit ``ff32e434422b794296456a1d0e8e4de5525bda57`` added
``BYOCProcessRequest``, ``process_byoc_request``, and ``stream_byoc_request``
to ``livepeer-python-gateway``. The PymtHouse SDK pins
``eliteprox/python-gateway@766ee55...``, which predates that commit, so the
process/SSE wrappers are reimplemented here on top of the primitives that *are*
available at the pinned version (``BYOCPaymentSession``,
``orchestrator_selector``, ``build_capabilities``, ``get_orch_info``).
"""

from __future__ import annotations

import base64
import json
import logging
import ssl
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..errors import PymthouseGatewayError
from ..sse import SSEClient

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SignedRequest:
    job_id: str
    capability: str
    headers: dict[str, str]
    timeout_seconds: int
    payment_session: Any
    signed_job_header: str


def _process_request_url(transcoder: str, *, request_endpoint: str, route: str) -> str:
    from livepeer_gateway.orchestrator import (
        resolve_transcoder_http_url,  # type: ignore[import-untyped]
    )

    base = resolve_transcoder_http_url(transcoder, request_endpoint)
    return base.rstrip("/") + "/" + route.lstrip("/")


def _signed_byoc_request(
    *,
    selected_url: str,
    info: Any,
    capability: str,
    request_id: str | None,
    request: dict[str, Any] | None,
    parameters: dict[str, Any] | None,
    timeout_seconds: int,
    stream_payment_endpoint: str,
    signer_url: str | None,
    signer_headers: dict[str, str] | None,
    capabilities: Any,
    use_tofu: bool,
) -> _SignedRequest:
    from livepeer_gateway import BYOCPaymentSession  # type: ignore[import-untyped]

    job_id = (request_id or "").strip() or uuid.uuid4().hex
    request_payload = json.dumps(request or {}, separators=(",", ":"))
    parameters_payload = json.dumps(parameters or {}, separators=(",", ":"))

    session = BYOCPaymentSession(
        signer_url,
        info,
        capability_name=capability,
        signer_headers=signer_headers,
        capabilities=capabilities,
        stream_payment_endpoint=stream_payment_endpoint,
        use_tofu=use_tofu,
    )
    signed = session.sign_byoc_job(
        job_id=job_id,
        capability=capability,
        request=request_payload,
        parameters=parameters_payload,
        timeout_seconds=max(1, int(timeout_seconds)),
    )
    signed_payload = {
        "id": job_id,
        "request": request_payload,
        "parameters": parameters_payload,
        "capability": capability,
        "sender": signed.sender,
        "sig": signed.signature,
        "timeout_seconds": int(timeout_seconds),
    }
    signed_job_header = base64.b64encode(
        json.dumps(signed_payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    headers = {"Livepeer": signed_job_header}
    payment = session.get_payment()
    if payment.payment:
        headers["Livepeer-Payment"] = payment.payment
        headers["Livepeer-Segment"] = payment.seg_creds or ""
    return _SignedRequest(
        job_id=job_id,
        capability=capability,
        headers=headers,
        timeout_seconds=int(timeout_seconds),
        payment_session=session,
        signed_job_header=signed_job_header,
    )


def _payment_retry_headers(signed: _SignedRequest) -> dict[str, str]:
    payment = signed.payment_session.get_payment()
    headers = {"Livepeer": signed.signed_job_header}
    if payment.payment:
        headers["Livepeer-Payment"] = payment.payment
        headers["Livepeer-Segment"] = payment.seg_creds or ""
    return headers


def _post_byoc_process(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST JSON to a BYOC process endpoint. Re-uses urllib for parity with upstream."""
    from livepeer_gateway import PaymentRequiredError  # type: ignore[import-untyped]
    from livepeer_gateway.orchestrator import _extract_error_message  # type: ignore[import-untyped]

    body_bytes = json.dumps(payload).encode("utf-8")
    req_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "pymthouse-gateway/0.1",
    }
    req_headers.update(headers)
    req = Request(url, data=body_bytes, headers=req_headers, method="POST")
    ssl_ctx = ssl._create_unverified_context()
    try:
        with urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            raw_body = resp.read().decode("utf-8", errors="replace")
            response_headers = {k: v for k, v in resp.headers.items()}
            status = resp.status
    except HTTPError as exc:
        body = _extract_error_message(exc)
        body_part = f"; body={body!r}" if body else ""
        if exc.code == 402:
            raise PaymentRequiredError(
                f"HTTP BYOC process error: HTTP 402 from endpoint (url={url}){body_part}"
            ) from exc
        raise PymthouseGatewayError(
            f"HTTP BYOC process error: HTTP {exc.code} from endpoint (url={url}){body_part}"
        ) from exc
    except ConnectionRefusedError as exc:
        raise PymthouseGatewayError(
            f"HTTP BYOC process error: connection refused (url={url})"
        ) from exc
    except URLError as exc:
        raise PymthouseGatewayError(
            f"HTTP BYOC process error: failed to reach endpoint: "
            f"{getattr(exc, 'reason', exc)} (url={url})"
        ) from exc

    parsed_body: Any = None
    if raw_body.strip():
        try:
            parsed_body = json.loads(raw_body)
        except Exception:
            parsed_body = raw_body
    return {"status_code": status, "headers": response_headers, "body": parsed_body}


@dataclass(frozen=True)
class NativeBYOCProcessResponse:
    status_code: int
    headers: dict[str, str]
    body: Any
    job_id: str
    capability: str
    orchestrator_url: str


@dataclass(frozen=True)
class NativeBYOCProcessStream:
    events: Any  # SSEClient
    job_id: str
    capability: str
    orchestrator_url: str


def _capabilities_for(capability: str) -> Any:
    from livepeer_gateway import CapabilityId, build_capabilities  # type: ignore[import-untyped]

    return build_capabilities(CapabilityId.BYOC, capability)


def _select_cursor(
    orch_url: Sequence[str] | str | None,
    *,
    signer_url: str | None,
    signer_headers: dict[str, str] | None,
    discovery_url: str | None,
    discovery_headers: dict[str, str] | None,
    capabilities: Any,
    use_tofu: bool,
) -> Any:
    from livepeer_gateway import orchestrator_selector  # type: ignore[import-untyped]

    return orchestrator_selector(
        orch_url,
        signer_url=signer_url,
        signer_headers=signer_headers,
        discovery_url=discovery_url,
        discovery_headers=discovery_headers,
        capabilities=capabilities,
        use_tofu=use_tofu,
    )


def native_process_byoc_request(
    orch_url: Sequence[str] | str | None,
    *,
    capability: str,
    route: str,
    request_id: str | None,
    request: dict[str, Any] | None,
    parameters: dict[str, Any] | None,
    body: dict[str, Any] | None,
    timeout_seconds: int,
    request_endpoint: str,
    stream_payment_endpoint: str,
    signer_url: str | None,
    signer_headers: dict[str, str] | None,
    discovery_url: str | None,
    discovery_headers: dict[str, str] | None,
    use_tofu: bool,
) -> NativeBYOCProcessResponse:
    from livepeer_gateway import (  # type: ignore[import-untyped]
        LivepeerGatewayError,
        NoOrchestratorAvailableError,
        OrchestratorRejection,
        PaymentRequiredError,
    )

    if not capability or not capability.strip():
        raise PymthouseGatewayError("process_byoc requires a non-empty capability")
    capability = capability.strip()

    capabilities = _capabilities_for(capability)
    cursor = _select_cursor(
        orch_url,
        signer_url=signer_url,
        signer_headers=signer_headers,
        discovery_url=discovery_url,
        discovery_headers=discovery_headers,
        capabilities=capabilities,
        use_tofu=use_tofu,
    )

    rejections: list[Any] = []
    while True:
        try:
            selected_url, info = cursor.next()
        except NoOrchestratorAvailableError as exc:
            all_rejections = list(exc.rejections) + rejections
            if all_rejections:
                raise NoOrchestratorAvailableError(
                    f"All orchestrators failed ({len(all_rejections)} tried)",
                    rejections=all_rejections,
                ) from None
            raise

        try:
            signed = _signed_byoc_request(
                selected_url=selected_url,
                info=info,
                capability=capability,
                request_id=request_id,
                request=request,
                parameters=parameters,
                timeout_seconds=timeout_seconds,
                stream_payment_endpoint=stream_payment_endpoint,
                signer_url=signer_url,
                signer_headers=signer_headers,
                capabilities=capabilities,
                use_tofu=use_tofu,
            )
            url = _process_request_url(
                info.transcoder,
                request_endpoint=request_endpoint,
                route=route,
            )
            payload = dict(body or {})
            try:
                data = _post_byoc_process(
                    url,
                    payload=payload,
                    headers=signed.headers,
                    timeout=float(signed.timeout_seconds),
                )
            except PaymentRequiredError:
                _LOG.debug(
                    "BYOC process returned HTTP 402; retrying with fresh payment ticket"
                )
                data = _post_byoc_process(
                    url,
                    payload=payload,
                    headers=_payment_retry_headers(signed),
                    timeout=float(signed.timeout_seconds),
                )
            return NativeBYOCProcessResponse(
                status_code=int(data["status_code"]),
                headers=data["headers"],
                body=data["body"],
                job_id=signed.job_id,
                capability=signed.capability,
                orchestrator_url=selected_url,
            )
        except LivepeerGatewayError as exc:
            _LOG.debug(
                "process_byoc candidate failed, trying fallback if available: %s (%s)",
                selected_url,
                exc,
            )
            rejections.append(OrchestratorRejection(url=selected_url, reason=str(exc)))


def native_stream_byoc_request(
    orch_url: Sequence[str] | str | None,
    *,
    capability: str,
    route: str,
    request_id: str | None,
    request: dict[str, Any] | None,
    parameters: dict[str, Any] | None,
    body: dict[str, Any] | None,
    timeout_seconds: int,
    request_endpoint: str,
    stream_payment_endpoint: str,
    signer_url: str | None,
    signer_headers: dict[str, str] | None,
    discovery_url: str | None,
    discovery_headers: dict[str, str] | None,
    use_tofu: bool,
) -> NativeBYOCProcessStream:
    from livepeer_gateway import (  # type: ignore[import-untyped]
        LivepeerGatewayError,
        NoOrchestratorAvailableError,
        OrchestratorRejection,
    )

    if not capability or not capability.strip():
        raise PymthouseGatewayError("stream_byoc requires a non-empty capability")
    capability = capability.strip()

    capabilities = _capabilities_for(capability)
    cursor = _select_cursor(
        orch_url,
        signer_url=signer_url,
        signer_headers=signer_headers,
        discovery_url=discovery_url,
        discovery_headers=discovery_headers,
        capabilities=capabilities,
        use_tofu=use_tofu,
    )

    rejections: list[Any] = []
    while True:
        try:
            selected_url, info = cursor.next()
        except NoOrchestratorAvailableError as exc:
            all_rejections = list(exc.rejections) + rejections
            if all_rejections:
                raise NoOrchestratorAvailableError(
                    f"All orchestrators failed ({len(all_rejections)} tried)",
                    rejections=all_rejections,
                ) from None
            raise

        try:
            signed = _signed_byoc_request(
                selected_url=selected_url,
                info=info,
                capability=capability,
                request_id=request_id,
                request=request,
                parameters=parameters,
                timeout_seconds=timeout_seconds,
                stream_payment_endpoint=stream_payment_endpoint,
                signer_url=signer_url,
                signer_headers=signer_headers,
                capabilities=capabilities,
                use_tofu=use_tofu,
            )
            url = _process_request_url(
                info.transcoder,
                request_endpoint=request_endpoint,
                route=route,
            )
            captured_signed = signed
            events = SSEClient.post_json(
                url,
                payload=dict(body or {}),
                headers=signed.headers,
                timeout=float(signed.timeout_seconds),
                retry_headers=lambda s=captured_signed: _payment_retry_headers(s),
                verify_tls=False,
            )
            return NativeBYOCProcessStream(
                events=events,
                job_id=signed.job_id,
                capability=signed.capability,
                orchestrator_url=selected_url,
            )
        except LivepeerGatewayError as exc:
            _LOG.debug(
                "stream_byoc candidate failed, trying fallback if available: %s (%s)",
                selected_url,
                exc,
            )
            rejections.append(OrchestratorRejection(url=selected_url, reason=str(exc)))
