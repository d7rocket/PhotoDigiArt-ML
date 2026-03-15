"""Crossfade widget for interpolating between two presets.

Provides A/B preset selection combo boxes with a horizontal slider
that smoothly interpolates between the two selected presets using
lerp_presets.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore, QtWidgets

from apollo7.project.presets import PresetManager, lerp_presets

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Style constants (matching feature_viewer theme)
# ---------------------------------------------------------------------------
_ACCENT = "#0078FF"
_BG = "#2B2B2B"
_BG_DARK = "#1a1a1a"
_BORDER = "#3a3a3a"
_TEXT = "#e0e0e0"
_TEXT_DIM = "#808080"


class CrossfadeWidget(QtWidgets.QWidget):
    """A/B preset crossfade slider widget.

    Shows two combo boxes for preset selection (A and B) with a
    horizontal slider in between. Moving the slider interpolates
    all parameters between the two selected presets and emits the
    result via crossfade_changed.
    """

    # Emitted when slider moves: carries the lerped preset dict
    crossfade_changed = QtCore.Signal(dict)

    def __init__(
        self,
        preset_manager: PresetManager | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = preset_manager or PresetManager()
        self._preset_a: dict[str, Any] | None = None
        self._preset_b: dict[str, Any] | None = None
        self._setup_ui()
        self._populate_combos()

    def _setup_ui(self) -> None:
        """Build the crossfade UI layout."""
        self.setStyleSheet(f"""
            QWidget {{
                background: {_BG};
                color: {_TEXT};
            }}
            QComboBox {{
                background: {_BG_DARK};
                color: {_TEXT};
                border: 1px solid {_BORDER};
                border-radius: 3px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {_BG_DARK};
                color: {_TEXT};
                selection-background-color: {_ACCENT};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {_BORDER};
                height: 6px;
                background: {_BG_DARK};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {_ACCENT};
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QLabel {{
                background: transparent;
                font-weight: bold;
                font-size: 13px;
            }}
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Preset A
        label_a = QtWidgets.QLabel("A")
        label_a.setStyleSheet(f"color: {_ACCENT};")
        label_a.setFixedWidth(14)
        layout.addWidget(label_a)

        self._combo_a = QtWidgets.QComboBox()
        self._combo_a.currentIndexChanged.connect(self._on_preset_a_changed)
        layout.addWidget(self._combo_a)

        # Slider
        self._slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(0)
        self._slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self._slider.setTickInterval(10)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, 1)

        # Preset B
        label_b = QtWidgets.QLabel("B")
        label_b.setStyleSheet(f"color: {_ACCENT};")
        label_b.setFixedWidth(14)
        layout.addWidget(label_b)

        self._combo_b = QtWidgets.QComboBox()
        self._combo_b.currentIndexChanged.connect(self._on_preset_b_changed)
        layout.addWidget(self._combo_b)

    def _populate_combos(self) -> None:
        """Fill both combo boxes from PresetManager.list_presets()."""
        listing = self._manager.list_presets()
        items: list[tuple[str, str]] = []  # (display_text, category/name)
        for category, names in sorted(listing.items()):
            for name in names:
                items.append((f"{category}/{name}", category))

        for combo in (self._combo_a, self._combo_b):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(none)")
            for display_text, _category in items:
                combo.addItem(display_text)
            combo.blockSignals(False)

    def refresh_presets(self) -> None:
        """Refresh combo boxes from preset manager (call after save/delete)."""
        current_a = self._combo_a.currentText()
        current_b = self._combo_b.currentText()
        self._populate_combos()
        # Restore selections if possible
        idx_a = self._combo_a.findText(current_a)
        if idx_a >= 0:
            self._combo_a.setCurrentIndex(idx_a)
        idx_b = self._combo_b.findText(current_b)
        if idx_b >= 0:
            self._combo_b.setCurrentIndex(idx_b)

    def _load_preset_from_combo(self, combo: QtWidgets.QComboBox) -> dict[str, Any] | None:
        """Load a preset based on combo box selection."""
        text = combo.currentText()
        if text == "(none)" or "/" not in text:
            return None
        category, name = text.split("/", 1)
        try:
            return self._manager.load_preset(name, category)
        except Exception as exc:
            logger.warning("Failed to load preset %s: %s", text, exc)
            return None

    def _on_preset_a_changed(self, _index: int) -> None:
        """Handle preset A combo selection change."""
        self._preset_a = self._load_preset_from_combo(self._combo_a)
        self._emit_crossfade()

    def _on_preset_b_changed(self, _index: int) -> None:
        """Handle preset B combo selection change."""
        self._preset_b = self._load_preset_from_combo(self._combo_b)
        self._emit_crossfade()

    def _on_slider_changed(self, value: int) -> None:
        """Handle slider value change."""
        self._emit_crossfade()

    def _emit_crossfade(self) -> None:
        """Compute and emit the interpolated preset."""
        if self._preset_a is None and self._preset_b is None:
            return

        t = self._slider.value() / 100.0

        # If only one preset selected, use it directly
        if self._preset_a is None:
            empty = {"sim_params": {}, "postfx_params": {}}
            result = lerp_presets(empty, self._preset_b, t)
        elif self._preset_b is None:
            empty = {"sim_params": {}, "postfx_params": {}}
            result = lerp_presets(self._preset_a, empty, t)
        else:
            result = lerp_presets(self._preset_a, self._preset_b, t)

        self.crossfade_changed.emit(result)
