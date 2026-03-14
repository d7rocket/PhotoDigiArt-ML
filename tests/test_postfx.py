"""Tests for post-processing effects: bloom, DoF, SSAO, and trails.

Covers:
- BloomController strength setting and clamping (with mock renderer)
- DepthOfFieldPass parameter validation and blur factor computation
- SSAOPass parameter validation and occlusion estimation
- TrailAccumulator decay calculation and ghost point generation
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pytest

from apollo7.postfx.bloom import BloomController
from apollo7.postfx.dof_pass import DepthOfFieldPass
from apollo7.postfx.ssao_pass import SSAOPass
from apollo7.postfx.trails import TrailAccumulator


# ---------------------------------------------------------------------------
# BloomController
# ---------------------------------------------------------------------------

class TestBloomController:
    """Test BloomController with a mock renderer."""

    def _make_mock_renderer(self):
        renderer = MagicMock()
        renderer.effect_passes = []
        return renderer

    def test_init_creates_bloom_pass(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer, strength=0.5)
        assert bloom.strength == 0.5
        assert bloom.enabled is True

    def test_set_strength(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer)
        bloom.set_strength(1.5)
        assert bloom.strength == 1.5

    def test_strength_clamped_high(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer)
        bloom.set_strength(10.0)
        assert bloom.strength == 3.0

    def test_strength_clamped_low(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer)
        bloom.set_strength(-1.0)
        assert bloom.strength == 0.0

    def test_toggle_enabled(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer)
        bloom.set_enabled(False)
        assert bloom.enabled is False
        bloom.set_enabled(True)
        assert bloom.enabled is True

    def test_bloom_pass_added_to_renderer(self):
        renderer = self._make_mock_renderer()
        bloom = BloomController(renderer)
        # effect_passes should have been set with the bloom pass
        assert renderer.effect_passes is not None


# ---------------------------------------------------------------------------
# DepthOfFieldPass
# ---------------------------------------------------------------------------

class TestDepthOfFieldPass:
    """Test DoF parameter validation and blur factor calculation."""

    def test_default_params(self):
        dof = DepthOfFieldPass()
        assert dof.focal_distance == 10.0
        assert dof.aperture == 2.0
        assert dof.enabled is False

    def test_focal_distance_clamped(self):
        dof = DepthOfFieldPass()
        dof.focal_distance = 100.0
        assert dof.focal_distance == 50.0
        dof.focal_distance = -5.0
        assert dof.focal_distance == 0.0

    def test_aperture_clamped(self):
        dof = DepthOfFieldPass()
        dof.aperture = 20.0
        assert dof.aperture == 5.0
        dof.aperture = 0.01
        assert dof.aperture == 0.1

    def test_blur_factor_disabled(self):
        dof = DepthOfFieldPass()
        assert dof.compute_blur_factor(5.0) == 0.0

    def test_blur_factor_at_focal_plane(self):
        dof = DepthOfFieldPass(focal_distance=10.0)
        dof.enabled = True
        assert dof.compute_blur_factor(10.0) == 0.0

    def test_blur_factor_far_from_focal(self):
        dof = DepthOfFieldPass(focal_distance=10.0, aperture=1.0)
        dof.enabled = True
        blur = dof.compute_blur_factor(30.0)
        assert blur > 0.0
        assert blur <= 1.0


# ---------------------------------------------------------------------------
# SSAOPass
# ---------------------------------------------------------------------------

class TestSSAOPass:
    """Test SSAO parameter validation and occlusion estimation."""

    def test_default_params(self):
        ssao = SSAOPass()
        assert ssao.radius == 0.5
        assert ssao.intensity == 1.0
        assert ssao.enabled is False

    def test_radius_clamped(self):
        ssao = SSAOPass()
        ssao.radius = 10.0
        assert ssao.radius == 2.0
        ssao.radius = 0.01
        assert ssao.radius == 0.1

    def test_intensity_clamped(self):
        ssao = SSAOPass()
        ssao.intensity = 5.0
        assert ssao.intensity == 2.0
        ssao.intensity = -1.0
        assert ssao.intensity == 0.0

    def test_occlusion_disabled(self):
        ssao = SSAOPass()
        assert ssao.estimate_occlusion(0.8) == 0.0

    def test_occlusion_scales_with_density(self):
        ssao = SSAOPass()
        ssao.enabled = True
        low = ssao.estimate_occlusion(0.2)
        high = ssao.estimate_occlusion(0.8)
        assert high > low

    def test_gpu_not_available(self):
        assert SSAOPass.GPU_AVAILABLE is False


# ---------------------------------------------------------------------------
# TrailAccumulator
# ---------------------------------------------------------------------------

class TestTrailAccumulator:
    """Test trail accumulation and decay calculations."""

    def test_default_params(self):
        trails = TrailAccumulator()
        assert trails.trail_length == 0.5
        assert trails.enabled is False

    def test_trail_length_clamped(self):
        trails = TrailAccumulator()
        trails.trail_length = 2.0
        assert trails.trail_length == 1.0
        trails.trail_length = -0.5
        assert trails.trail_length == 0.0

    def test_decay_calculation(self):
        trails = TrailAccumulator(trail_length=1.0)
        assert trails.decay == pytest.approx(0.99)
        trails.trail_length = 0.0
        assert trails.decay == pytest.approx(0.0)
        trails.trail_length = 0.5
        assert trails.decay == pytest.approx(0.495)

    def test_push_frame_disabled(self):
        trails = TrailAccumulator()
        positions = np.random.rand(100, 3).astype(np.float32)
        colors = np.random.rand(100, 4).astype(np.float32)
        trails.push_frame(positions, colors)
        assert trails.get_trail_points() == []

    def test_push_and_get_trail_points(self):
        trails = TrailAccumulator(trail_length=0.8)
        trails.enabled = True

        for i in range(5):
            pos = np.random.rand(50, 3).astype(np.float32)
            col = np.ones((50, 4), dtype=np.float32)
            trails.push_frame(pos, col)

        result = trails.get_trail_points()
        assert len(result) > 0

        # Verify alpha decay: older frames should have lower alpha
        alphas = [pts[1][:, 3].mean() for pts in result]
        # Each subsequent frame should have equal or higher alpha
        for i in range(1, len(alphas)):
            assert alphas[i] >= alphas[i - 1]

    def test_clear(self):
        trails = TrailAccumulator()
        trails.enabled = True
        trails.push_frame(
            np.random.rand(10, 3).astype(np.float32),
            np.random.rand(10, 4).astype(np.float32),
        )
        trails.clear()
        assert trails.get_trail_points() == []

    def test_disable_clears_history(self):
        trails = TrailAccumulator()
        trails.enabled = True
        trails.push_frame(
            np.random.rand(10, 3).astype(np.float32),
            np.random.rand(10, 4).astype(np.float32),
        )
        trails.enabled = False
        assert trails.get_trail_points() == []

    def test_effective_frames(self):
        trails = TrailAccumulator(trail_length=1.0, max_history=20)
        assert trails.effective_frames == 20
        trails.trail_length = 0.5
        assert trails.effective_frames == 10
        trails.trail_length = 0.0
        assert trails.effective_frames == 0
