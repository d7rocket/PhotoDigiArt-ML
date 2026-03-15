"""Feature-to-visual mapping evaluation engine.

Evaluates a MappingGraph against feature data to produce parameter updates.
"""

from __future__ import annotations

from typing import Any

from apollo7.extraction.base import ExtractionResult
from apollo7.mapping.connections import MappingGraph


class MappingEngine:
    """Evaluates mapping connections to produce parameter updates."""

    def extract_feature_value(
        self,
        feature_data: dict[str, ExtractionResult],
        source_feature: str,
        source_key: str,
    ) -> float | None:
        raise NotImplementedError

    def evaluate(
        self,
        graph: MappingGraph,
        feature_data: dict[str, ExtractionResult],
    ) -> dict[str, float]:
        raise NotImplementedError
