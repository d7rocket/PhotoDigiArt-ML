"""Image loading and folder scanning for Apollo 7 ingestion pipeline.

Supports JPEG, PNG, and TIFF formats. Images are returned as float32 RGB
numpy arrays normalized to [0.0, 1.0].
"""

import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

# Pillow format names that we accept (detected via header, not extension)
_SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF", "MPO"}


def load_image(path: str | Path) -> np.ndarray:
    """Load a single image file and return as float32 RGB array [0.0-1.0].

    Uses Pillow for format detection via file header, not extension.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is unsupported.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    img = Image.open(path)

    if img.format not in _SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format: {img.format}. "
            f"Supported formats: JPEG, PNG, TIFF"
        )

    # Convert to RGB (handles RGBA, grayscale, palette, CMYK, etc.)
    img = img.convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr


def load_folder(folder: str | Path) -> list[tuple[Path, np.ndarray]]:
    """Scan a folder for supported image files and load them.

    Returns a list of (path, image_array) tuples. Files that fail to load
    are skipped with a warning logged.
    """
    folder = Path(folder)
    results: list[tuple[Path, np.ndarray]] = []

    for file_path in sorted(folder.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            img = load_image(file_path)
            results.append((file_path, img))
        except Exception as exc:
            logger.warning("Skipping %s: %s", file_path, exc)

    return results
