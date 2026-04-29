"""Built-in media protocol adapters.

The default protocol delegates to the upstream ``livepeer_gateway`` trickle
publisher/subscriber. Integrators can register their own protocols via
:class:`~pymthouse_gateway.plugins.registry.PluginRegistry`.
"""

from __future__ import annotations

from typing import Any


class TrickleMediaProtocol:
    """Default trickle protocol — publish via ``MediaPublishConfig`` plus subscribe.

    This is intentionally thin; it forwards to whichever ``LiveVideoToVideo``
    or ``BYOCJob`` object the caller already holds.
    """

    name = "trickle"

    def prepare_ingress(self, job: Any) -> Any:
        return job

    def prepare_egress(self, job: Any) -> Any:
        return job
