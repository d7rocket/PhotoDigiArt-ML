"""Feature-to-visual mapping evaluation engine.

Evaluates a MappingGraph against extracted feature data to produce
parameter updates for SimulationParams.with_update().
"""

from __future__ import annotations

from typing import Any

import numpy as np

from apollo7.extraction.base import ExtractionResult
from apollo7.mapping.connections import MappingGraph


# ---------------------------------------------------------------------------
# Feature source registry: (feature_name, key) -> UI display label
# ---------------------------------------------------------------------------

FEATURE_SOURCES: dict[tuple[str, str], str] = {
    ("semantic", "mood_tags.serene"): "Mood: Serene",
    ("semantic", "mood_tags.chaotic"): "Mood: Chaotic",
    ("semantic", "mood_tags.joyful"): "Mood: Joyful",
    ("semantic", "mood_tags.melancholic"): "Mood: Melancholic",
    ("semantic", "mood_tags.energetic"): "Mood: Energetic",
    ("color", "dominant_saturation"): "Color: Avg Saturation",
    ("color", "dominant_brightness"): "Color: Avg Brightness",
    ("depth", "depth_mean"): "Depth: Mean",
    ("depth", "depth_range"): "Depth: Range",
    ("edge", "edge_density"): "Edge: Density",
}

# ---------------------------------------------------------------------------
# Target parameter registry: param_name -> (display_label, min, max)
# ---------------------------------------------------------------------------

TARGET_PARAMS: dict[str, tuple[str, float, float]] = {
    "noise_frequency": ("Noise Frequency", 0.01, 5.0),
    "noise_amplitude": ("Noise Amplitude", 0.0, 5.0),
    "noise_octaves": ("Noise Octaves", 1, 8),
    "turbulence_scale": ("Turbulence Scale", 0.0, 5.0),
    "viscosity": ("Viscosity", 0.0, 2.0),
    "pressure_strength": ("Pressure", 0.0, 5.0),
    "surface_tension": ("Surface Tension", 0.0, 1.0),
    "attraction_strength": ("Attraction", 0.0, 5.0),
    "repulsion_strength": ("Repulsion", 0.0, 5.0),
    "repulsion_radius": ("Repulsion Radius", 0.01, 1.0),
    "smoothing_radius": ("Smoothing Radius", 0.01, 1.0),
    "gas_constant": ("Gas Constant", 0.1, 10.0),
    "speed": ("Speed", 0.0, 5.0),
    "damping": ("Damping", 0.9, 1.0),
}


class MappingEngine:
    """Evaluates mapping connections against feature data.

    For each connection in a MappingGraph, extracts the feature value
    from the corresponding ExtractionResult, normalizes it to [0, 1],
    multiplies by the connection strength, and accumulates per target
    parameter.
    """

    def extract_feature_value(
        self,
        feature_data: dict[str, ExtractionResult],
        source_feature: str,
        source_key: str,
    ) -> float | None:
        """Extract a scalar feature value by navigating the dot-path key.

        Args:
            feature_data: Dict mapping extractor name to ExtractionResult.
            source_feature: The extractor name (e.g. 'semantic', 'color').
            source_key: Dot-path into data dict (e.g. 'mood_tags.serene').

        Returns:
            Normalized float in [0, 1], or None if the value is missing.
        """
        result = feature_data.get(source_feature)
        if result is None:
            return None

        # Navigate dot-path into result.data
        parts = source_key.split(".")
        current: Any = result.data

        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    # Try arrays fallback
                    break
                current = current[part]
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        # If we ended up with a numeric value, normalize
        if isinstance(current, (int, float)):
            # Clamp to [0, 1] -- feature values should already be normalized
            # but we clamp for safety
            return float(max(0.0, min(1.0, current)))

        # Try to extract from arrays if not found in data
        if source_key in result.arrays:
            arr = result.arrays[source_key]
            if isinstance(arr, np.ndarray) and arr.size > 0:
                # Compute summary stat: mean, normalized to [0, 1]
                val = float(np.mean(arr))
                return max(0.0, min(1.0, val))

        return None

    def evaluate(
        self,
        graph: MappingGraph,
        feature_data: dict[str, ExtractionResult],
    ) -> dict[str, float]:
        """Evaluate all connections and produce parameter updates.

        For each connection: extract feature value, multiply by strength,
        accumulate to target parameter. Multiple connections to the same
        target are summed (additive blending).

        Args:
            graph: The MappingGraph defining connections.
            feature_data: Dict mapping extractor name to ExtractionResult.

        Returns:
            Dict mapping target_param name to accumulated float value.
        """
        accumulators: dict[str, float] = {}

        for conn in graph.get_connections():
            value = self.extract_feature_value(
                feature_data, conn.source_feature, conn.source_key
            )
            if value is None:
                continue

            scaled = value * conn.strength
            accumulators[conn.target_param] = (
                accumulators.get(conn.target_param, 0.0) + scaled
            )

        return accumulators
