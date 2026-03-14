"""Level-of-detail decimation for point clouds.

Grid-based spatial decimation: divide space into cells, keep one
representative point per cell (closest to cell center).
"""

from __future__ import annotations

import numpy as np


def decimate_points(
    positions: np.ndarray,
    colors: np.ndarray,
    sizes: np.ndarray,
    factor: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reduce point count via grid-based spatial decimation.

    Divides the bounding volume into cells and keeps one point per cell
    (the point closest to the cell center).

    Args:
        positions: (N, 3) float32 point positions.
        colors: (N, 4) float32 point colors.
        sizes: (N,) float32 point sizes.
        factor: Target fraction of points to keep (0.5 = ~half).
            Controls cell size: smaller factor = larger cells = fewer points.

    Returns:
        Decimated (positions, colors, sizes) as contiguous float32 arrays.
    """
    n = positions.shape[0]
    if n == 0 or factor >= 1.0:
        return positions, colors, sizes

    # Compute bounding box
    p_min = positions.min(axis=0)
    p_max = positions.max(axis=0)
    extent = p_max - p_min + 1e-8

    # Determine grid resolution from factor
    # factor = target_points / n, and target_points ~ grid_cells
    # grid_cells = nx * ny * nz; for uniform: nx = ny = nz = cbrt(n * factor)
    target = max(1, int(n * factor))
    cells_per_axis = max(1, int(np.cbrt(target)))

    cell_size = extent / cells_per_axis

    # Assign each point to a grid cell
    cell_indices = ((positions - p_min) / cell_size).astype(np.int32)
    # Clamp to valid range
    cell_indices = np.clip(cell_indices, 0, cells_per_axis - 1)

    # Encode cell as single integer for hashing
    cell_keys = (
        cell_indices[:, 0] * cells_per_axis * cells_per_axis
        + cell_indices[:, 1] * cells_per_axis
        + cell_indices[:, 2]
    )

    # For each unique cell, keep the point closest to cell center
    cell_centers = p_min + (cell_indices + 0.5) * cell_size
    distances = np.linalg.norm(positions - cell_centers, axis=1)

    # Group by cell key and pick minimum distance
    unique_keys, inverse = np.unique(cell_keys, return_inverse=True)
    n_unique = len(unique_keys)

    # For each unique cell, find the point with minimum distance
    keep_indices = np.empty(n_unique, dtype=np.intp)
    best_dists = np.full(n_unique, np.inf, dtype=np.float64)

    for i in range(n):
        cell_idx = inverse[i]
        if distances[i] < best_dists[cell_idx]:
            best_dists[cell_idx] = distances[i]
            keep_indices[cell_idx] = i

    return (
        np.ascontiguousarray(positions[keep_indices], dtype=np.float32),
        np.ascontiguousarray(colors[keep_indices], dtype=np.float32),
        np.ascontiguousarray(sizes[keep_indices], dtype=np.float32),
    )
