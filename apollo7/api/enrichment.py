"""Claude API enrichment service for richer semantic descriptions.

Provides optional AI-powered enrichment of photo tags with artistic
descriptions and creative mapping suggestions. All methods gracefully
return None/empty when API is unavailable -- offline-first guarantee.

Usage:
    svc = EnrichmentService(api_key="sk-...", enabled=True)
    result = svc.enrich_tags("photo.jpg", [("serene", 0.85)])
    suggestions = svc.suggest_mappings(tags, ["speed", "turbulence"])
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field

from PySide6 import QtCore

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result from Claude API enrichment.

    Attributes:
        description: Artistic mood/content description of the photo.
        suggestion: Creative sculpting suggestion for the data sculpture.
        mapping_suggestions: Suggested feature-to-param connections as dicts.
    """

    description: str | None = None
    suggestion: str | None = None
    mapping_suggestions: list[dict] | None = None


# Default model for enrichment calls
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


class EnrichmentService:
    """Claude API enrichment with offline-first fallback.

    All methods return None or empty list when:
    - No API key provided
    - Service is disabled (enabled=False)
    - API call fails for any reason

    API calls are synchronous in this class. Use EnrichmentWorker
    for background thread execution with Qt signals.
    """

    def __init__(
        self,
        api_key: str | None = None,
        enabled: bool = True,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key
        self._enabled = enabled
        self._model = model
        self._client: object | None = None  # Lazy anthropic.Anthropic

    def _get_client(self) -> object | None:
        """Lazily create the Anthropic client."""
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
            return self._client
        except ImportError:
            logger.warning("anthropic package not installed; enrichment unavailable")
            return None
        except Exception as exc:
            logger.warning("Failed to create Anthropic client: %s", exc)
            return None

    def enrich_tags(
        self,
        image_path: str,
        basic_tags: list[tuple[str, float]],
    ) -> EnrichmentResult | None:
        """Enrich tags with artistic description via Claude API.

        Args:
            image_path: Path to the photo file.
            basic_tags: List of (label, confidence) tuples from CLIP.

        Returns:
            EnrichmentResult with description and suggestion, or None
            if API is unavailable or call fails.
        """
        if not self._api_key or not self._enabled:
            return None

        try:
            client = self._get_client()
            if client is None:
                return None

            # Load and base64 encode image
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine media type
            ext = image_path.lower().rsplit(".", 1)[-1] if "." in image_path else "jpeg"
            media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
            media_type = media_types.get(ext, "image/jpeg")

            tags_str = ", ".join(f"{label} ({conf:.2f})" for label, conf in basic_tags)

            response = client.messages.create(
                model=self._model,
                max_tokens=256,
                system="You are an art advisor analyzing photos for a 3D data sculpture tool.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"These tags were detected: {tags_str}. "
                                    "Provide JSON with two keys: "
                                    '"description" (artistic mood description, 1-2 sentences) '
                                    'and "suggestion" (how to map features to 3D visuals, 1 sentence).'
                                ),
                            },
                        ],
                    }
                ],
            )

            # Parse JSON from response
            text = response.content[0].text
            # Try to extract JSON from response text
            data = json.loads(text)
            return EnrichmentResult(
                description=data.get("description"),
                suggestion=data.get("suggestion"),
            )

        except Exception as exc:
            logger.warning("Enrichment API call failed: %s", exc)
            return None

    def suggest_mappings(
        self,
        tags: list[tuple[str, float]],
        available_params: list[str],
    ) -> list[dict]:
        """Suggest creative feature-to-parameter mappings via Claude API.

        Args:
            tags: List of (label, confidence) tuples from CLIP.
            available_params: List of simulation parameter names.

        Returns:
            List of mapping suggestion dicts, or empty list if API
            unavailable or call fails.
        """
        if not self._api_key or not self._enabled:
            return []

        if not tags or not available_params:
            return []

        try:
            client = self._get_client()
            if client is None:
                return []

            tags_str = ", ".join(f"{label} ({conf:.2f})" for label, conf in tags)
            params_str = ", ".join(available_params)

            response = client.messages.create(
                model=self._model,
                max_tokens=512,
                system="You are an art advisor for a 3D data sculpture tool.",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Given these semantic tags: {tags_str}\n"
                            f"And these visual parameters: {params_str}\n\n"
                            "Suggest 3-5 creative mappings. Respond as a JSON array of objects "
                            "with keys: source_key, target_param, strength (0-2), reasoning."
                        ),
                    }
                ],
            )

            text = response.content[0].text
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return []

        except Exception as exc:
            logger.warning("Mapping suggestion API call failed: %s", exc)
            return []


class _EnrichmentWorkerSignals(QtCore.QObject):
    """Signals for EnrichmentWorker."""

    enrichment_ready = QtCore.Signal(object)  # EnrichmentResult
    suggestions_ready = QtCore.Signal(list)   # list[dict]
    error = QtCore.Signal(str)                # error message


class EnrichmentWorker(QtCore.QRunnable):
    """Background worker for enrichment API calls.

    Wraps EnrichmentService calls in a QRunnable for background execution
    via QThreadPool. Results delivered via Qt signals.

    Usage:
        worker = EnrichmentWorker(service, image_path, tags, params)
        worker.signals.enrichment_ready.connect(on_enrichment)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        service: EnrichmentService,
        image_path: str | None = None,
        basic_tags: list[tuple[str, float]] | None = None,
        available_params: list[str] | None = None,
        mode: str = "enrich",  # "enrich", "suggest", or "both"
    ) -> None:
        super().__init__()
        self.signals = _EnrichmentWorkerSignals()
        self.setAutoDelete(True)

        self._service = service
        self._image_path = image_path
        self._basic_tags = basic_tags or []
        self._available_params = available_params or []
        self._mode = mode

    def run(self) -> None:
        """Execute enrichment in background thread."""
        try:
            if self._mode in ("enrich", "both") and self._image_path:
                result = self._service.enrich_tags(
                    self._image_path, self._basic_tags
                )
                self.signals.enrichment_ready.emit(result)

            if self._mode in ("suggest", "both"):
                suggestions = self._service.suggest_mappings(
                    self._basic_tags, self._available_params
                )
                self.signals.suggestions_ready.emit(suggestions)

        except Exception as exc:
            logger.error("EnrichmentWorker failed: %s", exc)
            self.signals.error.emit(str(exc))
