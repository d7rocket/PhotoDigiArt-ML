"""Test scaffolds for Phase 5 visual quality requirements.

Covers:
- REND-05: GPU buffer sharing (positions + colors without CPU readback)
- REND-02: Saturation boost in color extraction (stub for Plan 05-02)
- REND-03: Blend alpha tuned for luminous overlap (stub for Plan 05-03)
- REND-04: Bloom tuned for white background (stub for Plan 05-03)
- DPTH-02: Warm off-white background colors (stub for Plan 05-03)
"""

from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# REND-05: GPU buffer sharing (fully tested -- Plan 05-01)
# ---------------------------------------------------------------------------


def test_buffer_sharing():
    """ParticleBuffer exposes render_positions_buffer with VERTEX usage
    and extract_positions_to_render dispatches the extract shader."""
    import wgpu.utils

    from apollo7.simulation.buffers import ParticleBuffer

    device = wgpu.utils.get_default_device()
    pb = ParticleBuffer(device, max_particles=1024)

    # render_positions_buffer property must exist and return a wgpu buffer
    buf = pb.render_positions_buffer
    assert buf is not None, "render_positions_buffer must not be None"

    # Buffer must have VERTEX usage flag
    import wgpu

    assert buf.usage & wgpu.BufferUsage.VERTEX, (
        "render_positions_buffer must have VERTEX usage flag"
    )

    # Buffer size = max_particles * 16 (vec4<f32>)
    assert buf.size == 1024 * 16, (
        f"Expected buffer size {1024 * 16}, got {buf.size}"
    )

    # extract_positions_to_render must be callable
    assert callable(
        getattr(pb, "extract_positions_to_render", None)
    ), "extract_positions_to_render method must exist"

    # Should be callable without error (no particles uploaded yet, should be a no-op or safe)
    pb.extract_positions_to_render(device)


def test_color_buffer_has_vertex_flag():
    """Color buffer must have VERTEX usage flag for direct pygfx injection."""
    import wgpu
    import wgpu.utils

    from apollo7.simulation.buffers import ParticleBuffer

    device = wgpu.utils.get_default_device()
    pb = ParticleBuffer(device, max_particles=256)

    assert pb.color_buffer.usage & wgpu.BufferUsage.VERTEX, (
        "color_buffer must have VERTEX usage flag for pygfx sharing"
    )


# ---------------------------------------------------------------------------
# REND-02: Saturation boost (stub for Plan 05-02)
# ---------------------------------------------------------------------------


class TestEnrichedColors:
    """Tests for extract_enriched_colors with saturation boost (Plan 05-02)."""

    @pytest.mark.skip(reason="Plan 05-02: color palette tuning")
    def test_saturation_boost(self):
        """Saturation is boosted by the specified factor, clamped to valid range."""
        from apollo7.extraction.color import extract_enriched_colors

        # Create an image with known HSV saturation
        h, w = 32, 32
        image = np.zeros((h, w, 3), dtype=np.float32)
        image[:, :, 0] = 200.0 / 255.0
        image[:, :, 1] = 100.0 / 255.0
        image[:, :, 2] = 50.0 / 255.0

        boost = 1.3
        result = extract_enriched_colors(image, saturation_boost=boost)
        assert result.dtype == np.float32

    @pytest.mark.skip(reason="Plan 05-02: color palette tuning")
    def test_enriched_colors_shape(self):
        """Output is (H, W, 4) float32 RGBA."""
        from apollo7.extraction.color import extract_enriched_colors

        h, w = 48, 64
        image = np.random.rand(h, w, 3).astype(np.float32)
        result = extract_enriched_colors(image)
        assert result.shape == (h, w, 4)
        assert result.dtype == np.float32


# ---------------------------------------------------------------------------
# REND-03: Blend alpha for luminous overlap (stub for Plan 05-03)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Plan 05-03: white background and tuning")
def test_blend_alpha_configured():
    """_BLEND_ALPHA should be less than 0.7 for luminous overlap effect."""
    from apollo7.gui.widgets.viewport_widget import _BLEND_ALPHA

    assert _BLEND_ALPHA < 0.7, (
        f"_BLEND_ALPHA should be < 0.7 for luminous overlap, got {_BLEND_ALPHA}"
    )


# ---------------------------------------------------------------------------
# REND-04: Bloom tuned for white background (stub for Plan 05-03)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Plan 05-03: white background and tuning")
def test_bloom_tuned_for_white():
    """BLOOM_STRENGTH_DEFAULT should be higher than 0.04 for white bg."""
    from apollo7.config.settings import BLOOM_STRENGTH_DEFAULT

    assert BLOOM_STRENGTH_DEFAULT > 0.04, (
        f"BLOOM_STRENGTH_DEFAULT should be > 0.04, got {BLOOM_STRENGTH_DEFAULT}"
    )


# ---------------------------------------------------------------------------
# DPTH-02: Warm off-white background (stub for Plan 05-03)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Plan 05-03: white background and tuning")
def test_white_background():
    """BG_COLOR_TOP and BG_COLOR_BOTTOM should be warm off-white."""
    from apollo7.config.settings import BG_COLOR_TOP, BG_COLOR_BOTTOM

    for name, color in [("BG_COLOR_TOP", BG_COLOR_TOP), ("BG_COLOR_BOTTOM", BG_COLOR_BOTTOM)]:
        hex_val = color.lstrip("#")
        r, g, b = int(hex_val[:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        brightness = (r + g + b) / 3
        assert brightness > 200, (
            f"{name} should be warm off-white (brightness > 200), got {brightness}"
        )
