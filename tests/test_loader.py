"""Tests for image loading and folder scanning."""

import os

import numpy as np
import pytest
from PIL import Image


def _make_image(path: str, fmt: str = "JPEG", size: tuple = (100, 80)):
    """Helper to create a test image file."""
    arr = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    img.save(path, fmt)
    return path


class TestLoadImage:
    """Tests for load_image function."""

    def test_load_single_jpeg(self, tmp_dir):
        from apollo7.ingestion.loader import load_image

        path = _make_image(os.path.join(tmp_dir, "test.jpg"), "JPEG")
        result = load_image(path)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert result.ndim == 3
        assert result.shape[2] == 3  # RGB
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_load_single_png(self, tmp_dir):
        from apollo7.ingestion.loader import load_image

        path = _make_image(os.path.join(tmp_dir, "test.png"), "PNG")
        result = load_image(path)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert result.shape[2] == 3

    def test_load_unsupported(self, tmp_dir):
        from apollo7.ingestion.loader import load_image

        path = os.path.join(tmp_dir, "test.bmp")
        # Create a BMP file
        arr = np.zeros((10, 10, 3), dtype=np.uint8)
        Image.fromarray(arr).save(path, "BMP")
        with pytest.raises(ValueError, match="[Uu]nsupported"):
            load_image(path)

    def test_load_nonexistent(self):
        from apollo7.ingestion.loader import load_image

        with pytest.raises(FileNotFoundError):
            load_image("nonexistent_image_12345.jpg")


class TestLoadFolder:
    """Tests for load_folder function."""

    def test_load_folder(self, tmp_dir):
        from apollo7.ingestion.loader import load_folder

        for i in range(3):
            _make_image(os.path.join(tmp_dir, f"photo_{i}.jpg"), "JPEG")
        results = load_folder(tmp_dir)
        assert len(results) == 3
        for path, img in results:
            assert isinstance(img, np.ndarray)
            assert img.dtype == np.float32

    def test_load_folder_filters(self, tmp_dir):
        from apollo7.ingestion.loader import load_folder

        # Create supported and unsupported files
        _make_image(os.path.join(tmp_dir, "photo.jpg"), "JPEG")
        _make_image(os.path.join(tmp_dir, "photo.png"), "PNG")
        # Create a non-image file
        with open(os.path.join(tmp_dir, "notes.txt"), "w") as f:
            f.write("not an image")
        results = load_folder(tmp_dir)
        assert len(results) == 2


class TestExtractMetadata:
    """Tests for metadata extraction."""

    def test_extract_metadata(self, tmp_dir):
        from apollo7.ingestion.metadata import extract_metadata

        path = _make_image(os.path.join(tmp_dir, "test.jpg"), "JPEG", size=(200, 150))
        meta = extract_metadata(path)
        assert meta["width"] == 200
        assert meta["height"] == 150
        assert meta["format"] == "JPEG"
        assert "file_size_bytes" in meta
        assert meta["file_size_bytes"] > 0
        assert "exif" in meta
