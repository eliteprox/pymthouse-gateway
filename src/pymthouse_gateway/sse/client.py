"""Async SSE client, ported from upstream commit ff32e434."""

from __future__ import annotations

import json
import ssl
from collections.abc import AsyncIterator, Callable
from typing import Any

from ..errors import SSEError

# aiohttp is imported lazily to keep the module importable in environments
# where the SSE feature is unused.


class PaymentRequiredError(SSEError):
    """Raised when an SSE endpoint returns HTTP 402."""


class SSEClient:
    """Async HTTP SSE client supporting GET/POST and 402 retry callbacks."""

    def __init__(
        self,
        url: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retry_headers: Callable[[], dict[str, str]] | None = None,
        verify_tls: bool = True,
    ) -> None:
        self.url = url
        self.method = method
        self.payload = payload
        self.headers = headers or {}
        self.timeout = timeout
        self.retry_headers = retry_headers
        self.verify_tls = verify_tls

    @classmethod
    def post_json(
        cls,
        url: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float | None = None,
        retry_headers: Callable[[], dict[str, str]] | None = None,
        verify_tls: bool = True,
    ) -> SSEClient:
        return cls(
            url,
            method="POST",
            payload=payload,
            headers=headers,
            timeout=timeout,
            retry_headers=retry_headers,
            verify_tls=verify_tls,
        )

    def __aiter__(self) -> AsyncIterator:
        return self.events()

    async def events(self) -> AsyncIterator:
        async for event in self._events_once(self.headers, allow_retry=True):
            yield event

    async def json_events(self) -> AsyncIterator[Any]:
        async for event in self.events():
            if event.data == "[DONE]":
                yield event.data
                return
            try:
                yield event.json()
            except json.JSONDecodeError as exc:
                raise SSEError(
                    f"SSE JSON decode failed: {exc} (data={event.data[:256]!r})"
                ) from exc

    async def _events_once(
        self,
        headers: dict[str, str],
        *,
        allow_retry: bool,
    ) -> AsyncIterator:
        import aiohttp

        from .parser import parse_sse_lines

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        ssl_ctx: Any
        if self.verify_tls:
            ssl_ctx = None
        else:
            ssl_ctx = ssl._create_unverified_context()
        req_headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "pymthouse-gateway/0.1",
        }
        req_headers.update(headers)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    self.method,
                    self.url,
                    json=self.payload,
                    headers=req_headers,
                    ssl=ssl_ctx,
                ) as resp:
                    if (
                        resp.status == 402
                        and self.retry_headers is not None
                        and allow_retry
                    ):
                        raise PaymentRequiredError(
                            "SSE request returned HTTP 402 payment required"
                        )
                    if resp.status >= 400:
                        body = await resp.text()
                        raise SSEError(
                            f"SSE request failed: HTTP {resp.status} from "
                            f"endpoint (url={self.url}); body={body[:512]!r}"
                        )

                    content_type = resp.headers.get("Content-Type", "")
                    if "text/event-stream" not in content_type:
                        raise SSEError(
                            f"SSE request expected text/event-stream, got "
                            f"{content_type!r}"
                        )

                    pending: list[str] = []
                    buffered = ""
                    async for raw in resp.content:
                        buffered += raw.decode("utf-8", errors="replace")
                        lines = buffered.split("\n")
                        buffered = lines.pop()
                        for line in lines:
                            line = line.rstrip("\r")
                            if line == "":
                                event = parse_sse_lines(pending)
                                pending = []
                                if event is not None:
                                    yield event
                                    if event.data == "[DONE]":
                                        return
                            else:
                                pending.append(line)

                    if buffered:
                        pending.append(buffered.rstrip("\r"))
                    event = parse_sse_lines(pending)
                    if event is not None:
                        yield event
        except PaymentRequiredError:
            if self.retry_headers is None:
                raise
            retry_headers = self.retry_headers()
            async for event in self._events_once(retry_headers, allow_retry=False):
                yield event
        except SSEError:
            raise
        except Exception as exc:
            raise SSEError(
                f"SSE request error: {exc.__class__.__name__}: {exc} "
                f"(url={self.url})"
            ) from exc
