"""Dimensional slider mappings from abstract dimensions to concrete simulation parameters.

Maps four abstract creative dimensions (Energy, Density, Flow, Structure) to
concrete SimulationParams ranges, allowing artists to steer discovery by intent
rather than individual parameter values.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Each dimension maps to a set of parameters with their full ranges.
# Format: {dimension_name: {param_name: (range_min, range_max)}}
DIMENSION_MAPPINGS: dict[str, dict[str, tuple[float, float]]] = {
    "energy": {
        "speed": (0.2, 3.0),
        "turbulence_scale": (0.5, 3.0),
        "noise_amplitude": (0.3, 2.5),
        "noise_octaves": (2, 8),
    },
    "density": {
        "attraction_strength": (0.1, 1.0),
        "repulsion_radius": (0.05, 0.2),
    },
    "flow": {
        "viscosity": (0.01, 0.5),
        "damping": (0.9, 0.99),
        "noise_frequency": (0.1, 2.0),
    },
    "structure": {
        "noise_frequency": (0.1, 1.5),
        "repulsion_strength": (0.1, 0.8),
        "pressure_strength": (0.5, 2.0),
    },
}


class DimensionalMapper:
    """Maps abstract dimensional slider values [0,1] to concrete parameter range constraints.

    Uses exponential smoothing (alpha=0.3) to prevent wild parameter jumps
    when sliders are moved rapidly.
    """

    def __init__(self, alpha: float = 0.3):
        self._values: dict[str, float] = {
            "energy": 0.5,
            "density": 0.5,
            "flow": 0.5,
            "structure": 0.5,
        }
        self._alpha = alpha

    def set_dimension(self, name: str, value: float) -> None:
        """Set a dimensional slider value with exponential smoothing.

        Args:
            name: Dimension name (energy, density, flow, structure).
            value: Target value in [0, 1].
        """
        if name not in self._values:
            raise ValueError(f"Unknown dimension: {name}")
        value = max(0.0, min(1.0, value))
        # Exponential smoothing: new = old * (1 - alpha) + target * alpha
        self._values[name] = self._values[name] * (1 - self._alpha) + value * self._alpha

    def get_param_ranges(self) -> dict[str, tuple[float, float]]:
        """Compute constrained parameter ranges based on current slider positions.

        For each dimension, the slider position determines which portion of
        the parameter's full range to use:
        - At value=0: constrain to lower 40% of range
        - At value=0.5: use middle 60% of range
        - At value=1: constrain to upper 40% of range

        When multiple dimensions affect the same parameter, their ranges
        are intersected (narrower wins).

        Returns:
            Dict mapping param_name -> (min, max) constrained range.
        """
        result: dict[str, tuple[float, float]] = {}

        for dim_name, dim_value in self._values.items():
            mappings = DIMENSION_MAPPINGS.get(dim_name, {})
            for param_name, (full_min, full_max) in mappings.items():
                full_range = full_max - full_min
                # Window width: 40% of full range
                window = 0.4 * full_range
                # Center of window slides from full_min + window/2 to full_max - window/2
                center_min = full_min + window / 2
                center_max = full_max - window / 2
                center = center_min + dim_value * (center_max - center_min)

                lo = max(full_min, center - window / 2)
                hi = min(full_max, center + window / 2)

                # Intersect with existing range if param already constrained
                if param_name in result:
                    existing_lo, existing_hi = result[param_name]
                    lo = max(lo, existing_lo)
                    hi = max(lo, min(hi, existing_hi))  # Ensure lo <= hi

                result[param_name] = (lo, hi)

        return result

    def get_constraints(self) -> dict[str, tuple[float, float]]:
        """Alias for get_param_ranges() for backward compatibility."""
        return self.get_param_ranges()
