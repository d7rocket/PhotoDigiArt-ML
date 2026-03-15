"""CLIP-based semantic feature extraction via ONNX.

Produces mood tags, object tags, and a 512-dim embedding vector for
every photo using zero-shot classification with CLIP ViT-B/32.

Uses ONNX Runtime with DirectML for AMD GPU acceleration.
Falls back to CPU if DirectML is unavailable.
"""

from __future__ import annotations

import logging
import os

import cv2
import numpy as np

from apollo7.extraction.base import BaseExtractor, ExtractionResult
from apollo7.extraction.clip_tokenizer import CLIPTokenizer

logger = logging.getLogger(__name__)

# CLIP normalization constants (different from ImageNet)
_CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
_CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

# Zero-shot classification labels
_MOOD_LABELS = [
    "serene", "chaotic", "melancholic", "joyful",
    "dramatic", "mysterious", "peaceful", "energetic",
]

_OBJECT_LABELS = [
    "tree", "car", "person", "building", "water",
    "sky", "animal", "flower", "mountain", "road",
]

# Prompt templates for CLIP zero-shot (improves accuracy)
_MOOD_PROMPT = "a photo with a {} mood"
_OBJECT_PROMPT = "a photo of a {}"


class ClipExtractor(BaseExtractor):
    """Extracts semantic features using CLIP ViT-B/32 ONNX models.

    Produces mood tags, object tags (with confidence scores), and a
    512-dimensional embedding vector for each image.

    The ONNX sessions are created lazily on the first extract() call,
    not at import time, so importing this module is always cheap.

    Args:
        model_dir: Directory containing CLIP ONNX models and vocabulary.
    """

    def __init__(self, model_dir: str = "models") -> None:
        self._model_dir = model_dir
        self._visual_path = os.path.join(model_dir, "clip_vit_b32_visual.onnx")
        self._text_path = os.path.join(model_dir, "clip_vit_b32_text.onnx")
        self._visual_session = None  # Lazy-loaded
        self._text_session = None  # Lazy-loaded
        self._tokenizer = CLIPTokenizer(
            vocab_path=os.path.join(model_dir, "bpe_simple_vocab_16e6.txt.gz")
        )
        # Cache text embeddings (labels don't change between calls)
        self._mood_text_embs: np.ndarray | None = None
        self._object_text_embs: np.ndarray | None = None

    @property
    def name(self) -> str:
        return "semantic"

    def _ensure_sessions(self) -> None:
        """Create ONNX sessions on first use."""
        if self._visual_session is not None and self._text_session is not None:
            return

        for path, label in [
            (self._visual_path, "CLIP visual encoder"),
            (self._text_path, "CLIP text encoder"),
        ]:
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    f"{label} not found at '{path}'. "
                    "See models/README.md for download instructions."
                )

        import onnxruntime as ort

        available = ort.get_available_providers()
        providers: list[str] = []
        if "DmlExecutionProvider" in available:
            providers.append("DmlExecutionProvider")
        else:
            logger.warning(
                "DirectML execution provider not available. "
                "CLIP extraction will use CPU (slower). "
                "Install onnxruntime-directml for GPU acceleration."
            )
        providers.append("CPUExecutionProvider")

        self._visual_session = ort.InferenceSession(
            self._visual_path, providers=providers
        )
        self._text_session = ort.InferenceSession(
            self._text_path, providers=providers
        )
        logger.info("CLIP ONNX sessions loaded (providers: %s)", providers)

    def preprocess_clip(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for CLIP: center crop, resize 224x224, normalize, NCHW.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].

        Returns:
            (1, 3, 224, 224) float32 tensor ready for CLIP visual encoder.
        """
        h, w = image.shape[:2]

        # Center crop to square
        size = min(h, w)
        y_start = (h - size) // 2
        x_start = (w - size) // 2
        cropped = image[y_start : y_start + size, x_start : x_start + size]

        # Resize to 224x224
        # Convert to uint8 for cv2 resize, then back to float32
        img_uint8 = (np.clip(cropped, 0.0, 1.0) * 255).astype(np.uint8)
        resized = cv2.resize(img_uint8, (224, 224), interpolation=cv2.INTER_CUBIC)
        resized_float = resized.astype(np.float32) / 255.0

        # CLIP normalization
        normalized = (resized_float - _CLIP_MEAN) / _CLIP_STD

        # HWC -> NCHW
        tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)
        return tensor

    def _get_image_embedding(self, image: np.ndarray) -> np.ndarray:
        """Run visual encoder and return L2-normalized embedding.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].

        Returns:
            (512,) float32 L2-normalized embedding vector.
        """
        tensor = self.preprocess_clip(image)

        # Run visual encoder
        input_name = self._visual_session.get_inputs()[0].name
        outputs = self._visual_session.run(None, {input_name: tensor})
        embedding = outputs[0].squeeze().astype(np.float32)

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _get_text_embeddings(self, labels: list[str], prompt_template: str) -> np.ndarray:
        """Tokenize and encode text labels, return L2-normalized embeddings.

        Args:
            labels: List of text labels.
            prompt_template: Format string with {} placeholder for label.

        Returns:
            (N, 512) float32 L2-normalized embedding matrix.
        """
        # Apply prompt template
        texts = [prompt_template.format(label) for label in labels]

        # Tokenize all labels at once
        tokens = self._tokenizer.tokenize_batch(texts)

        # Run text encoder
        input_name = self._text_session.get_inputs()[0].name
        outputs = self._text_session.run(None, {input_name: tokens})
        embeddings = outputs[0].astype(np.float32)

        # L2 normalize each row
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        embeddings = embeddings / norms

        return embeddings

    def _classify(
        self,
        image_emb: np.ndarray,
        text_embs: np.ndarray,
        labels: list[str],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Zero-shot classification via cosine similarity with softmax.

        Args:
            image_emb: (512,) L2-normalized image embedding.
            text_embs: (N, 512) L2-normalized text embeddings.
            labels: N text labels corresponding to text_embs rows.
            top_k: Number of top results to return.

        Returns:
            List of (label, confidence) tuples sorted by confidence descending.
        """
        # Cosine similarity (both are already L2-normalized)
        similarities = text_embs @ image_emb  # (N,)

        # Temperature-scaled softmax (CLIP uses 100.0 logit scale)
        logit_scale = 100.0
        logits = similarities * logit_scale
        logits = logits - logits.max()  # Numerical stability
        exp_logits = np.exp(logits)
        probs = exp_logits / exp_logits.sum()

        # Sort by probability descending, take top_k
        indices = np.argsort(probs)[::-1][:top_k]

        return [(labels[i], float(probs[i])) for i in indices]

    def extract(self, image: np.ndarray) -> ExtractionResult:
        """Extract semantic features from an RGB float32 [0-1] image.

        Args:
            image: H x W x 3 numpy array, float32, values in [0.0, 1.0].

        Returns:
            ExtractionResult with:
                data: mood_tags (list of (str, float)), object_tags (list of (str, float))
                arrays: embedding (512-dim float32 vector)
        """
        self._ensure_sessions()

        # Get image embedding
        image_emb = self._get_image_embedding(image)

        # Get/cache text embeddings for mood labels
        if self._mood_text_embs is None:
            self._mood_text_embs = self._get_text_embeddings(
                _MOOD_LABELS, _MOOD_PROMPT
            )

        # Get/cache text embeddings for object labels
        if self._object_text_embs is None:
            self._object_text_embs = self._get_text_embeddings(
                _OBJECT_LABELS, _OBJECT_PROMPT
            )

        # Zero-shot classification
        mood_tags = self._classify(image_emb, self._mood_text_embs, _MOOD_LABELS, top_k=5)
        object_tags = self._classify(
            image_emb, self._object_text_embs, _OBJECT_LABELS, top_k=5
        )

        return ExtractionResult(
            extractor_name=self.name,
            data={
                "mood_tags": mood_tags,
                "object_tags": object_tags,
            },
            arrays={
                "embedding": image_emb,
            },
        )
