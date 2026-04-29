"""Consume a BYOC SSE worker through PymtHouse + the SDK SSE client."""

from __future__ import annotations

import argparse
import asyncio
import json

from pymthouse_gateway import (
    BYOCProcessRequest,
    PymthouseGatewayClient,
    PymthouseGatewayConfig,
    PymthouseGatewayError,
)


async def _amain() -> None:
    parser = argparse.ArgumentParser(description="PymtHouse-authenticated BYOC SSE request")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--capability", default="hello-world")
    parser.add_argument("--route", default="predict-sse")
    parser.add_argument("--name", default="livepeer")
    parser.add_argument("--orchestrator", default=None)
    args = parser.parse_args()

    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(base_url=args.base_url, client_id=args.client_id),
    )

    try:
        stream = client.stream_byoc(
            BYOCProcessRequest(
                capability=args.capability,
                route=args.route,
                body={"name": args.name},
            ),
            orch_url=args.orchestrator,
        )
    except PymthouseGatewayError as err:
        print(f"ERROR: {err}")
        return

    print(f"job_id:       {stream.job_id}")
    print(f"capability:   {stream.capability}")
    print(f"orchestrator: {stream.orchestrator_url}")
    print()

    async for event in stream.events:
        if event.data == "[DONE]":
            print("DONE")
            return
        try:
            payload = event.json()
        except json.JSONDecodeError:
            payload = event.data
        rendered = json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else payload
        print(f"{event.event}: {rendered}")


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
