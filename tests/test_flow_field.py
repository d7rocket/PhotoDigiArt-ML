"""Tests for shader loader and flow field shader.

Validates shader loading, concatenation, and that feature texture
references are present in flow field shader source.
"""

import math

import pytest

from apollo7.simulation.shaders import load_shader, build_combined_shader


class TestShaderLoader:
    """Verify shader loading from package directory."""

    def test_load_noise_shader(self):
        source = load_shader("noise")
        assert "perlin3d" in source
        assert "simplex3d" in source
        assert "fbm3d" in source

    def test_load_flow_field_shader(self):
        source = load_shader("flow_field")
        assert "compute_flow" in source

    def test_load_forces_shader(self):
        source = load_shader("forces")
        assert "compute_forces" in source
        assert "compute_external_forces" in source

    def test_load_integrate_shader(self):
        source = load_shader("integrate")
        assert "fn integrate" in source

    def test_load_sph_shader(self):
        source = load_shader("sph")
        assert "compute_density" in source
        assert "compute_sph_forces" in source

    def test_load_nonexistent_shader_raises(self):
        with pytest.raises(FileNotFoundError):
            load_shader("nonexistent_shader")


class TestCombinedShader:
    """Verify shader concatenation produces valid combined source."""

    def test_combined_noise_and_flow_field(self):
        source = build_combined_shader("noise", "flow_field")
        # Should contain functions from both shaders
        assert "perlin3d" in source
        assert "fbm3d" in source
        assert "compute_flow" in source
        assert "compute_flow_field" in source  # Entry point

    def test_combined_preserves_order(self):
        source = build_combined_shader("noise", "flow_field")
        # noise should appear before flow_field
        noise_pos = source.index("perlin3d")
        flow_pos = source.index("compute_flow")
        assert noise_pos < flow_pos

    def test_combined_includes_headers(self):
        source = build_combined_shader("noise", "sph")
        assert "=== noise.wgsl ===" in source
        assert "=== sph.wgsl ===" in source


class TestFlowFieldFeatureTextures:
    """Verify flow field shader references feature textures correctly."""

    def test_edge_map_texture_declared(self):
        source = load_shader("flow_field")
        assert "edge_map" in source
        assert "texture_2d<f32>" in source

    def test_depth_map_texture_declared(self):
        source = load_shader("flow_field")
        assert "depth_map" in source

    def test_texture_sampling_present(self):
        source = load_shader("flow_field")
        assert "textureSampleLevel" in source

    def test_feature_sampler_declared(self):
        source = load_shader("flow_field")
        assert "feature_sampler" in source
        assert "sampler" in source

    def test_uv_mapping_present(self):
        source = load_shader("flow_field")
        # Should map 3D position to 2D UV
        assert "pos_to_uv" in source


