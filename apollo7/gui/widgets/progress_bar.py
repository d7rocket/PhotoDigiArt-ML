"""Extraction progress bar widget.

Shows processing status during batch operations. Only visible
while processing is active.
"""

from PySide6 import QtCore, QtWidgets


class ExtractionProgressBar(QtWidgets.QWidget):
    """Progress bar with processing label, visible only during operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.setVisible(False)

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self._label = QtWidgets.QLabel("")
        self._label.setStyleSheet("font-size: 12px; color: #e0e0e0;")
        layout.addWidget(self._label)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(14)
        layout.addWidget(self._bar, stretch=1)

    def start(self, total: int):
        """Begin progress tracking for `total` items."""
        self._bar.setMaximum(total)
        self._bar.setValue(0)
        self._label.setText(f"Processing 0/{total} photos...")
        self.setVisible(True)

    def update(self, current: int, total: int):
        """Update progress to current/total."""
        self._bar.setMaximum(total)
        self._bar.setValue(current)
        self._label.setText(f"Processing {current}/{total} photos...")

    def finish(self):
        """Mark processing complete and hide after a brief delay."""
        self._label.setText("Done!")
        self._bar.setValue(self._bar.maximum())
        QtCore.QTimer.singleShot(1500, self.hide)

    def hide(self):
        """Hide the progress bar."""
        self.setVisible(False)
