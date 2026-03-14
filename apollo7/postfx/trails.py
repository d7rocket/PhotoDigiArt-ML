"""Alpha trail accumulation for particle motion history visualization.

Shows fading ghost paths of particle motion by maintaining a history
of recent positions and rendering them as additional point cloud objects
with decaying alpha. This approach is more compatible with pygfx's
rendering pipeline than framebuffer accumulation.
"""

from __future__ import annotations

import logging
from collections import deque

import numpy as np

from apollo7.config.settings import TRAIL_LENGTH_DEFAULT, TRAIL_LENGTH_RANGE

logger = logging.getLogger(__name__)


class TrailAccumulator:
    """Manages particle motion trails via ghost point history.

    Stores a ring buffer of recent particle positions and generates
    ghost point clouds with decaying alpha values. Each frame, the
    current positions are snapshot and older snapshots fade out.

    The trail_length parameter (0.0-1.0) maps to both the number of
    history frames kept and the decay rate of alpha.

    Args:
        trail_length: Trail intensity/length (0.0-1.0, default 0.5).
        max_history: Maximum number of history frames to keep.
    """

    def __init__(
        self,
        trail_length: float = TRAIL_LENGTH_DEFAULT,
        max_history: int = 20,
    ) -> None:
        self._trail_length = self._clamp(trail_length)
        self._max_history = max_history
        self._enabled = False

        # Ring buffer of (positions, colors) snapshots
        # Each entry: (positions_array, base_colors_array)
        self._history: deque[tuple[np.ndarray, np.ndarray]] = deque(
            maxlen=max_history
        )

        logger.info("Trail accumulator initialized (length=%.2f)", trail_length)

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp trail length to valid range."""
        lo, hi = TRAIL_LENGTH_RANGE
        return max(lo, min(hi, value))

    @property
    def trail_length(self) -> float:
        """Current trail length (0.0-1.0)."""
        return self._trail_length

    @trail_length.setter
    def trail_length(self, value: float) -> None:
        self._trail_length = self._clamp(value)

    @property
    def enabled(self) -> bool:
        """Whether trails are currently enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.clear()

    @property
    def decay(self) -> float:
        """Decay factor per frame derived from trail_length.

        Maps trail_length [0.0, 1.0] to decay [0.0, 0.99].
        Higher decay = longer-lasting trails.
        """
        return self._trail_length * 0.99

    @property
    def effective_frames(self) -> int:
        """Number of history frames that are visually relevant.

        Based on trail_length: 0.0 = 0 frames, 1.0 = max_history frames.
        """
        return max(0, int(self._trail_length * self._max_history))

    def push_frame(self, positions: np.ndarray, colors: np.ndarray) -> None:
        """Record a snapshot of current particle positions.

        Args:
            positions: (N, 3) float32 array of current particle positions.
            colors: (N, 4) float32 array of current particle RGBA colors.
        """
        if not self._enabled:
            return
        # Store copies to prevent external mutation
        self._history.append((positions.copy(), colors.copy()))

    def clear(self) -> None:
        """Clear all trail history."""
        self._history.clear()

    def get_trail_points(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Generate ghost point arrays with decaying alpha.

        Returns a list of (positions, colors) tuples for each history
        frame, with alpha values progressively faded based on age and
        decay factor.

        Returns:
            List of (positions, colors) tuples, oldest first.
            Empty list if trails disabled or no history.
        """
        if not self._enabled or not self._history:
            return []

        n_frames = self.effective_frames
        if n_frames <= 0:
            return []

        result: list[tuple[np.ndarray, np.ndarray]] = []
        history_list = list(self._history)

        # Take only the most recent n_frames entries
        recent = history_list[-n_frames:] if len(history_list) > n_frames else history_list

        decay = self.decay
        n = len(recent)

        for i, (positions, colors) in enumerate(recent):
            # Age: 0 = oldest shown, n-1 = most recent
            age_factor = (i + 1) / n  # 0..1, newest = 1.0
            alpha_scale = age_factor * decay

            faded_colors = colors.copy()
            faded_colors[:, 3] *= alpha_scale

            result.append((positions, faded_colors))

        return result
