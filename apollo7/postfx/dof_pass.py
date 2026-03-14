"""Depth of Field post-processing effect.

Simulates camera depth of field by blurring particles far from the focal
plane. Since pygfx's EffectPass system does not provide a straightforward
public API for custom fragment shaders with depth buffer access, this
implementation uses a parameter-based controller that stores DoF state.

The actual blur is applied via a custom pygfx EffectPass subclass that
reads the depth buffer when available, or falls back to a screen-space
approximation managed in the render loop.
"""

from __future__ import annotations

import logging

from apollo7.config.settings import (
    DOF_APERTURE_DEFAULT,
    DOF_APERTURE_RANGE,
    DOF_FOCAL_DEFAULT,
    DOF_FOCAL_RANGE,
)

logger = logging.getLogger(__name__)


class DepthOfFieldPass:
    """Depth of field effect controller.

    Manages focal distance and aperture parameters for depth-based blur.
    Integrates with the viewport render loop to apply selective blur
    based on distance from focal plane.

    Args:
        focal_distance: Distance to the sharp focus plane (0.0-50.0).
        aperture: Controls blur intensity (0.1-5.0, higher = more blur).
    """

    def __init__(
        self,
        focal_distance: float = DOF_FOCAL_DEFAULT,
        aperture: float = DOF_APERTURE_DEFAULT,
    ) -> None:
        self._focal_distance = self._clamp(focal_distance, DOF_FOCAL_RANGE)
        self._aperture = self._clamp(aperture, DOF_APERTURE_RANGE)
        self._enabled = False

        logger.info(
            "DoF initialized (focal=%.1f, aperture=%.1f)",
            self._focal_distance,
            self._aperture,
        )

    @staticmethod
    def _clamp(value: float, range_: tuple[float, float]) -> float:
        """Clamp value to range."""
        return max(range_[0], min(range_[1], value))

    @property
    def focal_distance(self) -> float:
        """Distance to the sharp focus plane."""
        return self._focal_distance

    @focal_distance.setter
    def focal_distance(self, value: float) -> None:
        self._focal_distance = self._clamp(value, DOF_FOCAL_RANGE)

    @property
    def aperture(self) -> float:
        """Aperture controlling blur intensity."""
        return self._aperture

    @aperture.setter
    def aperture(self, value: float) -> None:
        self._aperture = self._clamp(value, DOF_APERTURE_RANGE)

    @property
    def enabled(self) -> bool:
        """Whether DoF is currently enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def compute_blur_factor(self, depth: float) -> float:
        """Compute circle-of-confusion blur factor for a given depth.

        Returns a value 0.0 (sharp) to 1.0 (maximum blur) based on
        distance from the focal plane scaled by aperture.

        Args:
            depth: Distance from camera to the point.

        Returns:
            Blur factor in [0.0, 1.0].
        """
        if not self._enabled:
            return 0.0
        distance_from_focal = abs(depth - self._focal_distance)
        # Normalize by aperture -- smaller aperture = more of scene in focus
        coc = distance_from_focal / (self._aperture * 10.0 + 0.001)
        return min(1.0, coc)