class TestSPHKernelMath:
    """Validate SPH kernel functions with known inputs using pure Python."""

    @staticmethod
    def poly6_kernel_py(r_sq: float, h: float) -> float:
        """Python reference implementation of poly6 kernel."""
        h_sq = h * h
        if r_sq >= h_sq:
            return 0.0
        diff = h_sq - r_sq
        coeff = 315.0 / (64.0 * math.pi * h ** 9)
        return coeff * diff ** 3

    @staticmethod
    def spiky_gradient_py(r: float, h: float) -> float:
        """Python reference implementation of spiky kernel gradient magnitude."""
        if r >= h or r < 0.0001:
            return 0.0
        diff = h - r
        coeff = -45.0 / (math.pi * h ** 6)
        return coeff * diff ** 2

    @staticmethod
    def viscosity_laplacian_py(r: float, h: float) -> float:
        """Python reference implementation of viscosity kernel laplacian."""
        if r >= h:
            return 0.0
        coeff = 45.0 / (math.pi * h ** 6)
        return coeff * (h - r)

    def test_poly6_at_distance_zero(self):
        """Poly6 kernel at r=0 should produce maximum value."""
        h = 0.1
        val = self.poly6_kernel_py(0.0, h)
        assert val > 0.0
        # This is the maximum value of the kernel
        expected = 315.0 / (64.0 * math.pi * h ** 9) * h ** 6
        assert val == pytest.approx(expected, rel=1e-5)

    def test_poly6_at_smoothing_radius(self):
        """Poly6 kernel at r=h should equal 0."""
        h = 0.1
        val = self.poly6_kernel_py(h * h, h)
        assert val == 0.0

    def test_poly6_beyond_smoothing_radius(self):
        """Poly6 kernel at r>h should equal 0."""
        h = 0.1
        val = self.poly6_kernel_py(h * h * 1.5, h)
        assert val == 0.0

    def test_poly6_monotonically_decreasing(self):
        """Poly6 kernel should decrease as distance increases."""
        h = 0.1
        prev = self.poly6_kernel_py(0.0, h)
        for r_frac in [0.2, 0.4, 0.6, 0.8, 0.99]:
            r_sq = (r_frac * h) ** 2
            val = self.poly6_kernel_py(r_sq, h)
            assert val < prev, f"Kernel not decreasing at r/h={r_frac}"
            assert val >= 0.0
            prev = val

    def test_spiky_gradient_at_distance_zero(self):
        """Spiky gradient at r=0 should return 0 (singularity guard)."""
        h = 0.1
        val = self.spiky_gradient_py(0.0, h)
        assert val == 0.0

    def test_spiky_gradient_at_smoothing_radius(self):
        """Spiky gradient at r=h should equal 0."""
        h = 0.1
        val = self.spiky_gradient_py(h, h)
        assert val == 0.0

    def test_spiky_gradient_negative(self):
        """Spiky gradient should be negative (points inward)."""
        h = 0.1
        val = self.spiky_gradient_py(0.05, h)
        assert val < 0.0

    def test_viscosity_laplacian_positive(self):
        """Viscosity laplacian should be positive within smoothing radius."""
        h = 0.1
        val = self.viscosity_laplacian_py(0.05, h)
        assert val > 0.0

    def test_viscosity_laplacian_at_smoothing_radius(self):
        """Viscosity laplacian at r=h should equal 0."""
        h = 0.1
        val = self.viscosity_laplacian_py(h, h)
        assert val == 0.0


class TestSpatialHashCellIndex:
    """Validate spatial hash cell index computation."""

    @staticmethod
    def pos_to_cell(pos, cell_size):
        """Python reference for cell index computation."""
        import math

        offset = 64.0
        return tuple(int(math.floor((p + offset) / cell_size)) for p in pos)

    @staticmethod
    def cell_to_hash(cell, grid_size=128):
        """Python reference for hash from cell coords."""
        cx = cell[0] % grid_size
        cy = cell[1] % grid_size
        cz = cell[2] % grid_size
        return cx + cy * grid_size + cz * grid_size * grid_size

    def test_origin_maps_to_center_cell(self):
        """Position (0,0,0) should map to the center of the grid."""
        cell = self.pos_to_cell((0.0, 0.0, 0.0), 1.0)
        assert cell == (64, 64, 64)

    def test_negative_position(self):
        """Negative positions should map to lower cell indices."""
        cell = self.pos_to_cell((-10.0, -10.0, -10.0), 1.0)
        assert cell == (54, 54, 54)

    def test_hash_unique_for_different_cells(self):
        """Different cells should produce different hashes."""
        h1 = self.cell_to_hash((64, 64, 64))
        h2 = self.cell_to_hash((65, 64, 64))
        h3 = self.cell_to_hash((64, 65, 64))
        assert h1 != h2
        assert h1 != h3
        assert h2 != h3

    def test_cell_size_affects_resolution(self):
        """Larger cell size should produce fewer unique cells."""
        cell_small = self.pos_to_cell((1.0, 0.0, 0.0), 0.1)
        cell_large = self.pos_to_cell((1.0, 0.0, 0.0), 1.0)
        # With smaller cells, position maps to higher cell index
        assert cell_small[0] > cell_large[0]
