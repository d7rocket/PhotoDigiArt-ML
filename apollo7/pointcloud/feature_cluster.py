"""Feature-clustered point cloud layout.

Creates an abstract 3D arrangement where pixels are grouped by color
similarity and positioned as floating clusters in space.
"""

from __future__ import annotations

import numpy as np

from apollo7.config.settings import POINT_SIZE_DEFAULT

if False:  # TYPE_CHECKING without import overhead
    from apollo7.extraction.base import ExtractionResult


def generate_feature_clustered_cloud(
    image: np.ndarray,
    features: dict[str, "ExtractionResult"],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a feature-clustered point cloud from image and features.

    Groups pixels by dominant color similarity and arranges clusters
    in 3D space. Points retain original pixel colors.

    Args:
        image: H x W x 3 float32 RGB [0, 1].
        features: Dict of extraction results (uses 'color' key if available).

    Returns:
        (positions, colors, sizes) as contiguous float32 arrays.
    """
    h, w = image.shape[:2]

    # Downsample for clustering (every 4th pixel in each dimension)
    step = max(1, min(4, min(h, w) // 4))
    sampled = image[::step, ::step]
    sh, sw = sampled.shape[:2]
    pixels = sampled.reshape(-1, 3)
    n_sampled = pixels.shape[0]

    # Get dominant colors for clustering
    color_result = features.get("color")
    if color_result and "dominant_colors" in color_result.data:
        centers_rgb = color_result.data["dominant_colors"]
        # Convert uint8 tuples to float32 [0, 1]
        centers = np.array(centers_rgb, dtype=np.float32)
        if centers.max() > 1.0:
            centers = centers / 255.0
    else:
        # Fallback: simple color quantization with 8 bins
        centers = np.array(
            [
                [0.8, 0.2, 0.2],
                [0.2, 0.8, 0.2],
                [0.2, 0.2, 0.8],
                [0.8, 0.8, 0.2],
                [0.8, 0.2, 0.8],
                [0.2, 0.8, 0.8],
                [0.8, 0.8, 0.8],
                [0.2, 0.2, 0.2],
            ],
            dtype=np.float32,
        )

    n_clusters = len(centers)

    # Assign each pixel to nearest cluster center (Euclidean in RGB)
    # Shape: (n_sampled, n_clusters)
    dists = np.linalg.norm(
        pixels[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2
    )
    labels = dists.argmin(axis=1)

    # Arrange clusters in 3D: place cluster centers on a sphere
    angles = np.linspace(0, 2 * np.pi, n_clusters, endpoint=False)
    cluster_centers_3d = np.stack(
        [np.cos(angles) * 2.0, np.sin(angles) * 2.0, np.zeros(n_clusters)],
        axis=-1,
    ).astype(np.float32)

    # Give each cluster a Z spread for visual depth
    for ci in range(n_clusters):
        cluster_centers_3d[ci, 2] = (ci / max(n_clusters - 1, 1) - 0.5) * 2.0

    # Build positions: scatter points around their cluster center
    rng = np.random.default_rng(42)
    positions = np.zeros((n_sampled, 3), dtype=np.float32)
    for ci in range(n_clusters):
        mask = labels == ci
        count = mask.sum()
        if count == 0:
            continue
        # Random scatter within a sphere around cluster center
        offsets = rng.normal(0, 0.3, size=(count, 3)).astype(np.float32)
        positions[mask] = cluster_centers_3d[ci] + offsets

    positions = np.ascontiguousarray(positions, dtype=np.float32)

    # Colors: original pixel colors with alpha
    colors_rgb = pixels.astype(np.float32)
    alpha = np.ones((n_sampled, 1), dtype=np.float32)
    colors = np.ascontiguousarray(
        np.concatenate([colors_rgb, alpha], axis=-1), dtype=np.float32
    )

    # Uniform sizes
    sizes = np.full(n_sampled, POINT_SIZE_DEFAULT, dtype=np.float32)

    return positions, colors, sizes
