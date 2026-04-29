"""PymtHouse Python Gateway SDK.

Brandable client for streaming and accessing Livepeer network capabilities
through PymtHouse OIDC + remote signer. Wraps ``livepeer-gateway`` (pinned
to commit ``766ee55d9c9d7dff888aa3667a1f8719ba31d273``) with PymtHouse-aware
auth, branding, and extension hooks.
"""

from __future__ import annotations

from .auth import (
    CachedOidcTokenSource,
    OIDCConfig,
    StaticTokenSource,
    ThirdPartyInitiateRequest,
    TokenSource,
    clear_all_cached_tokens,
    clear_cached_token,
    device_login,
    discover,
    ensure_valid_token,
    load_cached_token,
    login,
    logout,
    logout_all,
    parse_third_party_initiate_url,
    probe_oidc,
    refresh,
    save_cached_token,
)
from .branding import BrandingConfig
from .client import PymthouseGatewayClient
from .config import LivepeerRoutingConfig, PymthouseGatewayConfig
from .errors import (
    AuthError,
    BrowserLoginError,
    ConfigError,
    DeviceFlowError,
    OIDCDiscoveryError,
    PymthouseGatewayError,
    ResolverError,
    SSEError,
    TokenRefreshError,
)
from .http import HookedTransport, HttpExchange, HttpRequest, HttpResponse, TransportHook
from .livepeer import (
    BYOCJobResult,
    BYOCProcessRequest,
    BYOCProcessResponse,
    BYOCProcessStream,
    BYOCRequest,
    ControlConfig,
    ControlMode,
    LivepeerResolution,
    LiveVideoToVideoJob,
    build_session_token,
    parse_session_token,
    process_byoc,
    resolve_livepeer_routing,
    start_byoc,
    stream_byoc,
    video_to_video,
)
from .plugins import GatewayPlugin, MediaProtocol, PluginRegistry, TokenHook
from .sse import SSEClient, SSEEvent, parse_sse_lines

__all__ = [
    "AuthError",
    "BYOCJobResult",
    "BYOCProcessRequest",
    "BYOCProcessResponse",
    "BYOCProcessStream",
    "BYOCRequest",
    "BrandingConfig",
    "BrowserLoginError",
    "CachedOidcTokenSource",
    "ConfigError",
    "ControlConfig",
    "ControlMode",
    "DeviceFlowError",
    "GatewayPlugin",
    "HookedTransport",
    "HttpExchange",
    "HttpRequest",
    "HttpResponse",
    "LivepeerResolution",
    "LivepeerRoutingConfig",
    "LiveVideoToVideoJob",
    "MediaProtocol",
    "OIDCConfig",
    "OIDCDiscoveryError",
    "PluginRegistry",
    "PymthouseGatewayClient",
    "PymthouseGatewayConfig",
    "PymthouseGatewayError",
    "ResolverError",
    "SSEClient",
    "SSEError",
    "SSEEvent",
    "StaticTokenSource",
    "ThirdPartyInitiateRequest",
    "TokenHook",
    "TokenRefreshError",
    "TokenSource",
    "TransportHook",
    "build_session_token",
    "clear_all_cached_tokens",
    "clear_cached_token",
    "device_login",
    "discover",
    "ensure_valid_token",
    "load_cached_token",
    "login",
    "logout",
    "logout_all",
    "parse_session_token",
    "parse_sse_lines",
    "parse_third_party_initiate_url",
    "probe_oidc",
    "process_byoc",
    "refresh",
    "resolve_livepeer_routing",
    "save_cached_token",
    "start_byoc",
    "stream_byoc",
    "video_to_video",
]

__version__ = "0.1.0"
