"""Screen-Space Ambient Occlusion (SSAO) post-processing effect.

SSAO darkens areas where particles are densely packed, creating a
perception of depth and volume. Currently implemented as a parameter
controller -- full GPU-based SSAO requires depth buffer access from
pygfx's rendering pipeline which is not yet publicly exposed for
custom effect passes.

Known limitation: Full screen-space SSAO requires depth buffer texture
access from the pygfx render pipeline. The current pygfx EffectPass API
provides USES_DEPTH=True on PhysicalBasedBloomPass but the depth texture
binding is internal. This controller stores parameters for future
GPU integration and provides a CPU-side density estimation fallback.
"""

from __future__ import annotations

import logging

from apollo7.config.settings import (
    SSAO_INTENSITY_DEFAULT,
    SSAO_INTENSITY_RANGE,
    SSAO_RADIUS_DEFAULT,
    SSAO_RADIUS_RANGE,
)

logger = logging.getLogger(__name__)


class SSAOPass:
    """Screen-space ambient occlusion parameter controller.

    Stores SSAO parameters (radius, intensity) and provides a
    density-based occlusion estimation for point clouds.

    Note: Full GPU SSAO is deferred pending pygfx depth buffer API.
    The controller is ready for integration when the API becomes
    available.

    Args:
        radius: Sampling radius for occlusion detection (0.1-2.0).
        intensity: Occlusion darkening multiplier (0.0-2.0).
    """

    # Flag indicating GPU SSAO is not yet available
    GPU_AVAILABLE: bool = False

    def __init__(
        self,
        radius: float = SSAO_RADIUS_DEFAULT,
        intensity: float = SSAO_INTENSITY_DEFAULT,
    ) -> None:
        self._radius = self._clamp(radius, SSAO_RADIUS_RANGE)
        self._intensity = self._clamp(intensity, SSAO_INTENSITY_RANGE)
        self._enabled = False

        if not self.GPU_AVAILABLE:
            logger.info(
                "SSAO initialized in parameter-only mode "
                "(GPU SSAO pending pygfx depth buffer API)"
            )

    @staticmethod
    def _clamp(value: float, range_: tuple[float, float]) -> float:
        """Clamp value to range."""
        return max(range_[0], min(range_[1], value))

    @property
    def radius(self) -> float:
        """Sampling radius for occlusion detection."""
        return self._radius

    @radius.setter
    def radius(self, value: float) -> None:
        self._radius = self._clamp(value, SSAO_RADIUS_RANGE)

    @property
    def intensity(self) -> float:
        """Occlusion darkening multiplier."""
        return self._intensity

    @intensity.setter
    def intensity(self, value: float) -> None:
        self._intensity = self._clamp(value, SSAO_INTENSITY_RANGE)

    @property
    def enabled(self) -> bool:
        """Whether SSAO is currently enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def estimate_occlusion(self, density: float) -> float:
        """Estimate ambient occlusion from local particle density.

        CPU-side fallback: higher density = more occlusion.

        Args:
            density: Normalized local particle density (0.0-1.0).

        Returns:
            Occlusion factor in [0.0, 1.0] where 1.0 = fully occluded.
        """
        if not self._enabled:
            return 0.0
        # Scale density by radius (larger radius = more neighbors counted)
        # and intensity (amplification factor)
        occlusion = density * self._radius * self._intensity
        return min(1.0, max(0.0, occlusion))
