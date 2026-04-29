"""Clear cached PymtHouse SDK tokens.

    uv run python examples/logout.py --base-url https://pymthouse.example.com --client-id app_xxx
    uv run python examples/logout.py --all
"""

from __future__ import annotations

import argparse

from pymthouse_gateway import PymthouseGatewayClient, PymthouseGatewayConfig, logout_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Logout / clear OAuth cache")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--client-id", default="pymthouse-sdk")
    parser.add_argument("--scopes", default="openid profile sign:job")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Wipe every cached token in the namespace",
    )
    parser.add_argument("--namespace", default="pymthouse-gateway")
    args = parser.parse_args()

    if args.all:
        cleared = logout_all(args.namespace)
        print(f"Cleared {cleared} cached tokens from namespace '{args.namespace}'.")
        return

    if not args.base_url:
        parser.error("--base-url is required when --all is not set")

    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(base_url=args.base_url, client_id=args.client_id, scopes=args.scopes)
    )
    client.logout()
    print(f"Cleared cached token for {args.base_url} ({args.client_id}).")


if __name__ == "__main__":
    main()
