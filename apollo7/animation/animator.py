"""Parameter animator that routes generator outputs to simulation parameters.

AnimationBinding maps a generator (LFO, noise, envelope) output to a
parameter range, and ParameterAnimator manages multiple bindings and
applies them each tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from apollo7.animation.lfo import LFO, NoiseGenerator, Envelope
from apollo7.simulation.parameters import SimulationParams

# Type alias for any generator
GeneratorType = Union[LFO, NoiseGenerator, Envelope]


@dataclass
class AnimationBinding:
    """Maps a generator output to a simulation parameter range.

    The generator's output (assumed in [-1, 1] for LFO/noise,
    [0, peak] for envelope) is linearly mapped to [min_val, max_val].

    For LFO/NoiseGenerator: output in [-1, 1] maps to [min_val, max_val]
    For Envelope: output in [0, peak] is first normalized to [0, 1],
                  then mapped to [min_val, max_val]

    Args:
        target_param: Name of the SimulationParams field to modulate.
        source: Generator instance (LFO, NoiseGenerator, or Envelope).
        min_val: Minimum output value.
        max_val: Maximum output value.
    """

    target_param: str
    source: Any  # LFO | NoiseGenerator | Envelope
    min_val: float = 0.0
    max_val: float = 1.0

    def evaluate(self, time: float) -> float:
        """Evaluate the binding at the given time.

        Maps the source output to [min_val, max_val].

        Args:
            time: Current time in seconds.

        Returns:
            Float value in [min_val, max_val].
        """
        raw = self.source.evaluate(time)

        # Normalize raw to [0, 1]
        if isinstance(self.source, Envelope):
            # Envelope output is in [0, peak], normalize by peak
            peak = self.source.peak if self.source.peak != 0 else 1.0
            normalized = raw / peak
        else:
            # LFO/Noise output is in [-amplitude, +amplitude], normalize
            amp = getattr(self.source, "amplitude", 1.0)
            offset = getattr(self.source, "offset", 0.0)
            # Remove offset, then normalize from [-amp, amp] to [0, 1]
            centered = raw - offset
            if amp != 0:
                normalized = (centered + amp) / (2.0 * amp)
            else:
                normalized = 0.5

        # Clamp to [0, 1] for safety
        normalized = max(0.0, min(1.0, normalized))

        # Map to [min_val, max_val]
        return self.min_val + normalized * (self.max_val - self.min_val)


class ParameterAnimator:
    """Manages animation bindings and applies them to SimulationParams.

    Each tick, all active bindings are evaluated and their results
    applied to a copy of the current params via with_update().
    """

    def __init__(self) -> None:
        self._bindings: list[AnimationBinding] = []

    def add_binding(self, binding: AnimationBinding) -> None:
        """Add an animation binding.

        If a binding for the same target_param already exists,
        it is replaced.

        Args:
            binding: The AnimationBinding to add.
        """
        # Replace existing binding for same param
        self._bindings = [
            b for b in self._bindings if b.target_param != binding.target_param
        ]
        self._bindings.append(binding)

    def remove_binding(self, target_param: str) -> None:
        """Remove the binding for a target parameter.

        Args:
            target_param: Name of the parameter to unbind.
        """
        self._bindings = [
            b for b in self._bindings if b.target_param != target_param
        ]

    @property
    def is_active(self) -> bool:
        """True if any bindings are registered."""
        return len(self._bindings) > 0

    def tick(self, time: float, params: SimulationParams) -> SimulationParams:
        """Evaluate all bindings and return updated params.

        Args:
            time: Current time in seconds.
            params: Current simulation parameters.

        Returns:
            New SimulationParams with animated values applied.
        """
        if not self._bindings:
            return params

        updates: dict[str, float] = {}
        for binding in self._bindings:
            updates[binding.target_param] = binding.evaluate(time)

        return params.with_update(**updates)
