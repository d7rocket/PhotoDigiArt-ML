"""Depth-projected point cloud layout.

Creates a relief-sculpture layout where depth maps drive Z-axis displacement.
Every pixel becomes a point at full density.
"""

from __future__ import annotations

import numpy as np

from apollo7.config.settings import DEPTH_EXAGGERATION_DEFAULT, POINT_SIZE_DEFAULT


def generate_depth_projected_cloud(
    image: np.ndarray,
    depth_map: np.ndarray,
    depth_exaggeration: float = DEPTH_EXAGGERATION_DEFAULT,
    layer_offset: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a depth-projected point cloud from image and depth map.

    Every pixel becomes a point. X/Y from pixel grid normalized to [-1, 1],
    Z from depth values multiplied by exaggeration factor.

    Args:
        image: H x W x 3 float32 RGB [0, 1].
        depth_map: H x W float32 [0, 1].
        depth_exaggeration: Multiplier for depth-to-Z mapping.
        layer_offset: Z offset for stacked multi-photo mode.

    Returns:
        (positions, colors, sizes) as contiguous float32 arrays:
        - positions: (N, 3) where N = H * W
        - colors: (N, 4) with alpha = 1.0
        - sizes: (N,) uniform point sizes
    """
    h, w = image.shape[:2]

    # Create grid of (x, y) coordinates normalized to [-1, 1]
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    x_norm = (x_coords.astype(np.float32) / w) * 2.0 - 1.0
    y_norm = -((y_coords.astype(np.float32) / h) * 2.0 - 1.0)  # Flip for Y-up

    # Z from depth, exaggerated, with optional layer offset
    z_coords = depth_map.astype(np.float32) * depth_exaggeration + layer_offset

    # Flatten to (N, 3)
    positions = np.stack([x_norm, y_norm, z_coords], axis=-1).reshape(-1, 3)
    positions = np.ascontiguousarray(positions, dtype=np.float32)

    # Colors: add alpha channel
    colors_rgb = image.reshape(-1, 3).astype(np.float32)
    alpha = np.ones((colors_rgb.shape[0], 1), dtype=np.float32)
    colors = np.ascontiguousarray(
        np.concatenate([colors_rgb, alpha], axis=-1), dtype=np.float32
    )

    # Uniform sizes
    sizes = np.full(h * w, POINT_SIZE_DEFAULT, dtype=np.float32)

    return positions, colors, sizes
