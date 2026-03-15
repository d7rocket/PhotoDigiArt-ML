"""Horizontal strip of proposal thumbnails for non-linear discovery navigation.

Displays a scrollable row of thumbnail cards representing past discovery
proposals. Clicking a card emits a signal to restore that proposal's parameters.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class _ThumbnailCard(QtWidgets.QFrame):
    """Single thumbnail card in the history strip."""

    clicked = QtCore.Signal(int)  # index

    def __init__(self, index: int, thumbnail: QtGui.QPixmap | None = None, parent=None):
        super().__init__(parent)
        self._index = index
        self._active = False
        self.setFixedSize(80, 60)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self._label = QtWidgets.QLabel()
        self._label.setAlignment(QtCore.Qt.AlignCenter)
        self._label.setFixedSize(76, 56)
        if thumbnail and not thumbnail.isNull():
            self._label.setPixmap(
                thumbnail.scaled(76, 56, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            )
        else:
            self._label.setText(f"#{index + 1}")
            self._label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self._label)

        self._update_style()

    def set_active(self, active: bool) -> None:
        """Set whether this card is the currently active proposal."""
        self._active = active
        self._update_style()

    def _update_style(self):
        border_color = "#0078FF" if self._active else "#333333"
        self.setStyleSheet(
            f"_ThumbnailCard {{ background: #1E1E1E; border: 2px solid {border_color}; border-radius: 3px; }}"
        )

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)
        super().mousePressEvent(event)


class HistoryStripWidget(QtWidgets.QWidget):
    """Horizontal scrollable strip of proposal thumbnail cards.

    Signals:
        proposal_selected(int): Emitted when a thumbnail card is clicked,
            carrying the proposal index.
    """

    proposal_selected = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("history-strip")
        self.setFixedHeight(80)

        self._cards: list[_ThumbnailCard] = []
        self._active_index: int = -1

        # Main layout
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll area
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(80)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #1E1E1E; border: none; }"
            "QScrollBar:horizontal { height: 8px; background: #1E1E1E; }"
            "QScrollBar::handle:horizontal { background: #444; border-radius: 4px; min-width: 20px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )

        # Container widget for cards
        self._container = QtWidgets.QWidget()
        self._container_layout = QtWidgets.QHBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch(1)

        self._scroll.setWidget(self._container)
        outer_layout.addWidget(self._scroll)

        self.setStyleSheet("HistoryStripWidget { background: #1E1E1E; }")

    def add_proposal(self, thumbnail: QtGui.QPixmap | None = None) -> None:
        """Add a new proposal thumbnail card to the strip.

        Args:
            thumbnail: Optional QPixmap snapshot of the viewport.
        """
        index = len(self._cards)
        card = _ThumbnailCard(index, thumbnail, self._container)
        card.clicked.connect(self._on_card_clicked)

        # Insert before the stretch
        self._container_layout.insertWidget(self._container_layout.count() - 1, card)
        self._cards.append(card)

        # Auto-select the newest card
        self.set_active(index)

        # Auto-scroll to newest
        QtCore.QTimer.singleShot(50, self._scroll_to_end)

    def set_active(self, index: int) -> None:
        """Set the active (highlighted) proposal card.

        Args:
            index: Index of the card to highlight.
        """
        if 0 <= index < len(self._cards):
            # Deactivate previous
            if 0 <= self._active_index < len(self._cards):
                self._cards[self._active_index].set_active(False)
            self._active_index = index
            self._cards[index].set_active(True)

    def clear(self) -> None:
        """Remove all thumbnail cards."""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self._active_index = -1

    def _on_card_clicked(self, index: int) -> None:
        """Handle card click: set active and emit signal."""
        self.set_active(index)
        self.proposal_selected.emit(index)

    def _scroll_to_end(self) -> None:
        """Scroll to show the latest card."""
        scrollbar = self._scroll.horizontalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
