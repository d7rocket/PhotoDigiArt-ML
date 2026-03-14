"""Point cloud generator facade.

Delegates to depth-projected or feature-clustered layout and applies
LOD decimation when point count exceeds the rendering budget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from apollo7.config.settings import LOD_POINT_BUDGET
from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud
from apollo7.pointcloud.feature_cluster import generate_feature_clustered_cloud
from apollo7.pointcloud.lod import decimate_points

if TYPE_CHECKING:
    from apollo7.extraction.base import ExtractionResult


class PointCloudGenerator:
    """Facade for generating point clouds from extracted features.

    Supports two layout modes and automatic LOD when point count
    exceeds the rendering budget.
    """

    def __init__(self, point_budget: int = LOD_POINT_BUDGET) -> None:
        self._point_budget = point_budget

    def generate(
        self,
        image: np.ndarray,
        features: dict[str, "ExtractionResult"],
        mode: str = "depth_projected",
        **kwargs: Any,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate a point cloud from image and extracted features.

        Args:
            image: H x W x 3 float32 RGB [0, 1].
            features: Dict of extraction results.
            mode: Layout mode -- 'depth_projected' or 'feature_clustered'.
            **kwargs: Extra arguments forwarded to the layout function
                (e.g., depth_exaggeration, layer_offset).

        Returns:
            (positions, colors, sizes) as contiguous float32 arrays.

        Raises:
            ValueError: If mode is unknown or required features are missing.
        """
        if mode == "depth_projected":
            depth_result = features.get("depth")
            if depth_result is None:
                raise ValueError(
                    "depth_projected mode requires 'depth' in features"
                )
            depth_map = depth_result.arrays["depth_map"]
            positions, colors, sizes = generate_depth_projected_cloud(
                image, depth_map, **kwargs
            )
        elif mode == "feature_clustered":
            positions, colors, sizes = generate_feature_clustered_cloud(
                image, features, **kwargs
            )
        else:
            raise ValueError(f"Unknown point cloud mode: {mode!r}")

        # Apply LOD if over budget
        if positions.shape[0] > self._point_budget:
            factor = self._point_budget / positions.shape[0]
            positions, colors, sizes = decimate_points(
                positions, colors, sizes, factor=factor
            )

        return positions, colors, sizes
