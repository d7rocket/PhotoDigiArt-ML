"""Persistent toolbar strip with Simulate/Pause, Reset Camera, and FPS counter.

Sits above the tab widget in the right sidebar. Always visible regardless
of which tab is active.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class ToolbarStrip(QtWidgets.QWidget):
    """Persistent toolbar with simulation controls and FPS display.

    Signals
    -------
    simulate_clicked
        Emitted when Simulate is clicked (initial start).
    pause_toggled(bool)
        Emitted when Pause/Resume is toggled. True = paused.
    reset_camera_clicked
        Emitted when Reset Camera is clicked.
    """

    simulate_clicked = QtCore.Signal()
    pause_toggled = QtCore.Signal(bool)
    reset_camera_clicked = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            "ToolbarStrip { background: #1a1a1a; border-bottom: 1px solid #3a3a3a; }"
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Simulate / Pause button
        self.btn_simulate = QtWidgets.QPushButton("Simulate")
        self.btn_simulate.setObjectName("btn-simulate")
        self.btn_simulate.setCheckable(True)
        self.btn_simulate.clicked.connect(self._on_simulate_clicked)
        layout.addWidget(self.btn_simulate)

        # Reset Camera button
        self.btn_reset_camera = QtWidgets.QPushButton("Reset Camera")
        self.btn_reset_camera.setObjectName("btn-reset-camera")
        self.btn_reset_camera.clicked.connect(self.reset_camera_clicked)
        layout.addWidget(self.btn_reset_camera)

        # Stretch spacer
        layout.addStretch(1)

        # FPS counter
        self.lbl_fps = QtWidgets.QLabel("0 FPS")
        self.lbl_fps.setObjectName("fps-counter")
        self.lbl_fps.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.lbl_fps)

        self._simulating = False

    def _on_simulate_clicked(self, checked: bool) -> None:
        """Handle the Simulate/Pause button click."""
        if not self._simulating:
            # First click -- start simulation
            self._simulating = True
            self.btn_simulate.setText("Pause")
            self.simulate_clicked.emit()
        else:
            # Subsequent clicks -- toggle pause
            if checked:
                self.btn_simulate.setText("Simulate")
                self.pause_toggled.emit(True)  # paused
            else:
                self.btn_simulate.setText("Pause")
                self.pause_toggled.emit(False)  # resumed

    def update_fps(self, fps: float) -> None:
        """Update the FPS counter display."""
        self.lbl_fps.setText(f"{fps:.0f} FPS")

    def set_simulating(self, active: bool) -> None:
        """Set the button state to reflect simulation status."""
        self._simulating = active
        if active:
            self.btn_simulate.setText("Pause")
            self.btn_simulate.setChecked(False)
        else:
            self.btn_simulate.setText("Simulate")
            self.btn_simulate.setChecked(False)
