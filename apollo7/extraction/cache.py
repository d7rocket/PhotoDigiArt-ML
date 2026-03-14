"""Feature caching to avoid re-extraction.

In-memory cache keyed by (photo_path, extractor_name). Results are stored
after extraction and returned on subsequent requests for the same photo
and extractor combination.
"""

from __future__ import annotations

from apollo7.extraction.base import ExtractionResult


class FeatureCache:
    """In-memory cache for extraction results."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], ExtractionResult] = {}

    def get(self, photo_path: str, extractor_name: str) -> ExtractionResult | None:
        """Retrieve a cached result, or None if not cached."""
        return self._store.get((photo_path, extractor_name))

    def store(
        self, photo_path: str, extractor_name: str, result: ExtractionResult
    ) -> None:
        """Cache an extraction result."""
        self._store[(photo_path, extractor_name)] = result

    def invalidate(self, photo_path: str) -> None:
        """Remove all cached results for a given photo."""
        keys_to_remove = [
            key for key in self._store if key[0] == photo_path
        ]
        for key in keys_to_remove:
            del self._store[key]

    def clear(self) -> None:
        """Remove all cached results."""
        self._store.clear()
