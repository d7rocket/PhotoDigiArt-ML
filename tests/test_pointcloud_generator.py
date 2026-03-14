"""Tests for point cloud generation, LOD, and layout modes."""

from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Depth-projected cloud tests
# ---------------------------------------------------------------------------


class TestDepthProjectedCloud:
    """Tests for generate_depth_projected_cloud."""

    def test_depth_projected_shape(self):
        """Returns (positions, colors, sizes) with correct shapes."""
        from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud

        image = np.random.rand(50, 60, 3).astype(np.float32)
        depth_map = np.random.rand(50, 60).astype(np.float32)

        positions, colors, sizes = generate_depth_projected_cloud(image, depth_map)

        n = 50 * 60
        assert positions.shape == (n, 3)
        assert colors.shape == (n, 4)
        assert sizes.shape == (n,)

    def test_depth_projected_positions(self):
        """Positions are (N,3) float32, N = H*W."""
        from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud

        h, w = 40, 80
        image = np.random.rand(h, w, 3).astype(np.float32)
        depth_map = np.random.rand(h, w).astype(np.float32)

        positions, _, _ = generate_depth_projected_cloud(image, depth_map)

        assert positions.shape == (h * w, 3)
        assert positions.dtype == np.float32

    def test_depth_projected_colors(self):
        """Colors are (N,4) float32 with alpha=1.0."""
        from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud

        image = np.random.rand(30, 30, 3).astype(np.float32)
        depth_map = np.random.rand(30, 30).astype(np.float32)

        _, colors, _ = generate_depth_projected_cloud(image, depth_map)

        assert colors.dtype == np.float32
        assert np.allclose(colors[:, 3], 1.0)

    def test_depth_exaggeration(self):
        """z-range increases with exaggeration factor."""
        from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud

        image = np.random.rand(20, 20, 3).astype(np.float32)
        depth_map = np.random.rand(20, 20).astype(np.float32)

        pos_low, _, _ = generate_depth_projected_cloud(
            image, depth_map, depth_exaggeration=1.0
        )
        pos_high, _, _ = generate_depth_projected_cloud(
            image, depth_map, depth_exaggeration=8.0
        )

        z_range_low = pos_low[:, 2].max() - pos_low[:, 2].min()
        z_range_high = pos_high[:, 2].max() - pos_high[:, 2].min()

        assert z_range_high > z_range_low


# ---------------------------------------------------------------------------
# Feature-clustered cloud tests
# ---------------------------------------------------------------------------


class TestFeatureClusteredCloud:
    """Tests for generate_feature_clustered_cloud."""

    def test_feature_clustered_shape(self):
        """Returns valid (positions, colors, sizes) tuple."""
        from apollo7.extraction.base import ExtractionResult
        from apollo7.pointcloud.feature_cluster import generate_feature_clustered_cloud

        image = np.random.rand(40, 40, 3).astype(np.float32)
        features = {
            "color": ExtractionResult(
                extractor_name="color",
                data={"dominant_colors": [(255, 0, 0), (0, 255, 0), (0, 0, 255)]},
                arrays={},
            )
        }

        positions, colors, sizes = generate_feature_clustered_cloud(image, features)

        assert positions.ndim == 2
        assert positions.shape[1] == 3
        assert colors.ndim == 2
        assert colors.shape[1] == 4
        assert sizes.ndim == 1
        assert positions.shape[0] == colors.shape[0] == sizes.shape[0]
        assert positions.shape[0] > 0


# ---------------------------------------------------------------------------
# LOD decimation tests
# ---------------------------------------------------------------------------


class TestLOD:
    """Tests for decimate_points."""

    def test_lod_reduces_points(self):
        """decimate_points with factor=0.5 returns roughly half the points."""
        from apollo7.pointcloud.lod import decimate_points

        n = 10000
        positions = np.random.rand(n, 3).astype(np.float32) * 10
        colors = np.random.rand(n, 4).astype(np.float32)
        sizes = np.full(n, 2.0, dtype=np.float32)

        dec_pos, dec_col, dec_sizes = decimate_points(positions, colors, sizes, factor=0.5)

        # Should be roughly half -- allow wide tolerance for grid-based decimation
        assert dec_pos.shape[0] < n
        assert dec_pos.shape[0] > n * 0.1  # but not too aggressive
        assert dec_col.shape[0] == dec_pos.shape[0]
        assert dec_sizes.shape[0] == dec_pos.shape[0]

    def test_lod_preserves_bounds(self):
        """Decimated cloud has similar spatial extent as original."""
        from apollo7.pointcloud.lod import decimate_points

        n = 5000
        positions = np.random.rand(n, 3).astype(np.float32) * 20
        colors = np.random.rand(n, 4).astype(np.float32)
        sizes = np.full(n, 2.0, dtype=np.float32)

        dec_pos, _, _ = decimate_points(positions, colors, sizes, factor=0.5)

        orig_extent = positions.max(axis=0) - positions.min(axis=0)
        dec_extent = dec_pos.max(axis=0) - dec_pos.min(axis=0)

        # Spatial extent should be at least 70% of original
        for i in range(3):
            assert dec_extent[i] > orig_extent[i] * 0.7
