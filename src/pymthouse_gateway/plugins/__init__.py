"""Plugin protocols and a small in-process registry."""

from __future__ import annotations

from .base import GatewayPlugin, MediaProtocol, TokenHook
from .registry import PluginRegistry

__all__ = ["GatewayPlugin", "MediaProtocol", "PluginRegistry", "TokenHook"]
