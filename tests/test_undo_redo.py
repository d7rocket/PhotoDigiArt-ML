"""Tests for undo/redo system with slider debouncing.

Covers:
- ParameterChangeCommand redo/undo calls apply_fn correctly
- mergeWith collapses same-id commands
- mergeWith rejects different-id commands
- QUndoStack with 5 pushes of same param -> 1 undo reverts to original
- QUndoStack with mixed params -> each param gets its own undo entry
- ResetSectionCommand redo/undo
"""

from __future__ import annotations

import pytest
from PySide6 import QtWidgets
from PySide6.QtGui import QUndoStack

from apollo7.gui.widgets.undo_commands import ParameterChangeCommand, ResetSectionCommand


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication exists for the test module."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class TestParameterChangeCommand:
    """Test ParameterChangeCommand redo/undo behavior."""

    def test_redo_calls_apply_fn(self, qapp):
        """redo() should call apply_fn with (param_name, new_value)."""
        calls = []
        cmd = ParameterChangeCommand(
            param_name="point_size",
            old_value=2.0,
            new_value=5.0,
            apply_fn=lambda name, val: calls.append((name, val)),
            merge_id_offset=0,
        )
        cmd.redo()
        assert calls == [("point_size", 5.0)]

    def test_undo_calls_apply_fn(self, qapp):
        """undo() should call apply_fn with (param_name, old_value)."""
        calls = []
        cmd = ParameterChangeCommand(
            param_name="opacity",
            old_value=0.8,
            new_value=1.0,
            apply_fn=lambda name, val: calls.append((name, val)),
            merge_id_offset=1,
        )
        # redo first (as Qt would)
        cmd.redo()
        calls.clear()
        cmd.undo()
        assert calls == [("opacity", 0.8)]

    def test_merge_same_id(self, qapp):
        """mergeWith() should collapse consecutive same-param commands."""
        calls = []
        fn = lambda name, val: calls.append((name, val))
        cmd1 = ParameterChangeCommand("point_size", 2.0, 3.0, fn, merge_id_offset=0)
        cmd2 = ParameterChangeCommand("point_size", 3.0, 4.0, fn, merge_id_offset=0)

        result = cmd1.mergeWith(cmd2)
        assert result is True
        # After merge, cmd1 should redo to 4.0 (cmd2's new_value)
        calls.clear()
        cmd1.redo()
        assert calls == [("point_size", 4.0)]
        # And undo back to 2.0 (cmd1's original old_value)
        calls.clear()
        cmd1.undo()
        assert calls == [("point_size", 2.0)]

    def test_merge_different_id_rejected(self, qapp):
        """mergeWith() should reject commands with different merge IDs."""
        fn = lambda name, val: None
        cmd1 = ParameterChangeCommand("point_size", 2.0, 3.0, fn, merge_id_offset=0)
        cmd2 = ParameterChangeCommand("opacity", 0.5, 0.8, fn, merge_id_offset=1)

        result = cmd1.mergeWith(cmd2)
        assert result is False

    def test_stack_five_pushes_same_param_one_undo(self, qapp):
        """5 rapid slider changes on same param -> 1 undo reverts to original."""
        applied = {}

        def apply_fn(name, val):
            applied[name] = val

        stack = QUndoStack()

        # Simulate 5 rapid slider drags (same param)
        values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0]  # old=2, then 3,4,5,6,7
        for i in range(5):
            cmd = ParameterChangeCommand(
                param_name="point_size",
                old_value=values[i],
                new_value=values[i + 1],
                apply_fn=apply_fn,
                merge_id_offset=0,
            )
            stack.push(cmd)

        # Should have only 1 entry due to merging
        assert stack.count() == 1
        assert applied["point_size"] == 7.0

        # Single undo should revert to original value (2.0)
        stack.undo()
        assert applied["point_size"] == 2.0

    def test_stack_mixed_params_separate_entries(self, qapp):
        """Mixed param changes should produce separate undo entries."""
        applied = {}

        def apply_fn(name, val):
            applied[name] = val

        stack = QUndoStack()

        # Push point_size change
        stack.push(ParameterChangeCommand("point_size", 2.0, 5.0, apply_fn, 0))
        # Push opacity change
        stack.push(ParameterChangeCommand("opacity", 1.0, 0.5, apply_fn, 1))

        assert stack.count() == 2

        # Undo opacity
        stack.undo()
        assert applied["opacity"] == 1.0
        assert applied.get("point_size") == 5.0  # unchanged

        # Undo point_size
        stack.undo()
        assert applied["point_size"] == 2.0


class TestResetSectionCommand:
    """Test ResetSectionCommand for batch reset operations."""

    def test_redo_applies_defaults(self, qapp):
        """redo() should apply all default values."""
        applied = {}

        def apply_fn(name, val):
            applied[name] = val

        params = {
            "point_size": (5.0, 2.0),  # (old_value, default_value)
            "opacity": (0.5, 1.0),
        }
        cmd = ResetSectionCommand(params, apply_fn)
        cmd.redo()

        assert applied["point_size"] == 2.0
        assert applied["opacity"] == 1.0

    def test_undo_restores_old_values(self, qapp):
        """undo() should restore all old values."""
        applied = {}

        def apply_fn(name, val):
            applied[name] = val

        params = {
            "point_size": (5.0, 2.0),
            "opacity": (0.5, 1.0),
        }
        cmd = ResetSectionCommand(params, apply_fn)
        cmd.redo()
        cmd.undo()

        assert applied["point_size"] == 5.0
        assert applied["opacity"] == 0.5

    def test_does_not_merge(self, qapp):
        """ResetSectionCommand should never merge (id returns -1)."""
        fn = lambda name, val: None
        cmd = ResetSectionCommand({"x": (1.0, 0.0)}, fn)
        assert cmd.id() == -1
