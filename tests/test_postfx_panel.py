"""Tests for PostFX controls panel.

Covers:
- PostFXPanel instantiation (all sections, sliders, checkboxes)
- postfx_param_changed signal emission on slider change
- postfx_toggled signal emission on checkbox toggle
- postfx_section_reset signal emission on reset button click
- Undo stack integration (merge IDs >= 100)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6 import QtWidgets
from PySide6.QtGui import QUndoStack

from apollo7.gui.panels.postfx_panel import PostFXPanel
from apollo7.gui.widgets.undo_commands import ParameterChangeCommand


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication exists for the test module."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class TestPostFXPanelCreation:
    """Test PostFXPanel widget creation."""

    def test_panel_instantiates(self, qapp):
        panel = PostFXPanel()
        assert panel is not None

    def test_has_bloom_checkbox(self, qapp):
        panel = PostFXPanel()
        assert panel.chk_bloom is not None
        assert panel.chk_bloom.isChecked() is True  # bloom on by default

    def test_has_dof_checkbox(self, qapp):
        panel = PostFXPanel()
        assert panel.chk_dof is not None
        assert panel.chk_dof.isChecked() is False  # dof off by default

    def test_has_ssao_checkbox(self, qapp):
        panel = PostFXPanel()
        assert panel.chk_ssao is not None
        assert panel.chk_ssao.isChecked() is False

    def test_has_trails_checkbox(self, qapp):
        panel = PostFXPanel()
        assert panel.chk_trails is not None
        assert panel.chk_trails.isChecked() is False

    def test_has_all_sliders(self, qapp):
        panel = PostFXPanel()
        expected_params = [
            "bloom_strength",
            "dof_focal_distance",
            "dof_aperture",
            "ssao_radius",
            "ssao_intensity",
            "trail_length",
        ]
        for param in expected_params:
            assert param in panel._sliders, f"Missing slider for {param}"

    def test_has_reset_buttons(self, qapp):
        panel = PostFXPanel()
        assert panel.btn_reset_bloom is not None
        assert panel.btn_reset_dof is not None
        assert panel.btn_reset_ssao is not None
        assert panel.btn_reset_trails is not None
        assert panel.btn_reset_all is not None


class TestPostFXPanelSignals:
    """Test PostFXPanel signal emission."""

    def test_param_changed_signal(self, qapp):
        panel = PostFXPanel()
        received = []
        panel.postfx_param_changed.connect(lambda name, val: received.append((name, val)))

        # Move bloom strength slider
        slider, _, _ = panel._sliders["bloom_strength"]
        slider.setValue(50)

        assert len(received) > 0
        assert received[-1][0] == "bloom_strength"

    def test_toggled_signal_bloom(self, qapp):
        panel = PostFXPanel()
        received = []
        panel.postfx_toggled.connect(lambda name, val: received.append((name, val)))

        # Toggle bloom off
        panel.chk_bloom.setChecked(False)
        assert ("bloom", False) in received

    def test_toggled_signal_dof(self, qapp):
        panel = PostFXPanel()
        received = []
        panel.postfx_toggled.connect(lambda name, val: received.append((name, val)))

        panel.chk_dof.setChecked(True)
        assert ("dof", True) in received

    def test_section_reset_signal(self, qapp):
        panel = PostFXPanel()
        received = []
        panel.postfx_section_reset.connect(lambda name: received.append(name))

        panel.btn_reset_bloom.click()
        assert "bloom" in received

    def test_reset_all_signal(self, qapp):
        panel = PostFXPanel()
        received = []
        panel.postfx_reset_all.connect(lambda: received.append("all"))

        panel.btn_reset_all.click()
        assert "all" in received


class TestPostFXUndoIntegration:
    """Test undo stack integration for postfx param changes."""

    def test_push_param_change_merge_id_gte_100(self, qapp):
        """PostFX param changes should use merge_id_offset >= 100."""
        from apollo7.gui.main_window import MainWindow

        # Verify the merge ID mapping
        assert MainWindow._POSTFX_MERGE_IDS["bloom_strength"] >= 100
        assert MainWindow._POSTFX_MERGE_IDS["dof_focal_distance"] >= 100
        assert MainWindow._POSTFX_MERGE_IDS["trail_length"] >= 100

    def test_undo_command_with_high_merge_id(self, qapp):
        """Commands with merge_id >= 100 should not merge with sim params."""
        calls = []
        fn = lambda name, val: calls.append((name, val))

        # Sim param command (offset 0)
        sim_cmd = ParameterChangeCommand("speed", 1.0, 2.0, fn, merge_id_offset=0)
        # PostFX param command (offset 100)
        pfx_cmd = ParameterChangeCommand("bloom_strength", 0.04, 0.5, fn, merge_id_offset=100)

        # They should NOT merge (different IDs)
        assert sim_cmd.mergeWith(pfx_cmd) is False

    def test_same_postfx_params_merge(self, qapp):
        """Consecutive changes to the same postfx param should merge."""
        calls = []
        fn = lambda name, val: calls.append((name, val))

        cmd1 = ParameterChangeCommand("bloom_strength", 0.04, 0.5, fn, merge_id_offset=100)
        cmd2 = ParameterChangeCommand("bloom_strength", 0.5, 1.0, fn, merge_id_offset=100)

        assert cmd1.mergeWith(cmd2) is True
        calls.clear()
        cmd1.redo()
        assert calls == [("bloom_strength", 1.0)]
