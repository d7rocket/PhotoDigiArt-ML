"""Tests for CollectionAnalyzer: DBSCAN clustering, UMAP projection, force attractors.

Covers clustering, 3D projection shape, edge cases (small collections),
centroid computation, force attractor generation, and output scaling.
"""

import numpy as np
import pytest

from apollo7.collection.analyzer import CollectionAnalyzer, CollectionResult


@pytest.fixture
def analyzer():
    return CollectionAnalyzer()


@pytest.fixture
def random_embeddings_10():
    """10 random 512-dim embeddings keyed by fake paths."""
    rng = np.random.RandomState(42)
    return {
        f"photo_{i}.jpg": rng.randn(512).astype(np.float32)
        for i in range(10)
    }


@pytest.fixture
def clustered_embeddings():
    """20 embeddings forming 2 clear clusters plus some noise."""
    rng = np.random.RandomState(123)
    embs = {}
    # Cluster A: 8 points near unit vector e0
    base_a = np.zeros(512, dtype=np.float32)
    base_a[0] = 1.0
    for i in range(8):
        v = base_a + rng.randn(512).astype(np.float32) * 0.05
        v /= np.linalg.norm(v)
        embs[f"cluster_a_{i}.jpg"] = v
    # Cluster B: 8 points near unit vector e1
    base_b = np.zeros(512, dtype=np.float32)
    base_b[1] = 1.0
    for i in range(8):
        v = base_b + rng.randn(512).astype(np.float32) * 0.05
        v /= np.linalg.norm(v)
        embs[f"cluster_b_{i}.jpg"] = v
    # 4 noise points scattered
    for i in range(4):
        v = rng.randn(512).astype(np.float32)
        v /= np.linalg.norm(v)
        embs[f"noise_{i}.jpg"] = v
    return embs


class TestAnalyzeBasic:
    """Test basic analyze functionality."""

    def test_analyze_basic(self, analyzer, random_embeddings_10):
        """10 random embeddings produce a CollectionResult with correct shapes."""
        result = analyzer.analyze(random_embeddings_10)
        assert isinstance(result, CollectionResult)
        assert len(result.paths) == 10
        assert result.labels.shape == (10,)
        assert result.positions_3d.shape == (10, 3)
        assert isinstance(result.n_clusters, int)
        assert result.n_clusters >= 0

    def test_umap_projection_shape(self, analyzer, random_embeddings_10):
        """positions_3d is (N, 3) float32."""
        result = analyzer.analyze(random_embeddings_10)
        assert result.positions_3d.shape == (10, 3)
        assert result.positions_3d.dtype == np.float32

    def test_dbscan_labels(self, analyzer, random_embeddings_10):
        """Labels array has length N with values >= -1."""
        result = analyzer.analyze(random_embeddings_10)
        assert result.labels.shape == (10,)
        assert np.all(result.labels >= -1)


class TestSmallCollections:
    """Test edge cases with small collections."""

    def test_umap_small_collection_2(self, analyzer):
        """2 embeddings don't crash, use fallback placement."""
        embs = {
            "a.jpg": np.random.randn(512).astype(np.float32),
            "b.jpg": np.random.randn(512).astype(np.float32),
        }
        result = analyzer.analyze(embs)
        assert result.positions_3d.shape == (2, 3)
        assert len(result.paths) == 2

    def test_single_photo(self, analyzer):
        """Single embedding handled gracefully."""
        embs = {"solo.jpg": np.random.randn(512).astype(np.float32)}
        result = analyzer.analyze(embs)
        assert result.positions_3d.shape == (1, 3)
        assert len(result.paths) == 1
        assert result.n_clusters == 0  # Can't cluster 1 point


class TestClusterCentroids:
    """Test centroid computation."""

    def test_cluster_centroids(self, analyzer, clustered_embeddings):
        """Centroids are mean of member embeddings."""
        result = analyzer.analyze(clustered_embeddings)
        # For each cluster, verify centroid is mean of members
        paths = result.paths
        for cluster_id, centroid in result.cluster_centroids.items():
            if cluster_id == -1:
                continue  # Skip noise
            member_indices = np.where(result.labels == cluster_id)[0]
            # Reconstruct member embeddings from input
            member_keys = [paths[i] for i in member_indices]
            member_embs = np.stack(
                [clustered_embeddings[k] for k in member_keys]
            )
            expected_centroid = member_embs.mean(axis=0)
            np.testing.assert_allclose(centroid, expected_centroid, atol=1e-5)


class TestForceAttractors:
    """Test force attractor generation."""

    def test_force_attractors(self, analyzer, clustered_embeddings):
        """Returns list of (position, weight) tuples, weights sum to <= 1.0."""
        result = analyzer.analyze(clustered_embeddings)
        attractors = analyzer.get_force_attractors(result)
        assert isinstance(attractors, list)
        for pos, weight in attractors:
            assert pos.shape == (3,)
            assert 0.0 < weight <= 1.0
        total_weight = sum(w for _, w in attractors)
        assert total_weight <= 1.0 + 1e-6  # Allow tiny float error


class TestUMAPScale:
    """Test output scaling."""

    def test_umap_scale(self, analyzer, random_embeddings_10):
        """Output positions are within [-6, 6] range (approx [-5, 5] with margin)."""
        result = analyzer.analyze(random_embeddings_10)
        assert np.all(result.positions_3d >= -6.0)
        assert np.all(result.positions_3d <= 6.0)
