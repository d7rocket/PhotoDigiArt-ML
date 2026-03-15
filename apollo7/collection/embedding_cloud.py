"""Embedding cloud renderer for 3D viewport visualization.

Renders photo embeddings as colored points in the viewport scene,
with cluster-based coloring, click-to-isolate interaction, and
toggle visibility controls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pygfx as gfx

from apollo7.collection.analyzer import CollectionResult

logger = logging.getLogger(__name__)

# 10 distinct colors for cluster visualization (avoiding red/green for accessibility)
# Uses blue, orange, teal, purple, gold, cyan, magenta, coral, indigo, lime-yellow
CLUSTER_PALETTE: list[tuple[float, float, float]] = [
    (0.30, 0.50, 0.90),  # Blue
    (0.95, 0.55, 0.20),  # Orange
    (0.20, 0.75, 0.70),  # Teal
    (0.65, 0.35, 0.80),  # Purple
    (0.90, 0.75, 0.20),  # Gold
    (0.25, 0.80, 0.95),  # Cyan
    (0.85, 0.35, 0.65),  # Magenta
    (0.95, 0.50, 0.45),  # Coral
    (0.40, 0.30, 0.75),  # Indigo
    (0.75, 0.80, 0.25),  # Lime-yellow
]

# Neutral gray for noise/outlier points
_NOISE_COLOR = (0.5, 0.5, 0.5, 0.6)

# Point size for embedding cloud (larger than sculpture particles)
_CLOUD_POINT_SIZE = 8.0


def create_embedding_cloud(result: CollectionResult) -> "gfx.Points":
    """Create a pygfx Points object visualizing the embedding cloud.

    Points are colored by cluster label using CLUSTER_PALETTE.
    Noise points (label -1) are neutral gray with reduced alpha.

    Args:
        result: CollectionResult from CollectionAnalyzer.analyze().

    Returns:
        pygfx.Points object ready to add to a scene.
    """
    import pygfx as gfx

    n = len(result.paths)
    if n == 0:
        positions = np.empty((0, 3), dtype=np.float32)
        colors = np.empty((0, 4), dtype=np.float32)
        sizes = np.empty((0,), dtype=np.float32)
    else:
        positions = result.positions_3d.astype(np.float32)

        # Assign colors by cluster label
        colors = np.zeros((n, 4), dtype=np.float32)
        for i, label in enumerate(result.labels):
            if label == -1:
                colors[i] = _NOISE_COLOR
            else:
                rgb = CLUSTER_PALETTE[int(label) % len(CLUSTER_PALETTE)]
                colors[i] = (*rgb, 1.0)

        sizes = np.full(n, _CLOUD_POINT_SIZE, dtype=np.float32)

    geometry = gfx.Geometry(
        positions=positions,
        colors=colors,
        sizes=sizes,
    )
    material = gfx.PointsGaussianBlobMaterial(
        color_mode="vertex",
        size_mode="vertex",
    )
    points = gfx.Points(geometry, material)
    return points


def create_cluster_labels(
    result: CollectionResult,
) -> list["gfx.Text"]:
    """Create text labels at cluster centroid positions.

    Only creates labels for clusters with 3+ members.

    Args:
        result: CollectionResult from CollectionAnalyzer.analyze().

    Returns:
        List of pygfx.Text objects positioned at cluster centroids.
    """
    import pygfx as gfx

    labels: list[gfx.Text] = []
    for cluster_id, pos_3d in result.cluster_positions_3d.items():
        member_count = int(np.sum(result.labels == cluster_id))
        if member_count < 3:
            continue
        try:
            text = gfx.Text(
                gfx.TextGeometry(f"C{cluster_id} ({member_count})"),
                gfx.TextMaterial(color=(1.0, 1.0, 1.0, 0.8)),
            )
            text.local.position = tuple(pos_3d.tolist())
            labels.append(text)
        except Exception as exc:
            logger.debug("Could not create cluster label: %s", exc)

    return labels


class EmbeddingCloudManager:
    """Manages embedding cloud lifecycle in the viewport.

    Handles creation, visibility toggling, and click-to-isolate
    interaction for the embedding cloud visualization.

    Attributes:
        cluster_isolated: Called with list of photo paths when cluster isolated.
        isolation_cleared: Called when isolation is cleared.
    """

    def __init__(self, viewport) -> None:
        """Create manager attached to a viewport widget.

        Args:
            viewport: ViewportWidget instance with scene access.
        """
        self._viewport = viewport
        self._cloud_points: "gfx.Points | None" = None
        self._cluster_labels: list["gfx.Text"] = []
        self._visible: bool = True
        self._current_result: CollectionResult | None = None
        self._isolated_cluster: int | None = None

        # Callback hooks (set by consumer)
        self.cluster_isolated = None  # Callable[[list[str]], None]
        self.isolation_cleared = None  # Callable[[], None]

    def update(self, result: CollectionResult) -> None:
        """Replace the current embedding cloud with new analysis results.

        Args:
            result: New CollectionResult to visualize.
        """
        self._remove_cloud()
        self._current_result = result

        if len(result.paths) == 0:
            return

        # Create and add cloud points
        self._cloud_points = create_embedding_cloud(result)
        self._viewport._scene.add(self._cloud_points)

        # Create and add cluster labels
        self._cluster_labels = create_cluster_labels(result)
        for label in self._cluster_labels:
            self._viewport._scene.add(label)

        self._visible = True
        self._isolated_cluster = None
        logger.info(
            "Embedding cloud updated: %d points, %d clusters",
            len(result.paths),
            result.n_clusters,
        )

    def toggle_visibility(self) -> None:
        """Show/hide the embedding cloud."""
        self._visible = not self._visible
        if self._cloud_points is not None:
            self._cloud_points.visible = self._visible
        for label in self._cluster_labels:
            label.visible = self._visible
        logger.info("Embedding cloud visibility: %s", self._visible)

    def isolate_cluster(self, cluster_id: int, result: CollectionResult) -> None:
        """Isolate a cluster by dimming all other points.

        Sets non-cluster embedding points to low alpha and cluster
        points to full alpha. Emits cluster_isolated with photo paths.

        Args:
            cluster_id: Cluster ID to isolate.
            result: CollectionResult for path lookup.
        """
        if self._cloud_points is None:
            return

        import pygfx as gfx

        self._isolated_cluster = cluster_id
        n = len(result.paths)
        colors = self._cloud_points.geometry.colors.data.copy()

        for i in range(n):
            if result.labels[i] == cluster_id:
                colors[i, 3] = 1.0
            else:
                colors[i, 3] = 0.15

        self._cloud_points.geometry.colors = gfx.Buffer(colors.astype(np.float32))

        # Get paths of photos in the isolated cluster
        cluster_paths = [
            result.paths[i]
            for i in range(n)
            if result.labels[i] == cluster_id
        ]

        if self.cluster_isolated is not None:
            self.cluster_isolated(cluster_paths)

        logger.info(
            "Isolated cluster %d (%d photos)", cluster_id, len(cluster_paths)
        )

    def clear_isolation(self) -> None:
        """Restore all points to normal alpha values."""
        if self._cloud_points is None or self._current_result is None:
            return

        import pygfx as gfx

        result = self._current_result
        n = len(result.paths)
        colors = self._cloud_points.geometry.colors.data.copy()

        for i in range(n):
            if result.labels[i] == -1:
                colors[i, 3] = _NOISE_COLOR[3]
            else:
                colors[i, 3] = 1.0

        self._cloud_points.geometry.colors = gfx.Buffer(colors.astype(np.float32))
        self._isolated_cluster = None

        if self.isolation_cleared is not None:
            self.isolation_cleared()

        logger.info("Cluster isolation cleared")

    @property
    def isolated_cluster(self) -> int | None:
        """Currently isolated cluster ID, or None."""
        return self._isolated_cluster

    @property
    def visible(self) -> bool:
        """Whether the embedding cloud is visible."""
        return self._visible

    def _remove_cloud(self) -> None:
        """Remove existing cloud and labels from scene."""
        if self._cloud_points is not None:
            try:
                self._viewport._scene.remove(self._cloud_points)
            except Exception:
                pass
            self._cloud_points = None

        for label in self._cluster_labels:
            try:
                self._viewport._scene.remove(label)
            except Exception:
                pass
        self._cluster_labels.clear()
