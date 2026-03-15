"""Collection analysis: clustering, UMAP projection, and embedding cloud visualization.

Analyzes photo collections by clustering CLIP embeddings with DBSCAN,
projecting to 3D with UMAP, and rendering embedding clouds in the viewport.
Cluster centroids serve as force attractors in the particle simulation.
"""

from apollo7.collection.analyzer import CollectionAnalyzer, CollectionResult
from apollo7.collection.embedding_cloud import (
    EmbeddingCloudManager,
    create_embedding_cloud,
)

__all__ = [
    "CollectionAnalyzer",
    "CollectionResult",
    "EmbeddingCloudManager",
    "create_embedding_cloud",
]
