"""Customize product name, support URL, login copy, and HTTP user-agent."""

from __future__ import annotations

from pymthouse_gateway import BrandingConfig, PymthouseGatewayClient, PymthouseGatewayConfig


def main() -> None:
    branding = BrandingConfig(
        product_name="Acme Video",
        support_url="https://acme.example/support",
        docs_url="https://acme.example/docs",
        device_login_title="LOG IN TO ACME VIDEO",
        device_login_instructions="Approve this device on your laptop or phone.",
        cache_namespace="acme-video",
        extra_user_agent_tokens=("acme-video/1.2.3",),
    )
    client = PymthouseGatewayClient(
        config=PymthouseGatewayConfig(
            base_url="https://pymthouse.example.com",
            client_id="app_acme",
        ),
        branding=branding,
    )
    print("Configured client:")
    print(f"  cache namespace: {branding.cache_namespace}")
    print(f"  effective UA:    {branding.effective_user_agent('0.1.0')}")
    print(f"  signer URL:      {client.config.signer_url()}")


if __name__ == "__main__":
    main()
