"""Tests for ColorExtractor and FeatureCache."""

import numpy as np
import pytest

from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.cache import FeatureCache


@pytest.fixture
def gradient_image():
    """100x100 RGB float32 [0-1] gradient image."""
    img = np.zeros((100, 100, 3), dtype=np.float32)
    img[:, :, 0] = np.linspace(0, 1, 100, dtype=np.float32)[np.newaxis, :]
    img[:, :, 1] = np.linspace(0, 1, 100, dtype=np.float32)[:, np.newaxis]
    img[:, :, 2] = 0.5
    return img


class TestColorExtractor:
    def test_color_extract_returns_result(self, gradient_image):
        result = ColorExtractor().extract(gradient_image)
        assert isinstance(result, ExtractionResult)
        assert result.extractor_name == "color"

    def test_color_dominant_colors(self, gradient_image):
        result = ColorExtractor().extract(gradient_image)
        dominant = result.data["dominant_colors"]
        assert isinstance(dominant, list)
        assert len(dominant) > 0
        # Each entry should be an (R, G, B) tuple
        for color_entry in dominant:
            assert len(color_entry) == 3
            assert all(isinstance(c, int) for c in color_entry)

    def test_color_histogram(self, gradient_image):
        result = ColorExtractor().extract(gradient_image)
        histogram = result.arrays["histogram"]
        assert isinstance(histogram, np.ndarray)


class TestFeatureCache:
    def test_cache_stores_result(self):
        cache = FeatureCache()
        extractor = ColorExtractor()
        img = np.ones((50, 50, 3), dtype=np.float32) * 0.5
        result = extractor.extract(img)

        cache.store("photo1.jpg", "color", result)
        cached = cache.get("photo1.jpg", "color")
        assert cached is result  # Same object, not re-extracted

    def test_cache_invalidation(self):
        cache = FeatureCache()
        result = ExtractionResult(
            extractor_name="color",
            data={"dominant_colors": [(128, 128, 128)]},
            arrays={"histogram": np.zeros(256)},
        )
        cache.store("photo1.jpg", "color", result)
        cache.invalidate("photo1.jpg")
        assert cache.get("photo1.jpg", "color") is None
