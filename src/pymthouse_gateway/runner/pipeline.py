"""Pipeline base class for BYOC worker servers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Pipeline(ABC):
    """Base class for batch/streaming inference pipelines."""

    def setup(self) -> None:  # noqa: B027 - intentional optional override
        """Run once before serving (load models, allocate buffers, warm GPUs).

        Default implementation is a no-op for stateless pipelines.
        """

    @abstractmethod
    def predict(self, **kwargs: Any) -> Any:
        """Run one inference. Kwargs come from the JSON request body.

        Return a JSON-serialisable value, an iterator/generator (auto-detected
        as SSE by ``make_app``), or raise to surface an error.
        """
        ...
