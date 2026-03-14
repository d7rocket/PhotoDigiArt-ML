"""Bottom strip showing extracted feature thumbnails as horizontal cards.

Displays color palette swatches, edge map thumbnails, and (later) depth map
previews in a collapsible, horizontally scrollable strip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from apollo7.extraction.base import ExtractionResult

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_CARD_BG = "#2d2d2d"
_CARD_BORDER = "#3a3a3a"
_CARD_RADIUS = 6
_CARD_MIN_W = 160
_CARD_MIN_H = 100
_SWATCH_SIZE = 20
_THUMB_H = 64


class _FeatureCard(QtWidgets.QFrame):
    """Base card widget for a single extracted feature."""

    def __init__(self, title: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feature-card")
        self.setMinimumSize(_CARD_MIN_W, _CARD_MIN_H)
        self.setStyleSheet(
            f"""
            QFrame#feature-card {{
                background: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: {_CARD_RADIUS}px;
                padding: 6px;
            }}
            """
        )

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(4)

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("color: #b0b0b0; font-size: 11px; font-weight: 600;")
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._layout.addWidget(label)


class ColorPaletteCard(_FeatureCard):
    """Card showing dominant color swatches."""

    def __init__(
        self, result: ExtractionResult, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__("Color Palette", parent)
        colors = result.data.get("dominant_colors", [])

        swatch_container = QtWidgets.QWidget()
        swatch_layout = QtWidgets.QGridLayout(swatch_container)
        swatch_layout.setContentsMargins(0, 2, 0, 2)
        swatch_layout.setSpacing(3)

        cols = 6
        for i, rgb in enumerate(colors[:18]):  # max 18 swatches (3 rows x 6)
            swatch = QtWidgets.QLabel()
            swatch.setFixedSize(_SWATCH_SIZE, _SWATCH_SIZE)
            r, g, b = rgb
            swatch.setStyleSheet(
                f"background: rgb({r},{g},{b}); "
                f"border: 1px solid {_CARD_BORDER}; "
                f"border-radius: 3px;"
            )
            swatch_layout.addWidget(swatch, i // cols, i % cols)

        self._layout.addWidget(swatch_container)
        self._layout.addStretch()


class EdgeMapCard(_FeatureCard):
    """Card showing edge map as a grayscale thumbnail."""

    def __init__(
        self, result: ExtractionResult, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__("Edge Map", parent)
        edge_map = result.arrays.get("edge_map")

        thumb_label = QtWidgets.QLabel()
        thumb_label.setAlignment(QtCore.Qt.AlignCenter)

        if edge_map is not None:
            h, w = edge_map.shape[:2]
            aspect = w / max(h, 1)
            thumb_w = int(_THUMB_H * aspect)
            # Scale to thumbnail size
            qimg = QtGui.QImage(
                edge_map.data, w, h, w, QtGui.QImage.Format_Grayscale8
            )
            pixmap = QtGui.QPixmap.fromImage(qimg).scaled(
                thumb_w,
                _THUMB_H,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            thumb_label.setPixmap(pixmap)
        else:
            thumb_label.setText("No edge data")
            thumb_label.setStyleSheet("color: #666;")

        self._layout.addWidget(thumb_label)
        self._layout.addStretch()


class DepthMapCard(_FeatureCard):
    """Placeholder card for depth map (populated in Plan 04)."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("Depth Map", parent)
        placeholder = QtWidgets.QLabel("Available after depth extraction")
        placeholder.setStyleSheet("color: #555; font-size: 10px;")
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        placeholder.setWordWrap(True)
        self._layout.addWidget(placeholder)
        self._layout.addStretch()


class FeatureStripPanel(QtWidgets.QWidget):
    """Collapsible bottom strip showing extracted features as horizontal cards."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feature-strip")
        self.setStyleSheet(
            """
            QWidget#feature-strip {
                background: #1e1e1e;
                border-top: 1px solid #333;
            }
            """
        )

        outer_layout = QtWidgets.QHBoxLayout(self)
        outer_layout.setContentsMargins(8, 4, 8, 4)
        outer_layout.setSpacing(8)

        # Section label with collapse toggle
        label_container = QtWidgets.QVBoxLayout()
        label_container.setSpacing(2)

        self._section_label = QtWidgets.QLabel("Features")
        self._section_label.setStyleSheet(
            "color: #888; font-size: 11px; font-weight: 700; letter-spacing: 1px;"
        )
        self._section_label.setAlignment(QtCore.Qt.AlignCenter)
        label_container.addWidget(self._section_label)

        self._toggle_btn = QtWidgets.QPushButton("Hide")
        self._toggle_btn.setFixedSize(40, 18)
        self._toggle_btn.setStyleSheet(
            """
            QPushButton {
                background: #333; color: #888; border: none;
                border-radius: 3px; font-size: 9px;
            }
            QPushButton:hover { background: #444; color: #aaa; }
            """
        )
        self._toggle_btn.clicked.connect(self._toggle_cards)
        label_container.addWidget(self._toggle_btn, alignment=QtCore.Qt.AlignCenter)
        label_container.addStretch()

        outer_layout.addLayout(label_container)

        # Scrollable card area
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
            QScrollBar:horizontal {
                height: 6px; background: #1e1e1e;
            }
            QScrollBar::handle:horizontal {
                background: #444; border-radius: 3px; min-width: 30px;
            }
            """
        )

        self._card_container = QtWidgets.QWidget()
        self._card_layout = QtWidgets.QHBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(8)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        outer_layout.addWidget(self._scroll, stretch=1)

        # Placeholder text
        self._placeholder = QtWidgets.QLabel("Select a photo to view features")
        self._placeholder.setStyleSheet("color: #555; font-size: 12px;")
        self._placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self._card_layout.insertWidget(0, self._placeholder)

        self._cards_visible = True

    def update_features(
        self, photo_path: str, results: dict[str, "ExtractionResult"]
    ) -> None:
        """Create/update feature cards from extraction results."""
        self._clear_cards()
        self._placeholder.hide()

        if "color" in results:
            card = ColorPaletteCard(results["color"])
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

        if "edge" in results:
            card = EdgeMapCard(results["edge"])
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

        # Depth placeholder always shown
        depth_card = DepthMapCard()
        self._card_layout.insertWidget(self._card_layout.count() - 1, depth_card)

    def clear(self) -> None:
        """Remove all cards and show placeholder."""
        self._clear_cards()
        self._placeholder.show()

    def _clear_cards(self) -> None:
        """Remove all card widgets from the layout (keep stretch and placeholder)."""
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            widget = item.widget()
            if widget and widget is not self._placeholder:
                widget.deleteLater()
            elif widget is self._placeholder:
                # Re-insert placeholder at 0
                self._card_layout.insertWidget(0, self._placeholder)
                break

    def _toggle_cards(self) -> None:
        """Toggle visibility of the card scroll area."""
        self._cards_visible = not self._cards_visible
        self._scroll.setVisible(self._cards_visible)
        self._toggle_btn.setText("Hide" if self._cards_visible else "Show")
