"""Metadata extraction from image files.

Extracts dimensions, format, file size, and EXIF data using Pillow.
"""

import os
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


def extract_metadata(path: str | Path) -> dict:
    """Extract metadata from an image file.

    Returns a dict with keys: width, height, format, file_size_bytes, exif.
    EXIF data is returned as a dict of tag-name to value mappings,
    or an empty dict if no EXIF data is present.
    """
    path = Path(path)

    img = Image.open(path)
    width, height = img.size

    # Extract EXIF
    exif_data: dict = {}
    raw_exif = img.getexif()
    if raw_exif:
        for tag_id, value in raw_exif.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            # Convert non-serializable types to string
            try:
                if isinstance(value, bytes):
                    value = value.hex()
                exif_data[tag_name] = value
            except Exception:
                exif_data[tag_name] = str(value)

    return {
        "width": width,
        "height": height,
        "format": img.format,
        "file_size_bytes": os.path.getsize(path),
        "exif": exif_data,
    }
