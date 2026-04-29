"""Run the BYOC hello-world worker via PymtHouse-authenticated batch request."""

from __future__ import annotations

import argparse
import json
import sys

from pymthouse_gateway import (
    BYOCProcessRequest,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
    PymthouseGatewayError,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="PymtHouse-authenticated BYOC process request")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--capability", default="hello-world")
    parser.add_argument("--route", default="predict")
    parser.add_argument("--name", default="livepeer")
    parser.add_argument("--orchestrator", default=None)
    args = parser.parse_args()

    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(base_url=args.base_url, client_id=args.client_id),
    )

    try:
        response = client.process_byoc(
            BYOCProcessRequest(
                capability=args.capability,
                route=args.route,
                body={"name": args.name},
            ),
            orch_url=args.orchestrator,
        )
    except PymthouseGatewayError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"job_id:       {response.job_id}")
    print(f"capability:   {response.capability}")
    print(f"orchestrator: {response.orchestrator_url}")
    print(f"status:       {response.status_code}")
    print("body:")
    print(
        json.dumps(response.body, indent=2, sort_keys=True)
        if isinstance(response.body, dict)
        else response.body
    )


if __name__ == "__main__":
    main()
