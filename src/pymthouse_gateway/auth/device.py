"""RFC 8628 device authorization flow."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from ..branding import BrandingConfig
from ..errors import DeviceFlowError
from ._http import build_oauth2_client
from .oidc import _ensure_https_for_display, discover

_LOG = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "pymthouse-sdk"
DEFAULT_SCOPES = "openid profile sign:job"
_DEVICE_POLL_TIMEOUT_S = 600


def _default_print_instructions(
    branding: BrandingConfig,
    *,
    verification_uri: str,
    verification_uri_complete: str | None,
    user_code: str,
    expires_in: int,
) -> None:
    bar = "=" * 50
    print()
    print(bar)
    title = branding.device_login_title or "DEVICE AUTHORIZATION"
    print(f"  {branding.product_name}: {title}")
    print(bar)
    if branding.device_login_instructions:
        print()
        print(f"  {branding.device_login_instructions}")
    if verification_uri_complete:
        print()
        print(f"  Go to: {verification_uri_complete}")
        print()
        print(f"  Or visit: {verification_uri}")
        print(f"  And enter code: {user_code}")
    else:
        print()
        print(f"  Go to: {verification_uri}")
        print(f"  Enter code: {user_code}")
    print()
    print(f"  Code expires in {max(1, expires_in // 60)} minutes.")
    print(bar)
    print()


def device_login(
    base_url: str,
    *,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
    branding: BrandingConfig | None = None,
    on_device_auth: Callable[[str, str, int], None] | None = None,
    timeout: float = 15.0,
    user_agent: str | None = None,
    allow_insecure_tls: bool = False,
    poll_timeout_s: int = _DEVICE_POLL_TIMEOUT_S,
    print_instructions: bool = True,
) -> dict[str, Any]:
    """Run RFC 8628 device authorization. Returns the token response dict.

    The token response includes ``access_token``, optional ``refresh_token``,
    ``expires_in``, etc., per the OIDC spec.

    ``on_device_auth`` is called with ``(verification_url, user_code, expires_in)``
    once the device code is issued. Pass a no-op callable plus
    ``print_instructions=False`` to suppress the default branded printout.
    """
    branding = branding or BrandingConfig()
    config = discover(
        base_url,
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    )

    if not config.device_authorization_endpoint:
        raise DeviceFlowError(
            "Device Authorization Flow not supported by this provider; "
            "discovery has no device_authorization_endpoint."
        )

    with build_oauth2_client(
        client_id=client_id,
        scopes=scopes,
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    ) as client:
        resp = client.request(
            "POST",
            config.device_authorization_endpoint,
            withhold_token=True,
            data={
                "client_id": client_id,
                "scope": scopes,
                # RFC 8707: bind issued tokens to this issuer as audience.
                "resource": config.issuer,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code >= 400:
        raise DeviceFlowError(
            f"Device authorization request failed (HTTP {resp.status_code}): "
            f"{resp.text[:512]}"
        )

    data = resp.json()
    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = _ensure_https_for_display(data.get("verification_uri", ""))
    verification_uri_complete = _ensure_https_for_display(
        data.get("verification_uri_complete", "") or ""
    )
    expires_in = int(data.get("expires_in", 600))
    interval = max(1, int(data.get("interval", 5)))

    auth_url = verification_uri_complete or verification_uri
    if on_device_auth is not None:
        try:
            on_device_auth(auth_url, user_code, expires_in)
        except Exception:
            _LOG.warning("on_device_auth callback failed", exc_info=True)

    if print_instructions:
        _default_print_instructions(
            branding,
            verification_uri=verification_uri,
            verification_uri_complete=verification_uri_complete or None,
            user_code=user_code,
            expires_in=expires_in,
        )

    deadline = time.time() + min(expires_in, poll_timeout_s)
    poll_interval = interval

    with build_oauth2_client(
        client_id=client_id,
        scopes=scopes,
        timeout=timeout,
        user_agent=user_agent,
        allow_insecure_tls=allow_insecure_tls,
    ) as client:
        while time.time() < deadline:
            time.sleep(poll_interval)

            resp = client.request(
                "POST",
                config.token_endpoint,
                withhold_token=True,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": client_id,
                    "device_code": device_code,
                    "resource": config.issuer,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code == 200:
                _LOG.info("Device authorized successfully")
                return resp.json()

            try:
                err_data = resp.json()
            except Exception as exc:
                raise DeviceFlowError(
                    f"Token poll failed (HTTP {resp.status_code}): {resp.text[:512]}"
                ) from exc

            error = err_data.get("error", "")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                poll_interval += 5
                continue
            if error == "access_denied":
                raise DeviceFlowError("User denied the device authorization request")
            if error == "expired_token":
                raise DeviceFlowError("Device code expired before user authorized")
            raise DeviceFlowError(
                f"Device code token exchange failed: "
                f"{err_data.get('error_description', error)}"
            )

    raise DeviceFlowError("Device authorization timed out before user approved")
