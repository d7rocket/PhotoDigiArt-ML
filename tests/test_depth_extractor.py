"""Tests for depth extraction and extraction pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from apollo7.extraction.base import ExtractionResult


# ---------------------------------------------------------------------------
# DepthExtractor tests (mocked ONNX session)
# ---------------------------------------------------------------------------


class TestDepthExtractor:
    """Tests for DepthExtractor with mocked ONNX inference."""

    def _make_mock_session(self, input_h: int = 518, input_w: int = 518):
        """Create a mock ONNX InferenceSession."""
        session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "image"
        mock_input.shape = [1, 3, input_h, input_w]
        session.get_inputs.return_value = [mock_input]

        # Return a fake depth map from run()
        def fake_run(output_names, input_dict):
            # Output shape matches model output (before resize)
            return [np.random.rand(1, input_h, input_w).astype(np.float32)]

        session.run = MagicMock(side_effect=fake_run)
        return session

    def test_depth_extract_returns_result(self):
        """DepthExtractor().extract(image) returns ExtractionResult with name='depth'."""
        from apollo7.extraction.depth import DepthExtractor

        extractor = DepthExtractor(model_path="dummy.onnx")
        # Inject mock session
        extractor._session = self._make_mock_session()

        image = np.random.rand(100, 100, 3).astype(np.float32)
        result = extractor.extract(image)

        assert isinstance(result, ExtractionResult)
        assert result.extractor_name == "depth"

    def test_depth_map_shape(self):
        """result.arrays['depth_map'] has same H,W as input image."""
        from apollo7.extraction.depth import DepthExtractor

        extractor = DepthExtractor(model_path="dummy.onnx")
        extractor._session = self._make_mock_session()

        image = np.random.rand(80, 120, 3).astype(np.float32)
        result = extractor.extract(image)
        depth_map = result.arrays["depth_map"]

        assert depth_map.shape == (80, 120)

    def test_depth_map_range(self):
        """depth_map values are in [0, 1] range."""
        from apollo7.extraction.depth import DepthExtractor

        extractor = DepthExtractor(model_path="dummy.onnx")
        extractor._session = self._make_mock_session()

        image = np.random.rand(50, 50, 3).astype(np.float32)
        result = extractor.extract(image)
        depth_map = result.arrays["depth_map"]

        assert depth_map.min() >= 0.0
        assert depth_map.max() <= 1.0


# ---------------------------------------------------------------------------
# ExtractionPipeline tests
# ---------------------------------------------------------------------------


class TestExtractionPipeline:
    """Tests for ExtractionPipeline orchestrator."""

    def _make_extractor(self, name: str) -> MagicMock:
        """Create a mock extractor."""
        extractor = MagicMock()
        extractor.name = name
        extractor.extract.return_value = ExtractionResult(
            extractor_name=name, data={}, arrays={}
        )
        return extractor

    def test_pipeline_runs_all(self):
        """ExtractionPipeline runs all extractors and returns dict of results."""
        from apollo7.extraction.pipeline import ExtractionPipeline

        color = self._make_extractor("color")
        edge = self._make_extractor("edge")
        depth = self._make_extractor("depth")

        pipeline = ExtractionPipeline([color, edge, depth])
        image = np.random.rand(50, 50, 3).astype(np.float32)
        results = pipeline.run(image, photo_path="test.jpg")

        assert len(results) == 3
        assert "color" in results
        assert "edge" in results
        assert "depth" in results

    def test_pipeline_order(self):
        """Extractors run in configured order."""
        from apollo7.extraction.pipeline import ExtractionPipeline

        call_order = []

        def make_ordered_extractor(name: str):
            ext = MagicMock()
            ext.name = name

            def extract_fn(image):
                call_order.append(name)
                return ExtractionResult(extractor_name=name, data={}, arrays={})

            ext.extract = extract_fn
            return ext

        color = make_ordered_extractor("color")
        edge = make_ordered_extractor("edge")
        depth = make_ordered_extractor("depth")

        pipeline = ExtractionPipeline([color, edge, depth])
        image = np.random.rand(50, 50, 3).astype(np.float32)
        pipeline.run(image, photo_path="test.jpg")

        assert call_order == ["color", "edge", "depth"]
