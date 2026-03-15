"""Bloom post-processing effect wrapper around pygfx PhysicalBasedBloomPass.

Creates an ethereal glow around bright particles. Thin wrapper that
manages the bloom pass lifecycle on a pygfx WgpuRenderer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pygfx.renderers.wgpu import PhysicalBasedBloomPass

from apollo7.config.settings import (
    BLOOM_FILTER_RADIUS,
    BLOOM_STRENGTH_DEFAULT,
    BLOOM_STRENGTH_RANGE,
)

if TYPE_CHECKING:
    import pygfx as gfx

logger = logging.getLogger(__name__)


class BloomController:
    """Manages bloom post-processing on a pygfx renderer.

    Wraps pygfx's PhysicalBasedBloomPass with runtime strength control,
    enable/disable toggle, and parameter range clamping.

    Args:
        renderer: The pygfx WgpuRenderer to attach bloom to.
        strength: Initial bloom strength (default from settings).
    """

    def __init__(
        self,
        renderer: gfx.WgpuRenderer,
        strength: float = BLOOM_STRENGTH_DEFAULT,
    ) -> None:
        self._renderer = renderer
        self._bloom_pass = PhysicalBasedBloomPass(
            bloom_strength=self._clamp_strength(strength),
            max_mip_levels=6,
            filter_radius=BLOOM_FILTER_RADIUS,
            use_karis_average=True,
        )
        self._enabled = True

        # Add bloom pass to renderer effect passes
        existing = list(renderer.effect_passes) if renderer.effect_passes else []
        existing.append(self._bloom_pass)
        renderer.effect_passes = existing

        logger.info("Bloom initialized (strength=%.3f)", strength)

    @staticmethod
    def _clamp_strength(value: float) -> float:
        """Clamp strength to valid range."""
        lo, hi = BLOOM_STRENGTH_RANGE
        return max(lo, min(hi, value))

    def set_strength(self, value: float) -> None:
        """Update bloom strength (clamped to 0.0-3.0)."""
        value = self._clamp_strength(value)
        self._bloom_pass.bloom_strength = value

    def set_enabled(self, enabled: bool) -> None:
        """Toggle bloom effect on/off."""
        self._enabled = enabled
        self._bloom_pass.enabled = enabled

    @property
    def strength(self) -> float:
        """Current bloom strength."""
        return self._bloom_pass.bloom_strength

    @property
    def enabled(self) -> bool:
        """Whether bloom is currently enabled."""
        return self._enabled

    @property
    def bloom_pass(self) -> PhysicalBasedBloomPass:
        """Access the underlying pygfx bloom pass."""
        return self._bloom_pass
