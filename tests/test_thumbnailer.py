"""Tests for thumbnail generation."""

import numpy as np
import pytest
from PIL import Image


class TestGenerateThumbnail:
    """Tests for generate_thumbnail function."""

    def test_generate_thumbnail(self):
        from apollo7.ingestion.thumbnailer import generate_thumbnail

        # Create a 200x200 float32 RGB array
        image = np.random.rand(200, 200, 3).astype(np.float32)
        thumb = generate_thumbnail(image, size=128)
        assert isinstance(thumb, Image.Image)
        assert max(thumb.size) == 128

    def test_thumbnail_preserves_aspect(self):
        from apollo7.ingestion.thumbnailer import generate_thumbnail

        # Wide image: 400x100
        image = np.random.rand(100, 400, 3).astype(np.float32)
        thumb = generate_thumbnail(image, size=128)
        assert isinstance(thumb, Image.Image)
        w, h = thumb.size
        assert w == 128  # Width is the limiting dimension
        assert h == 32   # Height scaled proportionally
        # Aspect ratio preserved
        assert abs(w / h - 4.0) < 0.1
