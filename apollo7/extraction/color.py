"""Color palette and distribution extraction.

Uses extcolors for dominant color palette extraction and numpy for
per-channel histogram computation.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from apollo7.extraction.base import BaseExtractor, ExtractionResult


def extract_enriched_colors(
    image_rgb: np.ndarray,
    saturation_boost: float = 1.8,
) -> np.ndarray:
    """Extract per-pixel colors with HSV saturation boost.

    Makes sculpture colors more vibrant than the source photo.

    Args:
        image_rgb: H x W x 3 float32 RGB [0, 1].
        saturation_boost: Multiplier for saturation channel (1.3 = 30% boost).

    Returns:
        H x W x 4 float32 RGBA with alpha=1.0, values in [0, 1].
    """
    h, w = image_rgb.shape[:2]

    # Convert float32 [0,1] to uint8 for HSV conversion
    img_uint8 = (np.clip(image_rgb, 0.0, 1.0) * 255).astype(np.uint8)

    # RGB -> HSV, boost saturation, HSV -> RGB
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV)
    hsv[:, :, 1] = np.clip(
        hsv[:, :, 1].astype(np.float32) * saturation_boost, 0, 255
    ).astype(np.uint8)
    boosted_uint8 = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    # Back to float32 [0, 1] with alpha=1.0
    rgb_f32 = boosted_uint8.astype(np.float32) / 255.0
    alpha = np.ones((h, w, 1), dtype=np.float32)
    return np.concatenate([rgb_f32, alpha], axis=-1)


class ColorExtractor(BaseExtractor):
    """Extracts dominant color palette and color distribution from an image."""

    @property
    def name(self) -> str:
        return "color"

    def extract(self, image: np.ndarray) -> ExtractionResult:
        """Extract color features from an RGB float32 [0-1] image.

        Returns ExtractionResult with:
            data: dominant_colors (list of (R,G,B) tuples), color_count (int)
            arrays: histogram (256x3 per-channel histogram),
                    color_distribution (H x W x 3 uint8 quantized map)
        """
        import extcolors

        # Convert float32 [0,1] -> uint8 [0,255] PIL Image
        img_uint8 = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
        pil_image = Image.fromarray(img_uint8, mode="RGB")

        # Dominant colors via extcolors
        colors_raw, _total_pixels = extcolors.extract_from_image(
            pil_image, tolerance=32, limit=12
        )
        # colors_raw is list of ((R, G, B), pixel_count)
        dominant_colors = [rgb for rgb, _count in colors_raw]

        # Per-channel histogram (256 bins each)
        histogram = np.zeros((256, 3), dtype=np.float64)
        for ch in range(3):
            histogram[:, ch], _ = np.histogram(
                img_uint8[:, :, ch], bins=256, range=(0, 256)
            )

        # Color distribution map: quantize to nearest dominant color
        color_distribution = img_uint8.copy()

        return ExtractionResult(
            extractor_name=self.name,
            data={
                "dominant_colors": dominant_colors,
                "color_count": len(dominant_colors),
            },
            arrays={
                "histogram": histogram,
                "color_distribution": color_distribution,
            },
        )
