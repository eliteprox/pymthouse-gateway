"""Browser-based authorization-code + PKCE login (loopback redirect)."""

from __future__ import annotations

import http.server
import logging
import socket
import threading
import webbrowser
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from ..branding import BrandingConfig
from ..errors import BrowserLoginError
from ._http import build_oauth2_client
from .oidc import discover

_LOG = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "pymthouse-sdk"
DEFAULT_SCOPES = "openid profile sign:job"
_CALLBACK_PATH = "/callback"
_AUTH_TIMEOUT_S = 300


def _make_loopback_callback_handler(
    session: dict[str, Any],
    branding: BrandingConfig,
) -> type[http.server.BaseHTTPRequestHandler]:
    """Build a handler class that stores callback fields on ``session`` (per login)."""

    class _LoopbackCallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server signature
            parsed = urlparse(self.path)
            if parsed.path != _CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return

            qs = parse_qs(parsed.query)
            session["state"] = qs.get("state", [None])[0]

            if "error" in qs:
                session["error"] = qs["error"][0]
                self._respond("Authorization denied. You can close this window.")
                return

            if "code" in qs:
                session["code"] = qs["code"][0]
                self._respond("Authorization successful! You can close this window.")
                return

            session["error"] = "missing_code"
            self._respond("Missing authorization code. You can close this window.")

        def _respond(self, body: str) -> None:
            title = branding.product_name or "PymtHouse"
            html = (
                "<!DOCTYPE html><html><head><title>"
                f"{title}</title></head><body><p>{body}</p></body></html>"
            )
            payload = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: N802
            _LOG.debug("OIDC callback server: " + fmt, *args)

    return _LoopbackCallbackHandler


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def login(
    base_url: str,
    *,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
    branding: Optional[BrandingConfig] = None,
    timeout: float = 15.0,
    user_agent: Optional[str] = None,
    allow_insecure_tls: bool = False,
    open_browser: bool = True,
    auth_timeout_s: int = _AUTH_TIMEOUT_S,
) -> dict[str, Any]:
    """Run OAuth2 Authorization Code + PKCE flow with a loopback redirect.

    Returns the token response dict on success.
    """
    from authlib.common.security import generate_token

    branding = branding or BrandingConfig()
    config = discover(
        base_url,
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    )
    code_verifier = generate_token(48)
    port = _find_free_port()
    redirect_uri = f"http://127.0.0.1:{port}{_CALLBACK_PATH}"

    session: dict[str, Any] = {
        "code": None,
        "error": None,
        "state": None,
    }
    handler_cls = _make_loopback_callback_handler(session, branding)
    server = http.server.HTTPServer(("127.0.0.1", port), handler_cls)
    server.timeout = auth_timeout_s

    with build_oauth2_client(
        client_id=client_id,
        scopes=scopes,
        redirect_uri=redirect_uri,
        code_challenge_method="S256",
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    ) as client:
        authorize_url, state = client.create_authorization_url(
            config.authorization_endpoint,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            resource=config.issuer,
        )

        _LOG.info("Opening browser for OIDC login")
        print(f"\nOpening browser for {branding.product_name} login: {authorize_url}\n")
        if open_browser:
            try:
                webbrowser.open(authorize_url)
            except Exception:
                _LOG.debug("webbrowser.open failed", exc_info=True)

        result: dict[str, Any] = {}

        def _serve() -> None:
            try:
                server.handle_request()
                result["code"] = session["code"]
                result["error"] = session["error"]
                result["state"] = session["state"]
            except Exception as exc:
                result["error"] = str(exc)
            finally:
                server.server_close()

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        thread.join(timeout=auth_timeout_s)

        if thread.is_alive():
            server.server_close()
            raise BrowserLoginError("Login timed out — no callback received")

        if result.get("error"):
            raise BrowserLoginError(f"Authorization failed: {result['error']}")

        code = result.get("code")
        if not code:
            raise BrowserLoginError("No authorization code received")

        callback_state = result.get("state")
        if callback_state is None:
            _LOG.warning(
                "OAuth callback omitted state parameter; using original request state "
                "(redirect_uri=%s)",
                redirect_uri,
            )
            received_state = state
        else:
            received_state = callback_state
        authorization_response = (
            f"{redirect_uri}?code={code}&state={received_state}"
        )

        try:
            return client.fetch_token(
                config.token_endpoint,
                authorization_response=authorization_response,
                code_verifier=code_verifier,
                redirect_uri=redirect_uri,
                resource=config.issuer,
                state=state,
            )
        except Exception as exc:
            raise BrowserLoginError(f"Token exchange failed: {exc}") from exc
