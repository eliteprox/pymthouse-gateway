"""SSE client and parser.

Mirrors the API and semantics of ``livepeer-python-gateway`` commit
``ff32e434422b794296456a1d0e8e4de5525bda57`` (``src/livepeer_gateway/sse.py``)
so :mod:`pymthouse_gateway.livepeer.byoc` can build BYOC SSE streams the same
way ``stream_byoc_request`` does upstream.
"""

from __future__ import annotations

from .client import SSEClient
from .events import SSEEvent
from .parser import parse_sse_lines

__all__ = ["SSEClient", "SSEEvent", "parse_sse_lines"]
