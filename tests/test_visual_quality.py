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

    def test_saturation_boost(self):
        """Saturation is boosted by the specified factor, clamped to valid range."""
        import cv2

        from apollo7.extraction.color import extract_enriched_colors

        # Create an image with known HSV saturation
        h, w = 32, 32
        image = np.zeros((h, w, 3), dtype=np.float32)
        image[:, :, 0] = 200.0 / 255.0  # R
        image[:, :, 1] = 100.0 / 255.0  # G
        image[:, :, 2] = 50.0 / 255.0   # B

        boost = 1.3
        result = extract_enriched_colors(image, saturation_boost=boost)
        assert result.dtype == np.float32

        # Compare saturation: boosted image should have higher saturation
        orig_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        orig_hsv = cv2.cvtColor(orig_uint8, cv2.COLOR_RGB2HSV)
        orig_sat = orig_hsv[0, 0, 1]

        result_rgb_uint8 = (np.clip(result[:, :, :3], 0, 1) * 255).astype(np.uint8)
        result_hsv = cv2.cvtColor(result_rgb_uint8, cv2.COLOR_RGB2HSV)
        result_sat = result_hsv[0, 0, 1]

        expected_sat = min(int(orig_sat * boost), 255)
        assert abs(int(result_sat) - expected_sat) <= 2, (
            f"Expected saturation ~{expected_sat}, got {result_sat}"
        )

    def test_enriched_colors_shape(self):
        """Output is (H, W, 4) float32 RGBA."""
        from apollo7.extraction.color import extract_enriched_colors

        h, w = 48, 64
        image = np.random.rand(h, w, 3).astype(np.float32)
        result = extract_enriched_colors(image)

        assert result.shape == (h, w, 4)
        assert result.dtype == np.float32
        # Alpha channel should be 1.0
        np.testing.assert_array_equal(result[:, :, 3], 1.0)
        # RGB values in [0, 1]
        assert result[:, :, :3].min() >= 0.0
        assert result[:, :, :3].max() <= 1.0


# ---------------------------------------------------------------------------
# REND-03: Blend alpha for luminous overlap (stub for Plan 05-03)
# ---------------------------------------------------------------------------


def test_blend_alpha_configured():
    """_BLEND_ALPHA should be less than 1.0 for luminous overlap on white bg."""
    from apollo7.gui.widgets.viewport_widget import _BLEND_ALPHA

    assert 0.7 <= _BLEND_ALPHA < 1.0, (
        f"_BLEND_ALPHA should be in [0.7, 1.0) for visible particles on white bg, got {_BLEND_ALPHA}"
    )


# ---------------------------------------------------------------------------
# REND-04: Bloom tuned for white background (stub for Plan 05-03)
# ---------------------------------------------------------------------------


def test_bloom_tuned_for_white():
    """BLOOM_STRENGTH_DEFAULT should be >= 0.3 and filter radius >= 0.01 for white bg."""
    from apollo7.config.settings import BLOOM_FILTER_RADIUS, BLOOM_STRENGTH_DEFAULT

    assert BLOOM_STRENGTH_DEFAULT >= 0.3, (
        f"BLOOM_STRENGTH_DEFAULT should be >= 0.3, got {BLOOM_STRENGTH_DEFAULT}"
    )
    assert BLOOM_FILTER_RADIUS >= 0.01, (
        f"BLOOM_FILTER_RADIUS should be >= 0.01, got {BLOOM_FILTER_RADIUS}"
    )


# ---------------------------------------------------------------------------
# DPTH-02: Warm off-white background (stub for Plan 05-03)
# ---------------------------------------------------------------------------


def test_white_background():
    """BG_COLOR_TOP and BG_COLOR_BOTTOM should be warm off-white."""
    from apollo7.config.settings import BG_COLOR_TOP, BG_COLOR_BOTTOM

    for name, color in [("BG_COLOR_TOP", BG_COLOR_TOP), ("BG_COLOR_BOTTOM", BG_COLOR_BOTTOM)]:
        assert color.startswith("#F"), (
            f"{name} should start with #F (light color), got {color}"
        )
        assert color != "#1a1a1a", (
            f"{name} should not be dark default #1a1a1a"
        )
        hex_val = color.lstrip("#")
        r, g, b = int(hex_val[:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        brightness = (r + g + b) / 3
        assert brightness > 200, (
            f"{name} should be warm off-white (brightness > 200), got {brightness}"
        )
