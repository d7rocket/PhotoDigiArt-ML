"""Feature extraction pipeline for Apollo 7.

Provides pluggable extractors that transform photos into visual features
(color palettes, edge maps, depth maps) used for point cloud generation.
"""

from apollo7.extraction.base import BaseExtractor, ExtractionResult
from apollo7.extraction.cache import FeatureCache
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.depth import DepthExtractor
from apollo7.extraction.edges import EdgeExtractor
from apollo7.extraction.pipeline import ExtractionPipeline

__all__ = [
    "BaseExtractor",
    "ExtractionResult",
    "ColorExtractor",
    "DepthExtractor",
    "EdgeExtractor",
    "ExtractionPipeline",
    "FeatureCache",
]
