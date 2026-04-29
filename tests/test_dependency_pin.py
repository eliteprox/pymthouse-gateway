"""Verify uv.lock pins livepeer-gateway at the expected commit."""

from __future__ import annotations

from pathlib import Path

import pytest

EXPECTED_COMMIT = "766ee55d9c9d7dff888aa3667a1f8719ba31d273"
LOCK_PATH = Path(__file__).resolve().parents[1] / "uv.lock"


@pytest.mark.skipif(not LOCK_PATH.exists(), reason="uv.lock not generated yet")
def test_livepeer_gateway_pinned_to_expected_commit():
    text = LOCK_PATH.read_text("utf-8")
    assert "livepeer-gateway" in text
    assert EXPECTED_COMMIT in text, (
        f"uv.lock should pin livepeer-gateway at {EXPECTED_COMMIT}"
    )
