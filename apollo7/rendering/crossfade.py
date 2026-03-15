"""Unified crossfade engine for smooth parameter transitions.

Provides ease-out chase animation for all continuous parameter changes
(slider drags, A/B preset crossfade). Discrete params like solver_iterations
snap instantly. Uses QTimer at ~60fps for smooth interpolation.

The cubic ease-out curve (1 - (1-t)^3) gives fast initial response with
smooth deceleration -- iOS-like polish for parameter changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6 import QtCore


@dataclass
class _Transition:
    """Tracks an active parameter transition."""

    start: float
    end: float
    progress: float  # 0.0 to 1.0


class CrossfadeEngine:
    """Ease-out interpolation engine for smooth parameter transitions.

    All continuous parameter changes are routed through this engine.
    Discrete params (solver_iterations) bypass the engine and are
    applied immediately.

    Args:
        apply_fn: Callback receiving (param_name, interpolated_value)
                  for each tick of an active transition.
    """

    TICK_MS: int = 16  # ~60fps update rate
    DURATION_MS: int = 400  # ~0.4s transition
    DISCRETE_PARAMS: frozenset = frozenset({"solver_iterations"})

    def __init__(self, apply_fn: Callable[[str, float], None]) -> None:
        self._apply_fn = apply_fn
        self._active: dict[str, _Transition] = {}

        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_target(self, name: str, target: float, current: float) -> None:
        """Start or retarget a parameter transition.

        If the param is discrete (e.g. solver_iterations), applies immediately.
        If a transition is already active for this param, retargets from the
        current interpolated position.

        Args:
            name: Parameter name.
            target: Target value to transition toward.
            current: Current value to transition from.
        """
        # Discrete params snap instantly
        if name in self.DISCRETE_PARAMS:
            self._apply_fn(name, target)
            return

        # If transition already active, compute current interpolated value
        # as new start point
        if name in self._active:
            existing = self._active[name]
            eased = self._ease_out(existing.progress)
            current = existing.start + (existing.end - existing.start) * eased

        self._active[name] = _Transition(
            start=current,
            end=target,
            progress=0.0,
        )

        # Start timer if not already running
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self) -> None:
        """Advance all active transitions by one frame.

        Computes eased value using cubic ease-out, calls apply_fn,
        and removes completed transitions. Stops timer when empty.
        """
        if not self._active:
            self._timer.stop()
            return

        dt_ratio = self.TICK_MS / self.DURATION_MS
        completed = []

        for name, transition in self._active.items():
            transition.progress = min(transition.progress + dt_ratio, 1.0)
            eased = self._ease_out(transition.progress)
            value = transition.start + (transition.end - transition.start) * eased

            self._apply_fn(name, value)

            if transition.progress >= 1.0:
                completed.append(name)

        for name in completed:
            del self._active[name]

        if not self._active:
            self._timer.stop()

    @staticmethod
    def _ease_out(t: float) -> float:
        """Cubic ease-out: 1 - (1-t)^3.

        Fast initial response, smooth deceleration.
        """
        return 1.0 - (1.0 - t) ** 3
