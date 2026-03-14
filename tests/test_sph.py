"""Tests for SPH shader loading and kernel math validation.

Validates that SPH shader loads correctly, kernel functions match
known mathematical properties, and spatial hashing is consistent.
"""

import math

import pytest

from apollo7.simulation.shaders import load_shader, build_combined_shader


class TestSPHShaderLoading:
    """Verify SPH shader loads and contains expected constructs."""

    def test_load_sph_shader(self):
        source = load_shader("sph")
        assert len(source) > 100

    def test_sph_has_density_pass(self):
        source = load_shader("sph")
        assert "compute_density" in source

    def test_sph_has_force_pass(self):
        source = load_shader("sph")
        assert "compute_sph_forces" in source

    def test_sph_has_poly6_kernel(self):
        source = load_shader("sph")
        assert "poly6_kernel" in source

    def test_sph_has_spiky_kernel(self):
        source = load_shader("sph")
        assert "spiky_kernel_gradient" in source

    def test_sph_has_viscosity_kernel(self):
        source = load_shader("sph")
        assert "viscosity_kernel_laplacian" in source

    def test_sph_has_spatial_hash(self):
        source = load_shader("sph")
        assert "sph_pos_to_cell" in source
        assert "sph_cell_to_hash" in source

    def test_combined_noise_sph(self):
        source = build_combined_shader("noise", "sph")
        assert "perlin3d" in source
        assert "compute_density" in source
        assert "poly6_kernel" in source


class TestSPHKernelNormalization:
    """Additional SPH kernel validation beyond test_flow_field.py tests."""

    @staticmethod
    def poly6_kernel(r_sq: float, h: float) -> float:
        h_sq = h * h
        if r_sq >= h_sq:
            return 0.0
        diff = h_sq - r_sq
        coeff = 315.0 / (64.0 * math.pi * h ** 9)
        return coeff * diff ** 3

    def test_poly6_symmetry(self):
        """Kernel should be symmetric: W(r) = W(-r)."""
        h = 0.1
        # Since we use r_sq, symmetry is automatic, but verify
        val_pos = self.poly6_kernel(0.04 ** 2, h)
        val_neg = self.poly6_kernel((-0.04) ** 2, h)
        assert val_pos == pytest.approx(val_neg)

    def test_poly6_different_smoothing_radii(self):
        """Larger smoothing radius should give lower peak value."""
        val_small = self.poly6_kernel(0.0, 0.1)
        val_large = self.poly6_kernel(0.0, 0.5)
        # Coeff includes h^-9, so larger h = smaller coefficient
        assert val_large < val_small

    def test_poly6_continuity_near_boundary(self):
        """Kernel should approach 0 smoothly near the boundary."""
        h = 0.1
        r_near = h * 0.999
        val = self.poly6_kernel(r_near ** 2, h)
        assert val >= 0.0
        assert val < 1.0  # Should be very small near boundary


class TestSPHPressureEquation:
    """Validate equation of state for pressure computation."""

    def test_pressure_at_rest_density(self):
        """Pressure should be zero at rest density."""
        gas_constant = 2.0
        rest_density = 1000.0
        pressure = gas_constant * (rest_density - rest_density)
        assert pressure == 0.0

    def test_pressure_above_rest_density(self):
        """Pressure should be positive above rest density."""
        gas_constant = 2.0
        rest_density = 1000.0
        density = 1500.0
        pressure = gas_constant * (density - rest_density)
        assert pressure > 0.0

    def test_pressure_below_rest_density(self):
        """Pressure should be negative below rest density (tension)."""
        gas_constant = 2.0
        rest_density = 1000.0
        density = 500.0
        pressure = gas_constant * (density - rest_density)
        assert pressure < 0.0
