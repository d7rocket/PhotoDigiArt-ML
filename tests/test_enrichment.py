"""Tests for Claude API enrichment service.

Covers:
- Offline fallback (no API key returns None/empty)
- Successful enrichment with mocked API client
- API error handling (graceful fallback)
- Mapping suggestions with mocked client
- ENRICHMENT_ENABLED flag respected
- Core features work without API key
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apollo7.api.enrichment import EnrichmentResult, EnrichmentService


class TestOfflineFallback:
    """Verify all methods return None/empty when no API key is set."""

    def test_enrich_tags_no_key_returns_none(self):
        """enrich_tags with api_key=None should return None immediately."""
        svc = EnrichmentService(api_key=None)
        result = svc.enrich_tags("test.jpg", [("serene", 0.8)])
        assert result is None

    def test_suggest_mappings_no_key_returns_empty(self):
        """suggest_mappings with api_key=None should return empty list."""
        svc = EnrichmentService(api_key=None)
        result = svc.suggest_mappings(
            [("serene", 0.8)], ["speed", "turbulence"]
        )
        assert result == []


class TestEnrichTagsSuccess:
    """Verify enrich_tags calls Claude API and parses response."""

    def test_enrich_tags_returns_enrichment_result(self, tmp_path):
        """Mock anthropic client; verify EnrichmentResult structure."""
        # Create a tiny test image
        img_path = tmp_path / "test.jpg"
        # Minimal JPEG-like bytes (just needs to be readable)
        from PIL import Image
        img = Image.new("RGB", (10, 10), (128, 64, 32))
        img.save(str(img_path), "JPEG")

        # Mock response from Claude
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps({
            "description": "A serene landscape bathed in golden light",
            "suggestion": "Map warmth to particle speed for flowing energy",
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        svc = EnrichmentService(api_key="test-key-123")
        svc._client = mock_client

        result = svc.enrich_tags(
            str(img_path), [("serene", 0.85), ("landscape", 0.72)]
        )

        assert result is not None
        assert isinstance(result, EnrichmentResult)
        assert result.description == "A serene landscape bathed in golden light"
        assert result.suggestion == "Map warmth to particle speed for flowing energy"
        mock_client.messages.create.assert_called_once()


class TestEnrichTagsError:
    """Verify enrich_tags handles API errors gracefully."""

    def test_api_error_returns_none(self, tmp_path):
        """When API call raises exception, return None gracefully."""
        img_path = tmp_path / "test.jpg"
        from PIL import Image
        img = Image.new("RGB", (10, 10), (128, 64, 32))
        img.save(str(img_path), "JPEG")

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Network error")

        svc = EnrichmentService(api_key="test-key-123")
        svc._client = mock_client

        result = svc.enrich_tags(
            str(img_path), [("serene", 0.85)]
        )
        assert result is None


class TestSuggestMappings:
    """Verify suggest_mappings calls Claude API and parses response."""

    def test_suggest_mappings_success(self):
        """Mock client returns valid JSON; verify parsed list."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps([
            {
                "source_key": "mood_tags.serene",
                "target_param": "speed",
                "strength": 0.7,
                "reasoning": "Serenity maps to slower movement",
            },
            {
                "source_key": "mood_tags.chaotic",
                "target_param": "turbulence",
                "strength": 1.2,
                "reasoning": "Chaos maps to turbulence",
            },
        ])

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        svc = EnrichmentService(api_key="test-key-123")
        svc._client = mock_client

        result = svc.suggest_mappings(
            [("serene", 0.85), ("chaotic", 0.3)],
            ["speed", "turbulence", "gravity_y"],
        )

        assert len(result) == 2
        assert result[0]["source_key"] == "mood_tags.serene"
        assert result[0]["target_param"] == "speed"
        mock_client.messages.create.assert_called_once()

    def test_suggest_mappings_api_error_returns_empty(self):
        """When API call raises, return empty list."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("Rate limited")

        svc = EnrichmentService(api_key="test-key-123")
        svc._client = mock_client

        result = svc.suggest_mappings(
            [("serene", 0.85)], ["speed"]
        )
        assert result == []


class TestEnrichmentDisabled:
    """Verify ENRICHMENT_ENABLED=False prevents API calls."""

    def test_enrichment_disabled_skips_api(self, tmp_path):
        """With ENRICHMENT_ENABLED=False, no API calls even with key."""
        img_path = tmp_path / "test.jpg"
        from PIL import Image
        img = Image.new("RGB", (10, 10), (128, 64, 32))
        img.save(str(img_path), "JPEG")

        mock_client = MagicMock()
        svc = EnrichmentService(api_key="test-key-123", enabled=False)
        svc._client = mock_client

        result = svc.enrich_tags(str(img_path), [("serene", 0.85)])
        assert result is None
        mock_client.messages.create.assert_not_called()

        mappings = svc.suggest_mappings([("serene", 0.85)], ["speed"])
        assert mappings == []
        mock_client.messages.create.assert_not_called()


class TestCoreFeaturesWithoutAPI:
    """Verify core features work without API key set."""

    def test_clip_extractor_importable(self):
        """ClipExtractor should import without API key."""
        from apollo7.extraction.clip import ClipExtractor
        ext = ClipExtractor()
        assert ext is not None

    def test_enrichment_service_no_crash(self):
        """EnrichmentService with no key should not crash on any method."""
        svc = EnrichmentService()
        assert svc.enrich_tags("nonexistent.jpg", []) is None
        assert svc.suggest_mappings([], []) == []
