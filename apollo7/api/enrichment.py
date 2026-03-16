"""Claude API enrichment service for richer semantic descriptions.

Provides optional AI-powered enrichment of photo tags with artistic
descriptions and creative mapping suggestions. All methods gracefully
return None/empty when API is unavailable -- offline-first guarantee.

Usage:
    svc = EnrichmentService(api_key="sk-...", enabled=True)
    result = svc.enrich_tags("photo.jpg", [("serene", 0.85)])
    suggestions = svc.suggest_mappings(tags, ["speed", "turbulence"])
    params = svc.suggest_parameters("photo.jpg")  # SculptureParams via messages.parse()
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field

from PySide6 import QtCore

from apollo7.api.models import SculptureParams

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

    def _load_image_content(
        self, image_path: str
    ) -> list[dict] | None:
        """Load and base64-encode an image for Claude API content blocks.

        Returns a list with image + text content blocks, or None on error.
        """
        try:
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            ext = image_path.lower().rsplit(".", 1)[-1] if "." in image_path else "jpeg"
            media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
            media_type = media_types.get(ext, "image/jpeg")

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            }
        except Exception as exc:
            logger.warning("Failed to load image %s: %s", image_path, exc)
            return None

    def suggest_parameters(
        self, image_path: str
    ) -> SculptureParams | None:
        """Analyze a photo and suggest sculpture parameters via Claude API.

        Uses messages.create() with JSON output and Pydantic validation
        for type-safe, bounded parameter suggestions.

        Args:
            image_path: Path to the photo file.

        Returns:
            SculptureParams with suggested values and artistic rationale,
            or None if API is unavailable or call fails.
        """
        if not self._api_key or not self._enabled:
            return None

        try:
            client = self._get_client()
            if client is None:
                return None

            image_block = self._load_image_content(image_path)
            if image_block is None:
                return None

            system_prompt = (
                "You are an art advisor for Apollo 7, a 3D data sculpture tool "
                "that transforms photos into living particle sculptures. Analyze "
                "the photo and suggest simulation parameters that would create a "
                "compelling sculpture capturing the photo's mood, energy, and "
                "visual character.\n\n"
                "Respond with ONLY a JSON object (no markdown, no extra text) with these fields:\n"
                '- "rationale": string (2-3 sentences explaining how the photo maps to parameters)\n'
                '- "solver_iterations": integer 1-6 (1=ethereal gas, 6=dense liquid)\n'
                '- "home_strength": float 0.1-20.0 (how tightly particles hold form)\n'
                '- "noise_amplitude": float 0.0-5.0 (organic motion strength)\n'
                '- "breathing_rate": float 0.05-0.5 (breathing animation speed)\n'
                '- "point_size": float 0.5-10.0 (particle visual size)\n'
                '- "opacity": float 0.0-1.0 (particle transparency)'
            )

            content = [
                image_block,
                {
                    "type": "text",
                    "text": (
                        "Analyze this photo and suggest sculpture parameters. "
                        "Consider: the photo's mood (calm vs energetic), visual "
                        "complexity (simple vs detailed), color palette (muted vs "
                        "vibrant), and subject matter. Your rationale should explain "
                        "HOW the photo's qualities map to your parameter choices."
                    ),
                },
            ]

            response = client.messages.create(
                model=self._model,
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )

            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3].strip()

            data = json.loads(text)
            params = SculptureParams(**data)
            return params.clamp_to_bounds()

        except Exception as exc:
            logger.warning("Parameter suggestion API call failed: %s", exc)
            return None

    def refine_parameters(
        self,
        image_path: str,
        current_params: dict,
        direction: str,
    ) -> SculptureParams | None:
        """Refine sculpture parameters in a given direction via Claude API.

        Takes the current parameter set and a direction string (e.g.
        "more fluid", "more structured") and asks Claude to adjust.

        Args:
            image_path: Path to the photo file.
            current_params: Current parameter dict (from to_param_dict).
            direction: Natural language direction for refinement.

        Returns:
            SculptureParams with adjusted values, or None if unavailable.
        """
        if not self._api_key or not self._enabled:
            return None

        try:
            client = self._get_client()
            if client is None:
                return None

            image_block = self._load_image_content(image_path)
            if image_block is None:
                return None

            system_prompt = (
                "You are an art advisor for Apollo 7, a 3D data sculpture tool "
                "that transforms photos into living particle sculptures.\n\n"
                "Respond with ONLY a JSON object (no markdown, no extra text) with these fields:\n"
                '- "rationale": string (2-3 sentences explaining your adjustments)\n'
                '- "solver_iterations": integer 1-6 (1=ethereal gas, 6=dense liquid)\n'
                '- "home_strength": float 0.1-20.0 (how tightly particles hold form)\n'
                '- "noise_amplitude": float 0.0-5.0 (organic motion strength)\n'
                '- "breathing_rate": float 0.05-0.5 (breathing animation speed)\n'
                '- "point_size": float 0.5-10.0 (particle visual size)\n'
                '- "opacity": float 0.0-1.0 (particle transparency)'
            )

            content = [
                image_block,
                {
                    "type": "text",
                    "text": (
                        f"I applied these parameters to the sculpture: "
                        f"{json.dumps(current_params, indent=2)}\n\n"
                        f"I'd like the sculpture to be '{direction}'. Adjust the "
                        f"parameters in that direction while keeping the photo's "
                        f"character. Explain your changes in the rationale."
                    ),
                },
            ]

            response = client.messages.create(
                model=self._model,
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )

            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3].strip()

            data = json.loads(text)
            params = SculptureParams(**data)
            return params.clamp_to_bounds()

        except Exception as exc:
            logger.warning("Parameter refinement API call failed: %s", exc)
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
    params_suggested = QtCore.Signal(object)  # SculptureParams
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
        mode: str = "enrich",  # "enrich", "suggest", "both", "suggest_params", "refine_params"
        current_params: dict | None = None,
        direction: str | None = None,
    ) -> None:
        super().__init__()
        self.signals = _EnrichmentWorkerSignals()
        self.setAutoDelete(True)

        self._service = service
        self._image_path = image_path
        self._basic_tags = basic_tags or []
        self._available_params = available_params or []
        self._mode = mode
        self._current_params = current_params
        self._direction = direction

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

            if self._mode == "suggest_params" and self._image_path:
                params = self._service.suggest_parameters(self._image_path)
                self.signals.params_suggested.emit(params)

            if self._mode == "refine_params" and self._image_path:
                params = self._service.refine_parameters(
                    self._image_path,
                    self._current_params or {},
                    self._direction or "",
                )
                self.signals.params_suggested.emit(params)

        except Exception as exc:
            logger.error("EnrichmentWorker failed: %s", exc)
            self.signals.error.emit(str(exc))
