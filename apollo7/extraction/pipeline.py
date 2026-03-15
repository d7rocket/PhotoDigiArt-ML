"""Extraction pipeline orchestrator.

Runs configured extractors in sequence on an image, with optional
caching to skip re-extraction.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from apollo7.extraction.base import BaseExtractor, ExtractionResult

if TYPE_CHECKING:
    from apollo7.extraction.cache import FeatureCache

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """Orchestrates multiple extractors in configured order.

    Args:
        extractors: Ordered list of BaseExtractor instances.
    """

    def __init__(self, extractors: list[BaseExtractor]) -> None:
        self._extractors = extractors

    def run(
        self,
        image: np.ndarray,
        photo_path: str,
        cache: FeatureCache | None = None,
    ) -> dict[str, ExtractionResult]:
        """Run all extractors on the image.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].
            photo_path: Path to the source photo (used as cache key).
            cache: Optional FeatureCache to skip re-extraction.

        Returns:
            Dict mapping extractor name to ExtractionResult.
        """
        results: dict[str, ExtractionResult] = {}

        for i, extractor in enumerate(self._extractors):
            name = extractor.name
            logger.debug(
                "Running extractor %d/%d: %s",
                i + 1,
                len(self._extractors),
                name,
            )

            # Check cache first
            if cache is not None:
                cached = cache.get(photo_path, name)
                if cached is not None:
                    logger.debug("Cache hit for %s on %s", name, photo_path)
                    results[name] = cached
                    continue

            # Extract — continue on failure so partial results are usable
            try:
                result = extractor.extract(image)
            except Exception as exc:
                logger.warning("Extractor %s failed: %s", name, exc)
                continue
            results[name] = result

            # Store in cache
            if cache is not None:
                cache.store(photo_path, name, result)

        return results
