"""Point cloud generation for Apollo 7.

Converts extracted features into 3D point cloud data (positions, colors, sizes)
in depth-projected or feature-clustered layout modes with LOD support.
"""

from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud
from apollo7.pointcloud.feature_cluster import generate_feature_clustered_cloud
from apollo7.pointcloud.generator import PointCloudGenerator
from apollo7.pointcloud.lod import decimate_points

__all__ = [
    "PointCloudGenerator",
    "generate_depth_projected_cloud",
    "generate_feature_clustered_cloud",
    "decimate_points",
]
