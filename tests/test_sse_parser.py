from __future__ import annotations

from pymthouse_gateway import SSEEvent
from pymthouse_gateway.sse import parse_sse_lines


def test_parses_multiline_data_and_fields():
    event = parse_sse_lines(
        [
            "id: abc",
            "event: token",
            "retry: 5000",
            "data: hello",
            "data: world",
        ]
    )
    assert event == SSEEvent(event="token", id="abc", retry=5000, data="hello\nworld")


def test_ignores_comments_and_empty_comment_events():
    assert parse_sse_lines([": keepalive"]) is None


def test_preserves_done_sentinel():
    event = parse_sse_lines(["data: [DONE]"])
    assert event is not None
    assert event.data == "[DONE]"


def test_strips_single_leading_space_from_value():
    event = parse_sse_lines(["data: hello world"])
    assert event is not None
    assert event.data == "hello world"


def test_invalid_retry_is_ignored():
    event = parse_sse_lines(["data: x", "retry: not-a-number"])
    assert event is not None
    assert event.retry is None


def test_event_json_decode():
    event = parse_sse_lines(["data: {\"x\": 1}"])
    assert event is not None
    assert event.json() == {"x": 1}
