"""Shared test fixtures for Apollo 7."""

import os
import tempfile

import numpy as np
import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory(prefix="apollo7_test_") as d:
        yield d


@pytest.fixture
def sample_image(tmp_dir):
    """Generate a 100x100 RGB gradient image saved as JPEG.

    Returns the file path to the saved image.
    """
    from PIL import Image

    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    # Horizontal red gradient
    arr[:, :, 0] = np.linspace(0, 255, 100, dtype=np.uint8)[np.newaxis, :]
    # Vertical green gradient
    arr[:, :, 1] = np.linspace(0, 255, 100, dtype=np.uint8)[:, np.newaxis]
    # Constant blue
    arr[:, :, 2] = 128

    img = Image.fromarray(arr)
    path = os.path.join(tmp_dir, "test_gradient.jpg")
    img.save(path, "JPEG")
    return path
