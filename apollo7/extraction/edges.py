"""Edge detection and contour extraction.

Uses OpenCV Canny edge detection and contour finding.
"""

from __future__ import annotations

import cv2
import numpy as np

from apollo7.extraction.base import BaseExtractor, ExtractionResult


class EdgeExtractor(BaseExtractor):
    """Extracts edges and contours from an image using Canny detection."""

    def __init__(
        self,
        low_threshold: int = 50,
        high_threshold: int = 150,
    ) -> None:
        self._low = low_threshold
        self._high = high_threshold

    @property
    def name(self) -> str:
        return "edge"

    def extract(self, image: np.ndarray) -> ExtractionResult:
        """Extract edge features from an RGB float32 [0-1] image.

        Returns ExtractionResult with:
            data: contour_count (int)
            arrays: edge_map (H x W uint8, values 0 or 255),
                    contour_image (H x W x 3 uint8, contours drawn on black)
        """
        # Convert to uint8 grayscale
        img_uint8 = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
        if img_uint8.ndim == 3:
            gray = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_uint8

        # Canny edge detection
        edge_map = cv2.Canny(gray, self._low, self._high)

        # Find contours
        contours, _ = cv2.findContours(
            edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Draw contours on a blank canvas
        contour_image = np.zeros((*gray.shape, 3), dtype=np.uint8)
        cv2.drawContours(contour_image, contours, -1, (0, 255, 0), 1)

        return ExtractionResult(
            extractor_name=self.name,
            data={"contour_count": len(contours)},
            arrays={
                "edge_map": edge_map,
                "contour_image": contour_image,
            },
        )
