"""Tiny in-process plugin registry."""

from __future__ import annotations

from collections.abc import Iterator

from .base import GatewayPlugin, MediaProtocol, TokenHook


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: list[GatewayPlugin] = []
        self._token_hooks: list[TokenHook] = []
        self._media_protocols: dict[str, MediaProtocol] = {}

    def register_plugin(self, plugin: GatewayPlugin) -> None:
        self._plugins.append(plugin)

    def register_token_hook(self, hook: TokenHook) -> None:
        self._token_hooks.append(hook)

    def register_media_protocol(self, protocol: MediaProtocol) -> None:
        self._media_protocols[protocol.name] = protocol

    def media_protocol(self, name: str) -> MediaProtocol:
        return self._media_protocols[name]

    def media_protocols(self) -> Iterator[MediaProtocol]:
        return iter(self._media_protocols.values())

    def plugins(self) -> Iterator[GatewayPlugin]:
        return iter(self._plugins)

    def token_hooks(self) -> Iterator[TokenHook]:
        return iter(self._token_hooks)

    def configure_all(self, client) -> None:
        for plugin in self._plugins:
            plugin.configure(client)
