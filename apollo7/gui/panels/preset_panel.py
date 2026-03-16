"""Preset browser panel for saving, loading, and managing presets.

Provides a category-filtered preset list with apply, save, and
delete functionality.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apollo7.project.presets import PresetManager
from apollo7.gui.widgets.crossfade import CrossfadeWidget
from apollo7.gui.widgets.section import Section as _Section

logger = logging.getLogger(__name__)


class PresetPanel(QtWidgets.QWidget):
    """Panel for browsing and managing parameter presets."""

    # Emitted when user applies a preset: (sim_params_dict, postfx_params_dict)
    preset_applied = QtCore.Signal(dict, dict)
    # Emitted when user wants to save current params as preset
    save_current_requested = QtCore.Signal()
    # Emitted when crossfade slider changes: carries lerped preset dict
    crossfade_changed = QtCore.Signal(dict)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preset-panel")
        self._manager = PresetManager()
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Presets")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # Category dropdown
        cat_row = QtWidgets.QHBoxLayout()
        cat_row.addWidget(QtWidgets.QLabel("Category:"))
        self._category_combo = QtWidgets.QComboBox()
        self._category_combo.currentTextChanged.connect(self._on_category_changed)
        cat_row.addWidget(self._category_combo, 1)
        layout.addLayout(cat_row)

        # Preset list
        self._preset_list = QtWidgets.QListWidget()
        self._preset_list.currentItemChanged.connect(self._on_preset_selected)
        layout.addWidget(self._preset_list)

        # Action buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(4)

        self._btn_apply = QtWidgets.QPushButton("Apply")
        self._btn_apply.setEnabled(False)
        self._btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self._btn_apply)

        self._btn_save = QtWidgets.QPushButton("Save Current")
        self._btn_save.clicked.connect(self._on_save_current)
        btn_row.addWidget(self._btn_save)

        self._btn_delete = QtWidgets.QPushButton("Delete")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self._btn_delete)

        layout.addLayout(btn_row)

        # Crossfade section
        crossfade_section = _Section("Crossfade")
        self._crossfade_widget = CrossfadeWidget(
            preset_manager=self._manager, parent=self
        )
        self._crossfade_widget.crossfade_changed.connect(self._on_crossfade_changed)
        crossfade_section.content_layout.addWidget(self._crossfade_widget)
        layout.addWidget(crossfade_section)

        # Push everything up
        layout.addStretch()

    def _on_crossfade_changed(self, lerped_preset: dict) -> None:
        """Forward crossfade result through panel signal."""
        sim_params = lerped_preset.get("sim_params", {})
        postfx_params = lerped_preset.get("postfx_params", {})
        self.preset_applied.emit(sim_params, postfx_params)
        self.crossfade_changed.emit(lerped_preset)

    def _refresh(self) -> None:
        """Refresh category list and preset list from disk."""
        current_cat = self._category_combo.currentText()
        self._category_combo.blockSignals(True)
        self._category_combo.clear()
        categories = self._manager.get_categories()
        for cat in categories:
            self._category_combo.addItem(cat)
        # Restore selection if possible
        idx = self._category_combo.findText(current_cat)
        if idx >= 0:
            self._category_combo.setCurrentIndex(idx)
        self._category_combo.blockSignals(False)
        self._on_category_changed(self._category_combo.currentText())
        # Also refresh crossfade combo boxes
        if hasattr(self, "_crossfade_widget"):
            self._crossfade_widget.refresh_presets()

    def _on_category_changed(self, category: str) -> None:
        """Filter preset list by selected category."""
        self._preset_list.clear()
        if not category:
            return
        listing = self._manager.list_presets()
        presets = listing.get(category, [])
        for name in presets:
            # Add tooltip with key param values
            item = QtWidgets.QListWidgetItem(name)
            try:
                data = self._manager.load_preset(name, category)
                sp = data.get("sim_params", {})
                summary_parts = []
                for key in ["speed", "noise_frequency", "noise_amplitude"]:
                    if key in sp:
                        short = key.replace("noise_", "n_").replace("frequency", "freq").replace("amplitude", "amp")
                        summary_parts.append(f"{short}={sp[key]}")
                if summary_parts:
                    item.setToolTip(", ".join(summary_parts))
            except Exception:
                pass
            self._preset_list.addItem(item)

    def _on_preset_selected(self, current, previous) -> None:
        """Enable/disable buttons based on selection."""
        has_selection = current is not None
        self._btn_apply.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

    def _on_apply(self) -> None:
        """Load and apply the selected preset."""
        item = self._preset_list.currentItem()
        category = self._category_combo.currentText()
        if item is None or not category:
            return
        try:
            data = self._manager.load_preset(item.text(), category)
            sim_params = data.get("sim_params", {})
            postfx_params = data.get("postfx_params", {})
            self.preset_applied.emit(sim_params, postfx_params)
            logger.info("Applied preset: %s/%s", category, item.text())
        except Exception as exc:
            logger.error("Failed to apply preset: %s", exc)

    def _on_save_current(self) -> None:
        """Prompt user for name/category and save current parameters."""
        self.save_current_requested.emit()

    def save_preset_dialog(
        self, sim_params: dict, postfx_params: dict
    ) -> None:
        """Show dialog to save a new preset with name and category.

        Args:
            sim_params: Current simulation parameters.
            postfx_params: Current post-processing parameters.
        """
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Preset", "Preset name:"
        )
        if not ok or not name.strip():
            return

        categories = self._manager.get_categories()
        category, ok = QtWidgets.QInputDialog.getItem(
            self, "Save Preset", "Category:", categories, editable=True
        )
        if not ok or not category.strip():
            return

        self._manager.save_preset(name.strip(), category.strip(), sim_params, postfx_params)
        self._refresh()

    def _on_delete(self) -> None:
        """Delete selected preset with confirmation."""
        item = self._preset_list.currentItem()
        category = self._category_combo.currentText()
        if item is None or not category:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{item.text()}' from '{category}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self._manager.delete_preset(item.text(), category)
            self._refresh()
