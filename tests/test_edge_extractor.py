"""Tests for EdgeExtractor."""

import numpy as np
import pytest

from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.edges import EdgeExtractor


@pytest.fixture
def sharp_image():
    """100x100 RGB float32 [0-1] image with sharp edges (white square on black)."""
    img = np.zeros((100, 100, 3), dtype=np.float32)
    img[25:75, 25:75, :] = 1.0  # White square
    return img


class TestEdgeExtractor:
    def test_edge_extract_returns_result(self, sharp_image):
        result = EdgeExtractor().extract(sharp_image)
        assert isinstance(result, ExtractionResult)
        assert result.extractor_name == "edge"

    def test_edge_map_shape(self, sharp_image):
        result = EdgeExtractor().extract(sharp_image)
        edge_map = result.arrays["edge_map"]
        assert edge_map.shape == (100, 100)

    def test_edge_map_binary(self, sharp_image):
        result = EdgeExtractor().extract(sharp_image)
        edge_map = result.arrays["edge_map"]
        assert edge_map.dtype == np.uint8
        unique_vals = set(np.unique(edge_map))
        assert unique_vals.issubset({0, 255})
