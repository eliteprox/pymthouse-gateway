"""On-disk OAuth token cache (XDG-style, namespaced by branding)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "pymthouse-gateway"
DEFAULT_CLIENT_ID = "pymthouse-sdk"
DEFAULT_SCOPES = "openid profile sign:job"


def _cache_dir(namespace: str = DEFAULT_NAMESPACE) -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / namespace / "tokens"


def _cache_key(
    base_url: str,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> str:
    key_material = f"{base_url}|{client_id}|{scopes}"
    return hashlib.sha256(key_material.encode()).hexdigest()[:16]


def _cache_path(
    base_url: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> Path:
    return _cache_dir(namespace) / f"{_cache_key(base_url, client_id, scopes)}.json"


def load_cached_token(
    base_url: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> dict[str, Any] | None:
    """Return the raw cached token dict for ``base_url`` or ``None``."""
    path = _cache_path(base_url, namespace=namespace, client_id=client_id, scopes=scopes)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        _LOG.debug("Failed to load cached token from %s", path, exc_info=True)
        return None


def save_cached_token(
    base_url: str,
    tokens: dict[str, Any],
    *,
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> None:
    """Persist a token dict atomically at mode 0600."""
    cache = _cache_dir(namespace)
    cache.mkdir(parents=True, exist_ok=True)
    path = _cache_path(base_url, namespace=namespace, client_id=client_id, scopes=scopes)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(tokens)), "utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        # Some filesystems (e.g. Windows) do not honor chmod; ignore.
        pass
    tmp.replace(path)


def clear_cached_token(
    base_url: str,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
) -> None:
    """Delete a single cached token (no-op if absent)."""
    path = _cache_path(base_url, namespace=namespace, client_id=client_id, scopes=scopes)
    try:
        path.unlink(missing_ok=True)
    except TypeError:
        # Python <3.8 lacks missing_ok; we target 3.10+ but be defensive.
        if path.exists():
            path.unlink()


def clear_all_cached_tokens(namespace: str = DEFAULT_NAMESPACE) -> int:
    """Remove every cached token in ``namespace``. Returns count cleared."""
    cache = _cache_dir(namespace)
    if not cache.exists():
        return 0
    count = 0
    for path in cache.glob("*.json"):
        try:
            path.unlink()
            count += 1
        except OSError:
            _LOG.debug("Failed to remove %s", path, exc_info=True)
    return count
