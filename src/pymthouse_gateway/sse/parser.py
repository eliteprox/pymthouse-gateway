"""Pure-function SSE field parser, ported from upstream commit ff32e434."""

from __future__ import annotations

from .events import SSEEvent


def parse_sse_lines(lines: list[str]) -> SSEEvent | None:
    """Parse a list of raw SSE lines (no blank-line terminator) into an event.

    Returns ``None`` for comment-only frames or other content that yields no
    semantic event (matches the upstream parser).
    """
    event = "message"
    event_id: str | None = None
    retry: int | None = None
    data: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if not line or line.startswith(":"):
            continue
        if ":" in line:
            field, value = line.split(":", 1)
            if value.startswith(" "):
                value = value[1:]
        else:
            field = line
            value = ""

        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
        elif field == "id":
            event_id = value
        elif field == "retry":
            try:
                retry = int(value)
            except ValueError:
                continue

    if not data and event == "message" and event_id is None and retry is None:
        return None
    return SSEEvent(data="\n".join(data), event=event, id=event_id, retry=retry)
