from __future__ import annotations

import os

from pymthouse_gateway.auth.cache import (
    clear_all_cached_tokens,
    clear_cached_token,
    load_cached_token,
    save_cached_token,
)


def test_round_trip_token():
    base = "https://pymthouse.example.com/api/v1/oidc"
    save_cached_token(base, {"access_token": "abc", "expires_in": 60})
    loaded = load_cached_token(base)
    assert loaded == {"access_token": "abc", "expires_in": 60}


def test_clear_cached_token_idempotent():
    base = "https://pymthouse.example.com/api/v1/oidc"
    clear_cached_token(base)  # no-op
    save_cached_token(base, {"access_token": "abc"})
    clear_cached_token(base)
    assert load_cached_token(base) is None


def test_clear_all_cached_tokens():
    save_cached_token("https://a.example/oidc", {"access_token": "a"})
    save_cached_token("https://b.example/oidc", {"access_token": "b"})
    cleared = clear_all_cached_tokens()
    assert cleared == 2
    assert load_cached_token("https://a.example/oidc") is None
    assert load_cached_token("https://b.example/oidc") is None


def test_save_writes_file_with_restrictive_mode(tmp_path):
    base = "https://pymthouse.example.com/api/v1/oidc"
    save_cached_token(base, {"access_token": "abc"})
    cache = tmp_path / "pymthouse-gateway" / "tokens"
    files = list(cache.glob("*.json"))
    assert len(files) == 1
    if hasattr(os, "stat"):
        mode = files[0].stat().st_mode & 0o777
        # Some filesystems normalise the mode; just verify owner-only minimum.
        assert mode & 0o077 == 0
