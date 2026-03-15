"""RandomWalk engine for constrained parameter exploration.

Generates new SimulationParams proposals by either pure random sampling
within constraints or by perturbing current values with gaussian noise
(random walk step).
"""

from __future__ import annotations

import numpy as np

from apollo7.simulation.parameters import SimulationParams


class RandomWalk:
    """Constrained random walk engine for parameter exploration.

    Args:
        seed: Optional random seed for reproducibility.
    """

    def __init__(self, seed: int | None = None):
        self._rng = np.random.default_rng(seed)

    def propose(
        self,
        constraints: dict[str, tuple[float, float]],
        current: SimulationParams | None = None,
        step_size: float = 0.2,
    ) -> SimulationParams:
        """Generate a new SimulationParams proposal within constraints.

        Args:
            constraints: Dict mapping param_name -> (min, max) range.
            current: If provided, perturb current values (random walk).
                     If None, generate pure random within constraints.
            step_size: Perturbation magnitude as fraction of range (0-1).

        Returns:
            New SimulationParams with proposed values.
        """
        updates: dict[str, float | int] = {}

        for param_name, (lo, hi) in constraints.items():
            if current is not None and hasattr(current, param_name):
                # Random walk step: perturb current value
                current_val = getattr(current, param_name)
                if isinstance(current_val, (tuple, list)):
                    continue  # Skip tuple params in constraints
                updates[param_name] = self._perturb(
                    float(current_val), lo, hi, step_size
                )
            else:
                # Pure random within constraints
                updates[param_name] = self._rng.uniform(lo, hi)

            # Handle integer params
            if param_name == "noise_octaves":
                updates[param_name] = int(round(updates[param_name]))

        # Randomize tuple params (gravity, wind) if not constrained
        if "gravity" not in constraints:
            updates["gravity"] = tuple(
                self._rng.uniform(-1.0, 1.0) for _ in range(3)
            )
        if "wind" not in constraints:
            updates["wind"] = tuple(
                self._rng.uniform(-1.0, 1.0) for _ in range(3)
            )

        base = current if current is not None else SimulationParams()
        return base.with_update(**updates)

    def _perturb(
        self,
        current_value: float,
        min_val: float,
        max_val: float,
        step_size: float = 0.2,
    ) -> float:
        """Perturb a value with gaussian noise, clamped to range.

        Args:
            current_value: Current parameter value.
            min_val: Minimum allowed value.
            max_val: Maximum allowed value.
            step_size: Noise magnitude as fraction of range.

        Returns:
            Perturbed value within [min_val, max_val].
        """
        range_size = max_val - min_val
        noise = self._rng.normal(0, step_size * range_size)
        new_value = current_value + noise
        return float(np.clip(new_value, min_val, max_val))
