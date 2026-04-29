from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Redirect the OAuth token cache to a tmp dir for each test."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("PYMTHOUSE_GATEWAY_AUTH_BROWSER", raising=False)
    monkeypatch.delenv("LIVEPEER_AUTH_BROWSER", raising=False)
    yield
    # Sanity: tmp_path is auto-cleaned by pytest.
    assert os.environ.get("XDG_CACHE_HOME") == str(tmp_path)
