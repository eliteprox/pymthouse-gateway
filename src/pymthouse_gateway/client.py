"""Top-level PymtHouse SDK client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .auth.cache import DEFAULT_NAMESPACE
from .auth.logout import logout, logout_all
from .auth.tokens import CachedOidcTokenSource, TokenSource
from .branding import BrandingConfig
from .config import LivepeerRoutingConfig, PymthouseGatewayConfig
from .errors import ConfigError
from .livepeer import (
    BYOCJobResult,
    BYOCProcessRequest,
    BYOCProcessResponse,
    BYOCProcessStream,
    BYOCRequest,
    LiveVideoToVideoJob,
    process_byoc,
    start_byoc,
    stream_byoc,
    video_to_video,
)
from .plugins import PluginRegistry


def _sdk_version() -> str:
    try:
        from importlib.metadata import version

        return version("pymthouse-gateway")
    except Exception:  # pragma: no cover
        return "0.1.0"


@dataclass
class PymthouseGatewayClient:
    """High-level entry point for PymtHouse Python integrations.

    Construct with a ``PymthouseGatewayConfig`` and optional ``BrandingConfig``;
    the client handles OIDC discovery, token acquisition, and Livepeer routing.
    Use the helper methods (``video_to_video``, ``process_byoc``,
    ``stream_byoc``, ...) for common flows or instantiate the lower-level
    objects directly when you need full control.
    """

    config: PymthouseGatewayConfig
    branding: BrandingConfig = field(default_factory=BrandingConfig)
    token_source: Optional[TokenSource] = None
    routing: Optional[LivepeerRoutingConfig] = None
    plugins: PluginRegistry = field(default_factory=PluginRegistry)

    def __post_init__(self) -> None:
        if not self.config.base_url:
            raise ConfigError("PymthouseGatewayConfig.base_url is required")
        if self.token_source is None:
            self.token_source = CachedOidcTokenSource(
                base_url=self.config.issuer_url(),
                client_id=self.config.client_id,
                scopes=self.config.scopes,
                headless=self.config.headless,
                branding=self.branding,
                namespace=self._cache_namespace(),
                timeout=self.config.timeout,
                user_agent=self._user_agent(),
                allow_insecure_tls=self.config.allow_insecure_tls,
            )
        self.plugins.configure_all(self)

    def _cache_namespace(self) -> str:
        return self.config.cache_namespace or self.branding.cache_namespace or DEFAULT_NAMESPACE

    def _user_agent(self) -> str:
        return self.branding.effective_user_agent(_sdk_version())

    # ---- auth helpers -----------------------------------------------------

    def login(self) -> str:
        """Force token acquisition and return the access token."""
        assert self.token_source is not None
        return self.token_source.get_access_token()

    def logout(self) -> None:
        """Clear the cached token for this client's issuer."""
        logout(
            self.config.issuer_url(),
            namespace=self._cache_namespace(),
            client_id=self.config.client_id,
            scopes=self.config.scopes,
        )

    def logout_all(self) -> int:
        """Clear every cached token in this client's namespace."""
        return logout_all(self._cache_namespace())

    # ---- Livepeer wrappers -----------------------------------------------

    def video_to_video(
        self,
        *,
        model_id: str,
        orch_url: Optional[Sequence[str] | str] = None,
        request_id: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        stream_id: Optional[str] = None,
        start_payments: bool = True,
        control_config: Optional[Any] = None,
    ) -> LiveVideoToVideoJob:
        return video_to_video(
            model_id=model_id,
            pymthouse_config=self.config,
            token_source=self.token_source,
            routing=self.routing,
            orch_url=orch_url,
            request_id=request_id,
            params=params,
            stream_id=stream_id,
            start_payments=start_payments,
            user_agent=self._user_agent(),
            control_config=control_config,
        )

    def start_byoc(
        self,
        req: BYOCRequest,
        *,
        orch_url: Optional[Sequence[str] | str] = None,
    ) -> BYOCJobResult:
        return start_byoc(
            req,
            pymthouse_config=self.config,
            token_source=self.token_source,
            routing=self.routing,
            orch_url=orch_url,
            user_agent=self._user_agent(),
        )

    def process_byoc(
        self,
        req: BYOCProcessRequest,
        *,
        orch_url: Optional[Sequence[str] | str] = None,
    ) -> BYOCProcessResponse:
        return process_byoc(
            req,
            pymthouse_config=self.config,
            token_source=self.token_source,
            routing=self.routing,
            orch_url=orch_url,
            user_agent=self._user_agent(),
        )

    def stream_byoc(
        self,
        req: BYOCProcessRequest,
        *,
        orch_url: Optional[Sequence[str] | str] = None,
    ) -> BYOCProcessStream:
        return stream_byoc(
            req,
            pymthouse_config=self.config,
            token_source=self.token_source,
            routing=self.routing,
            orch_url=orch_url,
            user_agent=self._user_agent(),
        )
