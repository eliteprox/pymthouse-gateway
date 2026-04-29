"""Lightweight transport that runs registered :class:`TransportHook` instances.

This is intentionally a thin abstraction. Most SDK code paths call into
``livepeer_gateway`` directly (which has its own HTTP machinery); this layer
exists so integrators can share a single hook bus across their own HTTP work.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import httpx

from .hooks import HttpExchange, HttpRequest, HttpResponse, TransportHook

_LOG = logging.getLogger(__name__)


class HookedTransport:
    """Synchronous httpx-backed transport with a hook bus.

    Async use cases should wrap their own ``httpx.AsyncClient``; this class
    keeps the surface area small for now.
    """

    def __init__(
        self,
        hooks: Iterable[TransportHook] | None = None,
        *,
        timeout: float = 30.0,
        verify: bool = True,
        user_agent: str | None = None,
    ) -> None:
        self._hooks: list[TransportHook] = list(hooks or [])
        headers = {"Accept": "application/json"}
        if user_agent:
            headers["User-Agent"] = user_agent
        self._client = httpx.Client(timeout=timeout, verify=verify, headers=headers)

    def add_hook(self, hook: TransportHook) -> None:
        self._hooks.append(hook)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> HttpResponse:
        request = HttpRequest(
            method=method.upper(),
            url=url,
            headers=dict(headers or {}),
            body=json,
        )
        exchange = HttpExchange(request=request)
        for hook in self._hooks:
            try:
                hook.on_request(request)
            except Exception:
                _LOG.exception("transport hook on_request failed")

        try:
            r = self._client.request(
                request.method,
                request.url,
                headers=request.headers or None,
                json=request.body,
                params=params,
            )
        except Exception as exc:
            exchange.error = exc
            for hook in self._hooks:
                try:
                    hook.on_error(exchange)
                except Exception:
                    _LOG.exception("transport hook on_error failed")
            raise

        body: Any
        if r.headers.get("content-type", "").startswith("application/json"):
            try:
                body = r.json()
            except Exception:
                body = r.text
        else:
            body = r.text
        response = HttpResponse(
            status_code=r.status_code,
            headers=dict(r.headers),
            body=body,
        )
        exchange.response = response
        for hook in self._hooks:
            try:
                hook.on_response(exchange)
            except Exception:
                _LOG.exception("transport hook on_response failed")
        return response

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HookedTransport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
