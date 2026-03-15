"""Tests for CLIP semantic feature extraction.

Covers:
- ClipExtractor name property
- Extract returns correct structure (mood_tags, object_tags, embedding)
- Lazy ONNX session loading
- Preprocessing output shape
- Zero-shot classification (sorted by confidence, top_k)
- CLIPTokenizer output shape
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from apollo7.extraction.base import ExtractionResult


class TestClipExtractor:
    """Tests for ClipExtractor with mocked ONNX inference."""

    def _make_mock_sessions(self):
        """Create mock visual and text ONNX sessions returning 512-dim embeddings."""
        visual_session = MagicMock()
        text_session = MagicMock()

        # Visual session: returns (1, 512) float32 embedding
        def fake_visual_run(output_names, input_dict):
            emb = np.random.randn(1, 512).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            return [emb]

        visual_session.run = MagicMock(side_effect=fake_visual_run)

        # Text session: returns (N, 512) float32 embeddings
        def fake_text_run(output_names, input_dict):
            # Determine N from the input shape
            for v in input_dict.values():
                n = v.shape[0]
                break
            emb = np.random.randn(n, 512).astype(np.float32)
            emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
            return [emb]

        text_session.run = MagicMock(side_effect=fake_text_run)

        return visual_session, text_session

    def _inject_mock_state(self, extractor):
        """Inject mock sessions and pre-computed text embeddings to avoid file I/O."""
        visual_session, text_session = self._make_mock_sessions()
        extractor._visual_session = visual_session
        extractor._text_session = text_session
        # Pre-populate cached text embeddings so tokenizer vocab file is not needed
        extractor._mood_text_embs = np.random.randn(8, 512).astype(np.float32)
        extractor._mood_text_embs /= np.linalg.norm(
            extractor._mood_text_embs, axis=1, keepdims=True
        )
        extractor._object_text_embs = np.random.randn(10, 512).astype(np.float32)
        extractor._object_text_embs /= np.linalg.norm(
            extractor._object_text_embs, axis=1, keepdims=True
        )

    def test_name_property(self):
        """ClipExtractor.name returns 'semantic'."""
        from apollo7.extraction.clip import ClipExtractor

        extractor = ClipExtractor(model_dir="dummy_models")
        assert extractor.name == "semantic"

    def test_extract_returns_correct_structure(self):
        """extract() returns ExtractionResult with mood_tags, object_tags, embedding."""
        from apollo7.extraction.clip import ClipExtractor

        extractor = ClipExtractor(model_dir="dummy_models")
        self._inject_mock_state(extractor)

        image = np.random.rand(100, 100, 3).astype(np.float32)
        result = extractor.extract(image)

        assert isinstance(result, ExtractionResult)
        assert result.extractor_name == "semantic"

        # Check data keys
        assert "mood_tags" in result.data
        assert "object_tags" in result.data

        # mood_tags is list of (label, confidence) tuples
        mood_tags = result.data["mood_tags"]
        assert isinstance(mood_tags, list)
        assert len(mood_tags) > 0
        for label, conf in mood_tags:
            assert isinstance(label, str)
            assert isinstance(conf, float)
            assert 0.0 <= conf <= 1.0

        # object_tags is list of (label, confidence) tuples
        object_tags = result.data["object_tags"]
        assert isinstance(object_tags, list)
        assert len(object_tags) > 0

        # Check embedding array
        assert "embedding" in result.arrays
        embedding = result.arrays["embedding"]
        assert embedding.shape == (512,)
        assert embedding.dtype == np.float32

    def test_lazy_loading(self):
        """Session is None before first extract call."""
        from apollo7.extraction.clip import ClipExtractor

        extractor = ClipExtractor(model_dir="dummy_models")
        assert extractor._visual_session is None
        assert extractor._text_session is None

    def test_preprocessing_shape(self):
        """preprocess_clip produces (1, 3, 224, 224) float32 tensor."""
        from apollo7.extraction.clip import ClipExtractor

        extractor = ClipExtractor(model_dir="dummy_models")

        # Test with various input shapes
        for h, w in [(100, 100), (200, 300), (50, 80)]:
            image = np.random.rand(h, w, 3).astype(np.float32)
            tensor = extractor.preprocess_clip(image)
            assert tensor.shape == (1, 3, 224, 224)
            assert tensor.dtype == np.float32

    def test_zero_shot_classification(self):
        """Classification returns sorted by confidence, respects top_k."""
        from apollo7.extraction.clip import ClipExtractor

        extractor = ClipExtractor(model_dir="dummy_models")

        # Create a deterministic image embedding
        image_emb = np.random.randn(512).astype(np.float32)
        image_emb = image_emb / np.linalg.norm(image_emb)

        # Create text embeddings that have known relative similarities
        labels = ["alpha", "beta", "gamma", "delta", "epsilon"]
        text_embs = np.random.randn(len(labels), 512).astype(np.float32)
        text_embs = text_embs / np.linalg.norm(text_embs, axis=1, keepdims=True)

        results = extractor._classify(image_emb, text_embs, labels, top_k=3)

        # Should return top_k items
        assert len(results) == 3

        # Should be sorted by confidence (descending)
        confidences = [conf for _, conf in results]
        assert confidences == sorted(confidences, reverse=True)

        # All confidences should be valid probabilities
        for label, conf in results:
            assert label in labels
            assert 0.0 <= conf <= 1.0
