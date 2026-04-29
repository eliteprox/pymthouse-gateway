"""Run a hello-world BYOC pipeline using ``pymthouse_gateway.runner``."""

from __future__ import annotations

from pymthouse_gateway.branding import BrandingConfig
from pymthouse_gateway.runner import Pipeline, serve


class HelloWorld(Pipeline):
    def predict(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}


if __name__ == "__main__":
    serve(HelloWorld(), branding=BrandingConfig(product_name="PymtHouse Demo"))
