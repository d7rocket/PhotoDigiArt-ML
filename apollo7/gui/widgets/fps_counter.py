"""FPS counter overlay widget for the 3D viewport.

Displays a semi-transparent FPS readout in the top-right corner,
updated every 0.5 seconds by averaging frame intervals.
"""

from __future__ import annotations

import time

from PySide6 import QtCore, QtWidgets


class FPSCounter(QtWidgets.QLabel):
    """Semi-transparent FPS overlay positioned in the viewport corner.

    Call tick() each frame. Display updates every 0.5 seconds using
    averaged frame times for stable readout.
    """

    _UPDATE_INTERVAL = 0.5  # seconds between display updates

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fps-counter")
        self.setText("-- FPS")
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.setStyleSheet(
            "background-color: rgba(0, 0, 0, 150);"
            "color: #ffffff;"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 11px;"
            "padding: 3px 6px;"
            "border-radius: 3px;"
        )
        self.setFixedWidth(70)
        self.setFixedHeight(22)

        self._frame_count = 0
        self._last_update_time = time.perf_counter()
        self._last_tick_time = time.perf_counter()

    def tick(self):
        """Called each frame to accumulate timing data.

        Updates the displayed FPS every _UPDATE_INTERVAL seconds.
        """
        now = time.perf_counter()
        self._frame_count += 1

        elapsed = now - self._last_update_time
        if elapsed >= self._UPDATE_INTERVAL:
            fps = self._frame_count / elapsed
            self.update_fps(fps)
            self._frame_count = 0
            self._last_update_time = now

        self._last_tick_time = now

    def update_fps(self, fps: float):
        """Set the displayed FPS value."""
        self.setText(f"{fps:.0f} FPS")
