"""Server-Sent Event data model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SSEEvent:
    data: str
    event: str = "message"
    id: str | None = None
    retry: int | None = None

    def json(self) -> Any:
        """Decode ``data`` as JSON. Raises ``json.JSONDecodeError`` on failure."""
        return json.loads(self.data)
