"""Export panel for high-resolution PNG image export.

Provides resolution selection (quick buttons, presets dropdown,
custom dimensions), transparent background toggle, and export
trigger with file save dialog.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import EXPORT_MAX_RESOLUTION
from apollo7.project.export import RESOLUTION_PRESETS

logger = logging.getLogger(__name__)


class ExportPanel(QtWidgets.QWidget):
    """Panel for configuring and triggering image export."""

    # Emitted when user clicks Export with (width, height, transparent, output_path)
    export_requested = QtCore.Signal(int, int, bool, str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("export-panel")
        self._viewport_size: tuple[int, int] = (1920, 1080)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Export Image")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # -- Quick resolution buttons --
        quick_row = QtWidgets.QHBoxLayout()
        quick_row.setSpacing(4)
        for label, multiplier in [("1x", 1), ("2x", 2), ("4x", 4)]:
            btn = QtWidgets.QPushButton(label)
            btn.setFixedWidth(48)
            btn.clicked.connect(lambda checked, m=multiplier: self._set_multiplier(m))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        # -- Preset dropdown --
        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self._preset_combo = QtWidgets.QComboBox()
        self._preset_combo.addItem("Custom")
        for name in RESOLUTION_PRESETS:
            w, h = RESOLUTION_PRESETS[name]
            self._preset_combo.addItem(f"{name} ({w}x{h})")
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self._preset_combo, 1)
        layout.addLayout(preset_row)

        # -- Custom resolution inputs --
        res_row = QtWidgets.QHBoxLayout()
        res_row.addWidget(QtWidgets.QLabel("W:"))
        self._width_spin = QtWidgets.QSpinBox()
        self._width_spin.setRange(1, EXPORT_MAX_RESOLUTION)
        self._width_spin.setValue(1920)
        res_row.addWidget(self._width_spin)

        res_row.addWidget(QtWidgets.QLabel("H:"))
        self._height_spin = QtWidgets.QSpinBox()
        self._height_spin.setRange(1, EXPORT_MAX_RESOLUTION)
        self._height_spin.setValue(1080)
        res_row.addWidget(self._height_spin)
        layout.addLayout(res_row)

        # -- Transparent background --
        self._transparent_cb = QtWidgets.QCheckBox("Transparent background")
        layout.addWidget(self._transparent_cb)

        # -- Export button --
        self._btn_export = QtWidgets.QPushButton("Export PNG")
        self._btn_export.setObjectName("btn-simulate")  # reuse accent style
        self._btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(self._btn_export)

        layout.addStretch()

    def set_viewport_size(self, width: int, height: int) -> None:
        """Update the viewport size used for multiplier calculations."""
        self._viewport_size = (width, height)

    def _set_multiplier(self, m: int) -> None:
        """Set resolution to viewport size * multiplier."""
        w, h = self._viewport_size
        self._width_spin.setValue(w * m)
        self._height_spin.setValue(h * m)
        self._preset_combo.setCurrentIndex(0)  # Custom

    def _on_preset_selected(self, index: int) -> None:
        """Apply selected resolution preset."""
        if index == 0:  # Custom
            return
        preset_names = list(RESOLUTION_PRESETS.keys())
        if index - 1 < len(preset_names):
            name = preset_names[index - 1]
            w, h = RESOLUTION_PRESETS[name]
            self._width_spin.setValue(w)
            self._height_spin.setValue(h)

    def _on_export_clicked(self) -> None:
        """Open save dialog and emit export_requested signal."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG Images (*.png)"
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"

        width = self._width_spin.value()
        height = self._height_spin.value()
        transparent = self._transparent_cb.isChecked()
        self.export_requested.emit(width, height, transparent, path)
