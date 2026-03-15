"""Tests for preset interpolation (lerp) logic."""

import pytest

from apollo7.project.presets import lerp_presets


class TestLerpPresets:
    """Test preset crossfade interpolation."""

    def _make_presets(self):
        """Create two test presets with known values."""
        preset_a = {
            "sim_params": {
                "noise_frequency": 0.0,
                "speed": 0.0,
                "damping": 0.0,
            },
            "postfx_params": {
                "bloom_strength": 0.0,
            },
        }
        preset_b = {
            "sim_params": {
                "noise_frequency": 1.0,
                "speed": 2.0,
                "damping": 1.0,
            },
            "postfx_params": {
                "bloom_strength": 0.5,
            },
        }
        return preset_a, preset_b

    def test_lerp_at_zero(self):
        """t=0 returns preset_a values exactly."""
        a, b = self._make_presets()
        result = lerp_presets(a, b, 0.0)
        assert result["sim_params"]["noise_frequency"] == 0.0
        assert result["sim_params"]["speed"] == 0.0
        assert result["postfx_params"]["bloom_strength"] == 0.0

    def test_lerp_at_one(self):
        """t=1 returns preset_b values exactly."""
        a, b = self._make_presets()
        result = lerp_presets(a, b, 1.0)
        assert result["sim_params"]["noise_frequency"] == 1.0
        assert result["sim_params"]["speed"] == 2.0
        assert result["postfx_params"]["bloom_strength"] == 0.5

    def test_lerp_midpoint(self):
        """t=0.5 returns average of numeric values."""
        a, b = self._make_presets()
        result = lerp_presets(a, b, 0.5)
        assert abs(result["sim_params"]["noise_frequency"] - 0.5) < 1e-6
        assert abs(result["sim_params"]["speed"] - 1.0) < 1e-6
        assert abs(result["postfx_params"]["bloom_strength"] - 0.25) < 1e-6

    def test_lerp_tuple_values(self):
        """Gravity/wind tuples are interpolated component-wise."""
        a = {
            "sim_params": {"gravity": [0.0, 0.0, 0.0]},
            "postfx_params": {},
        }
        b = {
            "sim_params": {"gravity": [1.0, -1.0, 2.0]},
            "postfx_params": {},
        }
        result = lerp_presets(a, b, 0.5)
        grav = result["sim_params"]["gravity"]
        assert abs(grav[0] - 0.5) < 1e-6
        assert abs(grav[1] - (-0.5)) < 1e-6
        assert abs(grav[2] - 1.0) < 1e-6

    def test_lerp_missing_keys(self):
        """Key in only one preset uses 0.0 as default for the missing side."""
        a = {
            "sim_params": {"speed": 2.0},
            "postfx_params": {},
        }
        b = {
            "sim_params": {"damping": 1.0},
            "postfx_params": {},
        }
        result = lerp_presets(a, b, 0.5)
        # speed: 2.0 lerp with 0.0 at t=0.5 -> 1.0
        assert abs(result["sim_params"]["speed"] - 1.0) < 1e-6
        # damping: 0.0 lerp with 1.0 at t=0.5 -> 0.5
        assert abs(result["sim_params"]["damping"] - 0.5) < 1e-6

    def test_lerp_clamp(self):
        """t values outside [0,1] are clamped."""
        a, b = self._make_presets()
        result_neg = lerp_presets(a, b, -0.5)
        result_over = lerp_presets(a, b, 1.5)
        # Clamped to 0
        assert result_neg["sim_params"]["speed"] == 0.0
        # Clamped to 1
        assert result_over["sim_params"]["speed"] == 2.0

    def test_lerp_non_numeric(self):
        """Non-numeric values snap at t=0.5 boundary."""
        a = {
            "sim_params": {"mode": "fast"},
            "postfx_params": {},
        }
        b = {
            "sim_params": {"mode": "slow"},
            "postfx_params": {},
        }
        # t < 0.5: use A
        result_low = lerp_presets(a, b, 0.3)
        assert result_low["sim_params"]["mode"] == "fast"
        # t >= 0.5: use B
        result_high = lerp_presets(a, b, 0.5)
        assert result_high["sim_params"]["mode"] == "slow"
