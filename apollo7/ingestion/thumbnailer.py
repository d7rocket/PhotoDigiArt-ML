"""Thumbnail generation for loaded images.

Takes float32 RGB numpy arrays and produces PIL Image thumbnails
with preserved aspect ratio.
"""

import numpy as np
from PIL import Image


def generate_thumbnail(image: np.ndarray, size: int = 128) -> Image.Image:
    """Create a thumbnail from a float32 RGB array.

    Args:
        image: Float32 RGB array with shape (H, W, 3), values in [0.0, 1.0].
        size: Maximum dimension (width or height) of the thumbnail.

    Returns:
        PIL Image thumbnail with aspect ratio preserved.
    """
    # Convert float32 [0-1] back to uint8 [0-255]
    img_uint8 = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
    pil_img = Image.fromarray(img_uint8, mode="RGB")
    pil_img.thumbnail((size, size), Image.LANCZOS)
    return pil_img
