"""Tests for FeatureViewerPanel.

Covers:
- Instantiation
- update_features with mock data populates sections
- clear() resets to placeholder state
- Missing extractor results show "Not extracted" gracefully
"""

from __future__ import annotations

import numpy as np
import pytest
from PySide6 import QtWidgets

from apollo7.extraction.base import ExtractionResult
from apollo7.gui.panels.feature_viewer import FeatureViewerPanel


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication exists for the test module."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _make_color_result() -> ExtractionResult:
    """Create a mock color extraction result."""
    return ExtractionResult(
        extractor_name="color",
        data={
            "dominant_colors": [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
            "color_weights": [0.5, 0.3, 0.2],
        },
        arrays={
            "rgb_histogram": np.random.randint(0, 100, (3, 64), dtype=np.int32),
        },
    )


def _make_edge_result() -> ExtractionResult:
    """Create a mock edge extraction result."""
    edge_map = np.zeros((50, 50), dtype=np.uint8)
    edge_map[10:20, 10:20] = 255  # some edges
    return ExtractionResult(
        extractor_name="edge",
        data={"contour_count": 5},
        arrays={"edge_map": edge_map},
    )


def _make_depth_result() -> ExtractionResult:
    """Create a mock depth extraction result."""
    depth_map = np.linspace(0.0, 1.0, 50 * 50).reshape(50, 50).astype(np.float32)
    return ExtractionResult(
        extractor_name="depth",
        data={},
        arrays={"depth_map": depth_map},
    )


class TestFeatureViewerPanel:
    """Test FeatureViewerPanel behavior."""

    def test_can_instantiate(self, qapp):
        """Panel should instantiate without errors."""
        panel = FeatureViewerPanel()
        assert panel is not None
        assert panel.objectName() == "feature-viewer"

    def test_update_features_populates_sections(self, qapp):
        """update_features with full data should create 3 sections."""
        panel = FeatureViewerPanel()
        features = {
            "color": _make_color_result(),
            "edge": _make_edge_result(),
            "depth": _make_depth_result(),
        }
        panel.update_features("/test/photo.jpg", features)

        # Should have 3 sections
        assert len(panel._sections) == 3
        # Placeholder should be hidden
        assert panel._placeholder.isHidden()

    def test_clear_resets_to_placeholder(self, qapp):
        """clear() should remove sections and show placeholder."""
        panel = FeatureViewerPanel()
        features = {
            "color": _make_color_result(),
            "edge": _make_edge_result(),
        }
        panel.update_features("/test/photo.jpg", features)
        assert len(panel._sections) > 0

        panel.clear()
        assert len(panel._sections) == 0
        # isHidden checks the widget's own hidden flag (not parent visibility)
        assert not panel._placeholder.isHidden()

    def test_missing_extractor_shows_not_extracted(self, qapp):
        """Missing extractors should show 'Not extracted' gracefully."""
        panel = FeatureViewerPanel()
        # Only color result, no edge or depth
        features = {
            "color": _make_color_result(),
        }
        panel.update_features("/test/photo.jpg", features)

        # Should still have 3 sections (color, edge placeholder, depth placeholder)
        assert len(panel._sections) == 3

    def test_update_features_twice_replaces_old(self, qapp):
        """Calling update_features again should replace previous sections."""
        panel = FeatureViewerPanel()
        features1 = {"color": _make_color_result()}
        panel.update_features("/test/photo1.jpg", features1)
        first_count = len(panel._sections)

        features2 = {"color": _make_color_result(), "edge": _make_edge_result()}
        panel.update_features("/test/photo2.jpg", features2)

        # Sections should be freshly built, not accumulated
        assert len(panel._sections) == 3  # always 3 sections (color, edge, depth)
