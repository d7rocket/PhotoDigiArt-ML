"""Controls panel: extraction settings and layout mode toggle.

Placeholder for Phase 1. Contains an Extract Features button and
layout mode radio buttons (Depth-projected / Feature-clustered).
Will be wired to extraction in Plans 03/04.
"""

from PySide6 import QtWidgets


class ControlsPanel(QtWidgets.QWidget):
    """Controls panel with extraction and layout mode groups."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QtWidgets.QLabel("Controls")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # --- Extraction group ---
        extraction_group = QtWidgets.QGroupBox("Extraction")
        ext_layout = QtWidgets.QVBoxLayout(extraction_group)

        self.btn_extract = QtWidgets.QPushButton("Extract Features")
        self.btn_extract.setEnabled(False)
        self.btn_extract.setToolTip("Run feature extraction on loaded photos")
        ext_layout.addWidget(self.btn_extract)

        layout.addWidget(extraction_group)

        # --- Layout Mode group ---
        mode_group = QtWidgets.QGroupBox("Layout Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)

        self.radio_depth = QtWidgets.QRadioButton("Depth-projected")
        self.radio_depth.setChecked(True)
        self.radio_depth.setToolTip(
            "Depth map drives Z-axis displacement, creating a relief sculpture"
        )
        mode_layout.addWidget(self.radio_depth)

        self.radio_clustered = QtWidgets.QRadioButton("Feature-clustered")
        self.radio_clustered.setToolTip(
            "Points grouped by feature similarity in abstract 3D space"
        )
        mode_layout.addWidget(self.radio_clustered)

        layout.addWidget(mode_group)

        # Spacer to push content to top
        layout.addStretch(1)
