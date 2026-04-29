"""Branded device-flow login example.

    uv run python examples/device_login.py --base-url https://pymthouse.example.com \\
        --client-id app_xxx
"""

from __future__ import annotations

import argparse

from pymthouse_gateway import BrandingConfig, PymthouseGatewayClient, PymthouseGatewayConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="PymtHouse device login")
    parser.add_argument("--base-url", required=True, help="PymtHouse origin")
    parser.add_argument("--client-id", required=True, help="Public OIDC client id (app_...)")
    parser.add_argument("--scopes", default="openid profile sign:job")
    parser.add_argument("--product-name", default="PymtHouse")
    parser.add_argument("--browser", action="store_true", help="Force browser PKCE flow")
    args = parser.parse_args()

    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(
            base_url=args.base_url,
            client_id=args.client_id,
            scopes=args.scopes,
            headless=not args.browser,
        ),
        branding=BrandingConfig(product_name=args.product_name),
    )
    token = client.login()
    print(f"Logged in. access_token preview: {token[:24]}…")


if __name__ == "__main__":
    main()
