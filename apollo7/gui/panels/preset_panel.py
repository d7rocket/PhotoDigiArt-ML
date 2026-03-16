"""Preset browser panel with visual 2-column grid of gradient thumbnail cards.

Displays built-in and user-saved presets as PresetCard widgets in a grid
layout. Clicking a card applies its parameters via the preset_applied signal.
Includes an A/B crossfade widget in a collapsible section.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apollo7.gui.widgets.crossfade import CrossfadeWidget
from apollo7.gui.widgets.preset_card import PresetCard
from apollo7.gui.widgets.section import Section
from apollo7.project.presets import PresetManager

logger = logging.getLogger(__name__)

_GRID_COLUMNS = 2
_GRID_SPACING = 8


class PresetPanel(QtWidgets.QWidget):
    """Panel displaying presets as a 2-column grid of gradient thumbnail cards."""

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
        self._cards: list[PresetCard] = []
        self._selected_card: PresetCard | None = None
        self._setup_ui()
        self._populate_grid()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Presets")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # Scrollable grid area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._grid_container = QtWidgets.QWidget()
        self._grid_layout = QtWidgets.QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(_GRID_SPACING)
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)

        # Save button
        btn_save = QtWidgets.QPushButton("Save Current")
        btn_save.clicked.connect(self._on_save_current)
        layout.addWidget(btn_save)

        # Crossfade section
        crossfade_section = Section("Crossfade")
        self._crossfade_widget = CrossfadeWidget(
            preset_manager=self._manager, parent=self
        )
        self._crossfade_widget.crossfade_changed.connect(self._on_crossfade_changed)
        crossfade_section.content_layout.addWidget(self._crossfade_widget)
        layout.addWidget(crossfade_section)

    # ------------------------------------------------------------------
    # Grid population
    # ------------------------------------------------------------------

    def _populate_grid(self) -> None:
        """Fill grid with PresetCard widgets from PresetManager."""
        self._clear_grid()

        listing = self._manager.list_presets()
        index = 0
        for category in sorted(listing.keys()):
            names = listing[category]
            for name in names:
                try:
                    data = self._manager.load_preset(name, category)
                except Exception:
                    continue

                card = PresetCard(name, data, parent=self._grid_container)
                card.setProperty("category", category)
                card.clicked.connect(self._on_preset_clicked)
                self._grid_layout.addWidget(
                    card, index // _GRID_COLUMNS, index % _GRID_COLUMNS
                )
                self._cards.append(card)
                index += 1

        # Add stretch at bottom of grid so cards stay top-aligned
        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self._grid_layout.addItem(
            spacer, (index // _GRID_COLUMNS) + 1, 0, 1, _GRID_COLUMNS
        )

    def _clear_grid(self) -> None:
        """Remove all cards from the grid layout."""
        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_card = None
        # Remove spacer items
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh_grid(self) -> None:
        """Rebuild grid from PresetManager (call after save/delete)."""
        self._populate_grid()
        # Also refresh crossfade combo boxes
        if hasattr(self, "_crossfade_widget"):
            self._crossfade_widget.refresh_presets()

    # ------------------------------------------------------------------
    # Card interaction
    # ------------------------------------------------------------------

    def _on_preset_clicked(self, name: str) -> None:
        """Handle preset card click: select card and emit preset_applied."""
        # Find the card that was clicked
        card: PresetCard | None = None
        for c in self._cards:
            if c.preset_name == name:
                card = c
                break

        if card is None:
            return

        # Deselect previous
        if self._selected_card is not None:
            self._selected_card.set_selected(False)

        # Select new
        card.set_selected(True)
        self._selected_card = card

        # Load and emit preset data
        category = card.property("category")
        try:
            data = self._manager.load_preset(name, category)
            sim_params = data.get("sim_params", {})
            postfx_params = data.get("postfx_params", {})
            self.preset_applied.emit(sim_params, postfx_params)
            logger.info("Applied preset: %s/%s", category, name)
        except Exception as exc:
            logger.error("Failed to apply preset: %s", exc)

    # ------------------------------------------------------------------
    # Crossfade forwarding
    # ------------------------------------------------------------------

    def _on_crossfade_changed(self, lerped_preset: dict) -> None:
        """Forward crossfade result through panel signals."""
        sim_params = lerped_preset.get("sim_params", {})
        postfx_params = lerped_preset.get("postfx_params", {})
        self.preset_applied.emit(sim_params, postfx_params)
        self.crossfade_changed.emit(lerped_preset)

    # ------------------------------------------------------------------
    # Save / dialog
    # ------------------------------------------------------------------

    def _on_save_current(self) -> None:
        """Request save of current parameters."""
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

        self._manager.save_preset(
            name.strip(), category.strip(), sim_params, postfx_params
        )
        self.refresh_grid()
