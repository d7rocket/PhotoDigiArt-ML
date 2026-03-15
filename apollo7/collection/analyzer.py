"""Collection analyzer: DBSCAN clustering and UMAP 3D projection.

Clusters photo embeddings to identify natural groupings,
projects 512-dim CLIP embeddings to 3D positions via UMAP,
and generates force attractor data for the simulation engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result of collection analysis.

    Attributes:
        paths: Photo paths in order.
        labels: DBSCAN cluster labels (-1 = noise/outlier).
        positions_3d: (N, 3) float32 UMAP projections scaled to [-5, 5].
        cluster_centroids: cluster_id -> centroid in original 512-dim space.
        cluster_positions_3d: cluster_id -> centroid in 3D UMAP space.
        n_clusters: Number of clusters (excluding noise label -1).
    """

    paths: list[str]
    labels: np.ndarray
    positions_3d: np.ndarray
    cluster_centroids: dict[int, np.ndarray] = field(default_factory=dict)
    cluster_positions_3d: dict[int, np.ndarray] = field(default_factory=dict)
    n_clusters: int = 0


class CollectionAnalyzer:
    """Analyzes photo collections via DBSCAN clustering and UMAP projection.

    Consumes 512-dim CLIP embeddings, identifies natural clusters,
    projects to 3D for viewport visualization, and produces force
    attractor data for the simulation engine.
    """

    def analyze(self, embeddings: dict[str, np.ndarray]) -> CollectionResult:
        """Cluster and project embeddings to 3D.

        Args:
            embeddings: Mapping from photo path to 512-dim embedding vector.

        Returns:
            CollectionResult with clustering, 3D positions, and centroids.
        """
        paths = list(embeddings.keys())
        n = len(paths)

        if n == 0:
            return CollectionResult(
                paths=[],
                labels=np.array([], dtype=np.int32),
                positions_3d=np.empty((0, 3), dtype=np.float32),
                n_clusters=0,
            )

        # Stack embeddings into (N, 512) matrix
        emb_matrix = np.stack([embeddings[p] for p in paths]).astype(np.float32)

        # --- DBSCAN clustering ---
        labels = self._cluster(emb_matrix)

        # --- UMAP 3D projection ---
        positions_3d = self._project_3d(emb_matrix, n)

        # --- Compute cluster centroids ---
        unique_labels = set(labels.tolist())
        unique_labels.discard(-1)  # Remove noise label
        n_clusters = len(unique_labels)

        cluster_centroids: dict[int, np.ndarray] = {}
        cluster_positions_3d: dict[int, np.ndarray] = {}

        for cluster_id in unique_labels:
            member_mask = labels == cluster_id
            # Centroid in original 512-dim space
            cluster_centroids[cluster_id] = emb_matrix[member_mask].mean(axis=0)
            # Centroid in 3D UMAP space
            cluster_positions_3d[cluster_id] = positions_3d[member_mask].mean(axis=0)

        logger.info(
            "Collection analyzed: %d photos, %d clusters, %d outliers",
            n,
            n_clusters,
            int(np.sum(labels == -1)),
        )

        return CollectionResult(
            paths=paths,
            labels=labels,
            positions_3d=positions_3d,
            cluster_centroids=cluster_centroids,
            cluster_positions_3d=cluster_positions_3d,
            n_clusters=n_clusters,
        )

    def _cluster(self, emb_matrix: np.ndarray) -> np.ndarray:
        """Run DBSCAN clustering on embeddings.

        Args:
            emb_matrix: (N, 512) float32 embedding matrix.

        Returns:
            (N,) int32 array of cluster labels (-1 = noise).
        """
        from sklearn.cluster import DBSCAN

        n = emb_matrix.shape[0]
        if n < 2:
            return np.array([-1] * n, dtype=np.int32)

        db = DBSCAN(eps=0.3, min_samples=2, metric="cosine")
        labels = db.fit_predict(emb_matrix)
        return labels.astype(np.int32)

    def _project_3d(self, emb_matrix: np.ndarray, n: int) -> np.ndarray:
        """Project embeddings to 3D positions.

        For small collections (< 3), uses simple fallback placement.
        Otherwise uses UMAP with n_components=3.

        Args:
            emb_matrix: (N, 512) float32 embedding matrix.
            n: Number of embeddings.

        Returns:
            (N, 3) float32 positions scaled to [-5, 5].
        """
        if n == 1:
            return np.array([[0.0, 0.0, 0.0]], dtype=np.float32)

        if n == 2:
            return np.array([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32)

        # UMAP projection for 3+ points
        import umap

        n_neighbors = min(15, n - 1)
        reducer = umap.UMAP(
            n_components=3,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            random_state=42,
        )
        positions = reducer.fit_transform(emb_matrix).astype(np.float32)

        # Scale to [-5, 5] range
        positions = self._scale_positions(positions)

        return positions

    def _scale_positions(self, positions: np.ndarray) -> np.ndarray:
        """Scale 3D positions to [-5, 5] range per axis.

        Args:
            positions: (N, 3) float32 raw UMAP output.

        Returns:
            (N, 3) float32 positions scaled to [-5, 5].
        """
        for axis in range(3):
            col = positions[:, axis]
            col_min = col.min()
            col_max = col.max()
            col_range = col_max - col_min
            if col_range < 1e-8:
                positions[:, axis] = 0.0
            else:
                # Normalize to [0, 1] then scale to [-5, 5]
                positions[:, axis] = (col - col_min) / col_range * 10.0 - 5.0
        return positions

    def get_force_attractors(
        self, result: CollectionResult
    ) -> list[tuple[np.ndarray, float]]:
        """Generate force attractor data from collection analysis.

        For each cluster (excluding noise), returns the 3D centroid
        position and a weight proportional to cluster size.

        Args:
            result: CollectionResult from analyze().

        Returns:
            List of (3D position, weight) tuples. Weights are
            cluster_size / total_size, summing to <= 1.0.
        """
        if result.n_clusters == 0:
            return []

        total = len(result.paths)
        attractors: list[tuple[np.ndarray, float]] = []

        for cluster_id, pos_3d in result.cluster_positions_3d.items():
            member_count = int(np.sum(result.labels == cluster_id))
            weight = member_count / total
            attractors.append((pos_3d.copy(), weight))

        return attractors
