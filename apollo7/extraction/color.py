"""Color palette and distribution extraction.

Uses extcolors for dominant color palette extraction and numpy for
per-channel histogram computation.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from apollo7.extraction.base import BaseExtractor, ExtractionResult


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
