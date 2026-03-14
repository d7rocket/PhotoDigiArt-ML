"""Monocular depth estimation via Depth Anything V2 ONNX.

Uses ONNX Runtime with DirectML for AMD GPU acceleration.
Falls back to CPU if DirectML is unavailable.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from apollo7.extraction.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# ImageNet normalization constants
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class DepthExtractor(BaseExtractor):
    """Extracts monocular depth maps using Depth Anything V2 ONNX model.

    The ONNX session is created lazily on the first extract() call,
    not at import time, so importing this module is always cheap.
    """

    def __init__(self, model_path: str = "models/depth_anything_v2_vits.onnx") -> None:
        self._model_path = model_path
        self._session = None  # Lazy-loaded

    @property
    def name(self) -> str:
        return "depth"

    def _ensure_session(self) -> None:
        """Create ONNX session on first use."""
        if self._session is not None:
            return

        import os

        if not os.path.isfile(self._model_path):
            raise FileNotFoundError(
                f"Depth model not found at '{self._model_path}'. "
                "Download Depth Anything V2 ViT-S ONNX from "
                "https://github.com/fabio-sim/Depth-Anything-ONNX/releases "
                "and place it at the expected path."
            )

        import onnxruntime as ort

        available = ort.get_available_providers()
        providers = []
        if "DmlExecutionProvider" in available:
            providers.append("DmlExecutionProvider")
        else:
            logger.warning(
                "DirectML execution provider not available. "
                "Depth extraction will use CPU (slower). "
                "Install onnxruntime-directml for GPU acceleration."
            )
        providers.append("CPUExecutionProvider")

        self._session = ort.InferenceSession(
            self._model_path, providers=providers
        )

    def extract(self, image: np.ndarray) -> ExtractionResult:
        """Extract depth map from an RGB float32 [0-1] image.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].

        Returns:
            ExtractionResult with:
                data: min_depth (float), max_depth (float)
                arrays: depth_map (H x W float32, values in [0, 1])
        """
        self._ensure_session()

        h, w = image.shape[:2]

        # Get model input dimensions
        model_input = self._session.get_inputs()[0]
        input_name = model_input.name
        input_shape = model_input.shape
        # ONNX dynamic shapes may return strings (e.g., "height") — use defaults
        model_h = input_shape[2] if isinstance(input_shape[2], int) else 518
        model_w = input_shape[3] if isinstance(input_shape[3], int) else 518

        # Convert float32 [0,1] -> uint8 [0,255] for preprocessing
        img_uint8 = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)

        # Resize to model input size
        resized = cv2.resize(
            img_uint8, (model_w, model_h), interpolation=cv2.INTER_LINEAR
        )

        # Normalize: uint8 -> float32 [0,1] -> ImageNet normalization
        normalized = resized.astype(np.float32) / 255.0
        normalized = (normalized - _IMAGENET_MEAN) / _IMAGENET_STD

        # HWC -> NCHW
        input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...].astype(
            np.float32
        )

        # Run inference
        outputs = self._session.run(None, {input_name: input_tensor})
        depth = outputs[0].squeeze()

        # Resize back to original image dimensions
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)

        # Normalize to [0, 1]
        d_min, d_max = float(depth.min()), float(depth.max())
        depth = (depth - d_min) / (d_max - d_min + 1e-8)
        depth = depth.astype(np.float32)

        return ExtractionResult(
            extractor_name=self.name,
            data={"min_depth": d_min, "max_depth": d_max},
            arrays={"depth_map": depth},
        )
