"""Tests for the feature-to-visual mapping data model and engine."""

from __future__ import annotations

import numpy as np
import pytest

from apollo7.extraction.base import ExtractionResult
from apollo7.mapping.connections import MappingConnection, MappingGraph
from apollo7.mapping.engine import MappingEngine


# ---------------------------------------------------------------------------
# MappingConnection tests
# ---------------------------------------------------------------------------

class TestMappingConnection:
    def test_connection_serialization(self):
        """to_dict/from_dict round-trip preserves all fields."""
        conn = MappingConnection(
            source_feature="semantic",
            source_key="mood_tags.serene",
            target_param="noise_frequency",
            strength=0.75,
        )
        d = conn.to_dict()
        restored = MappingConnection.from_dict(d)
        assert restored.source_feature == conn.source_feature
        assert restored.source_key == conn.source_key
        assert restored.target_param == conn.target_param
        assert restored.strength == pytest.approx(conn.strength)

    def test_connection_default_strength(self):
        """Default strength is 1.0."""
        conn = MappingConnection(
            source_feature="color",
            source_key="dominant_saturation",
            target_param="speed",
        )
        assert conn.strength == 1.0


# ---------------------------------------------------------------------------
# MappingGraph tests
# ---------------------------------------------------------------------------

class TestMappingGraph:
    def test_graph_add_remove(self):
        """Add connections, verify count, remove one, verify again."""
        graph = MappingGraph()
        c1 = MappingConnection("semantic", "mood_tags.serene", "noise_frequency", 1.0)
        c2 = MappingConnection("color", "dominant_saturation", "speed", 0.5)
        graph.add_connection(c1)
        graph.add_connection(c2)
        assert len(graph.get_connections()) == 2

        graph.remove_connection("semantic", "mood_tags.serene", "noise_frequency")
        assert len(graph.get_connections()) == 1
        assert graph.get_connections()[0].source_feature == "color"

    def test_graph_get_connections_for_target(self):
        """get_connections_for_target returns only matching connections."""
        graph = MappingGraph()
        c1 = MappingConnection("semantic", "mood_tags.serene", "speed", 1.0)
        c2 = MappingConnection("color", "dominant_saturation", "speed", 0.5)
        c3 = MappingConnection("depth", "depth_mean", "noise_frequency", 1.0)
        graph.add_connection(c1)
        graph.add_connection(c2)
        graph.add_connection(c3)

        speed_conns = graph.get_connections_for_target("speed")
        assert len(speed_conns) == 2
        assert all(c.target_param == "speed" for c in speed_conns)

    def test_graph_serialization(self):
        """Graph round-trip via to_dict/from_dict."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("semantic", "mood_tags.chaotic", "turbulence_scale", 1.5)
        )
        graph.add_connection(
            MappingConnection("edge", "edge_density", "noise_amplitude", 0.8)
        )

        d = graph.to_dict()
        restored = MappingGraph.from_dict(d)
        assert len(restored.get_connections()) == 2
        names = {c.source_key for c in restored.get_connections()}
        assert names == {"mood_tags.chaotic", "edge_density"}

    def test_graph_clear(self):
        """clear() removes all connections."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("depth", "depth_mean", "speed", 1.0)
        )
        assert len(graph.get_connections()) == 1
        graph.clear()
        assert len(graph.get_connections()) == 0


# ---------------------------------------------------------------------------
# MappingEngine tests
# ---------------------------------------------------------------------------

def _make_feature_data(**kwargs) -> dict[str, ExtractionResult]:
    """Helper to build feature data dict for engine tests."""
    results: dict[str, ExtractionResult] = {}
    for name, data in kwargs.items():
        results[name] = ExtractionResult(extractor_name=name, data=data)
    return results


class TestMappingEngine:
    def setup_method(self):
        self.engine = MappingEngine()

    def test_engine_evaluate_single(self):
        """One connection produces correct output."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("semantic", "mood_tags.serene", "noise_frequency", 1.0)
        )
        feature_data = _make_feature_data(
            semantic={"mood_tags": {"serene": 0.8, "chaotic": 0.2}}
        )
        result = self.engine.evaluate(graph, feature_data)
        assert "noise_frequency" in result
        assert result["noise_frequency"] == pytest.approx(0.8)

    def test_engine_evaluate_multiple_targets(self):
        """Different params get different values."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("semantic", "mood_tags.serene", "noise_frequency", 1.0)
        )
        graph.add_connection(
            MappingConnection("color", "dominant_saturation", "speed", 1.0)
        )
        feature_data = _make_feature_data(
            semantic={"mood_tags": {"serene": 0.8}},
            color={"dominant_saturation": 0.6},
        )
        result = self.engine.evaluate(graph, feature_data)
        assert result["noise_frequency"] == pytest.approx(0.8)
        assert result["speed"] == pytest.approx(0.6)

    def test_engine_additive_blending(self):
        """Two connections to same target sum their contributions."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("semantic", "mood_tags.serene", "speed", 1.0)
        )
        graph.add_connection(
            MappingConnection("color", "dominant_saturation", "speed", 1.0)
        )
        feature_data = _make_feature_data(
            semantic={"mood_tags": {"serene": 0.3}},
            color={"dominant_saturation": 0.4},
        )
        result = self.engine.evaluate(graph, feature_data)
        assert result["speed"] == pytest.approx(0.7)

    def test_engine_missing_feature(self):
        """Gracefully skips when feature data is missing."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("semantic", "mood_tags.serene", "speed", 1.0)
        )
        # No semantic data provided
        feature_data = _make_feature_data(
            color={"dominant_saturation": 0.5},
        )
        result = self.engine.evaluate(graph, feature_data)
        # speed should not appear or be 0 since source is missing
        assert result.get("speed", 0.0) == pytest.approx(0.0)

    def test_engine_strength_scaling(self):
        """strength=2.0 doubles the output."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("color", "dominant_saturation", "speed", 2.0)
        )
        feature_data = _make_feature_data(
            color={"dominant_saturation": 0.3},
        )
        result = self.engine.evaluate(graph, feature_data)
        assert result["speed"] == pytest.approx(0.6)

    def test_engine_negative_strength(self):
        """strength=-1.0 inverts the mapping."""
        graph = MappingGraph()
        graph.add_connection(
            MappingConnection("color", "dominant_saturation", "speed", -1.0)
        )
        feature_data = _make_feature_data(
            color={"dominant_saturation": 0.7},
        )
        result = self.engine.evaluate(graph, feature_data)
        assert result["speed"] == pytest.approx(-0.7)
