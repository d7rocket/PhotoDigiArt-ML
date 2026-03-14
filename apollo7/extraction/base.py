"""Abstract extractor interface and shared result type.

All extractors receive RGB float32 [0.0-1.0] numpy arrays and return
ExtractionResult instances containing scalars/metadata and array data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ExtractionResult:
    """Container for extractor output.

    Attributes:
        extractor_name: Identifier for the extractor that produced this result.
        data: Scalar values and metadata (e.g. dominant color list, counts).
        arrays: Numpy array outputs (e.g. edge maps, histograms).
    """

    extractor_name: str
    data: dict[str, Any] = field(default_factory=dict)
    arrays: dict[str, np.ndarray] = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract base class for all feature extractors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this extractor (e.g. 'color', 'edge')."""
        ...

    @abstractmethod
    def extract(self, image: np.ndarray) -> ExtractionResult:
        """Extract features from an RGB float32 [0-1] image.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].

        Returns:
            ExtractionResult with extracted data and arrays.
        """
        ...
