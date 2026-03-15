"""Discovery mode panel with dimensional sliders and proposal controls.

Provides the UI for discovery mode: abstract dimensional sliders (Energy,
Density, Flow, Structure), propose/apply buttons, and a history strip
for browsing past proposals.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from apollo7.gui.widgets.history_strip import HistoryStripWidget


# Slider definitions: (dimension_name, left_label, right_label)
_DIMENSION_SLIDERS = [
    ("energy", "calm", "chaotic"),
    ("density", "sparse", "dense"),
    ("flow", "rigid", "fluid"),
    ("structure", "organic", "geometric"),
]


class DiscoveryPanel(QtWidgets.QWidget):
    """Discovery mode panel with dimensional sliders, propose/apply, and history strip.

    Signals:
        proposal_requested: Emitted when user clicks Propose.
        proposal_applied(dict): Carries param dict to apply to simulation.
        dimension_changed(str, float): When any dimensional slider moves.
        discovery_toggled(bool): On/off state change.
    """

    proposal_requested = QtCore.Signal()
    proposal_applied = QtCore.Signal(dict)
    dimension_changed = QtCore.Signal(str, float)
    discovery_toggled = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("discovery-panel")

        # Slider references: {dimension_name: (slider, value_label)}
        self._sliders: dict[str, tuple[QtWidgets.QSlider, QtWidgets.QLabel]] = {}
        self._enabled = False

        self._build_ui()
        self._connect_signals()
        self._set_controls_enabled(False)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # -- Header with toggle --
        header_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Discovery Mode")
        title.setObjectName("panel-title")
        header_row.addWidget(title)
        header_row.addStretch(1)

        self.btn_toggle = QtWidgets.QPushButton("OFF")
        self.btn_toggle.setObjectName("btn-discovery-toggle")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setFixedWidth(50)
        self.btn_toggle.setStyleSheet(
            "QPushButton { background: #333; color: #888; border: 1px solid #555; border-radius: 3px; padding: 4px; }"
            "QPushButton:checked { background: #0078FF; color: white; border: 1px solid #0078FF; }"
        )
        header_row.addWidget(self.btn_toggle)
        layout.addLayout(header_row)

        # -- Dimensions section --
        self._dimensions_group = QtWidgets.QGroupBox("Dimensions")
        self._dimensions_group.setCheckable(False)
        dim_layout = QtWidgets.QVBoxLayout(self._dimensions_group)
        dim_layout.setSpacing(4)

        for dim_name, left_label, right_label in _DIMENSION_SLIDERS:
            self._add_dimension_slider(dim_layout, dim_name, left_label, right_label)

        layout.addWidget(self._dimensions_group)

        # -- Buttons --
        btn_row = QtWidgets.QHBoxLayout()

        self.btn_propose = QtWidgets.QPushButton("Propose")
        self.btn_propose.setObjectName("btn-propose")
        self.btn_propose.setMinimumHeight(32)
        self.btn_propose.setStyleSheet(
            "QPushButton { background: #0078FF; color: white; border: none; border-radius: 4px; font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background: #1A8AFF; }"
            "QPushButton:disabled { background: #333; color: #666; }"
        )
        btn_row.addWidget(self.btn_propose)

        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_apply.setObjectName("btn-apply")
        self.btn_apply.setMinimumHeight(32)
        self.btn_apply.setStyleSheet(
            "QPushButton { background: #444444; color: white; border: none; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background: #555555; }"
            "QPushButton:disabled { background: #333; color: #666; }"
        )
        btn_row.addWidget(self.btn_apply)

        layout.addLayout(btn_row)

        # -- History strip --
        self.history_strip = HistoryStripWidget()
        layout.addWidget(self.history_strip)

        layout.addStretch(1)

    def _add_dimension_slider(
        self,
        layout: QtWidgets.QVBoxLayout,
        dim_name: str,
        left_label: str,
        right_label: str,
    ):
        """Add a dimensional slider with left/right semantic labels."""
        # Capitalize dimension name as header
        name_label = QtWidgets.QLabel(dim_name.capitalize())
        name_label.setStyleSheet("color: #CCC; font-size: 11px; font-weight: bold;")
        layout.addWidget(name_label)

        slider_row = QtWidgets.QHBoxLayout()

        lbl_left = QtWidgets.QLabel(left_label)
        lbl_left.setStyleSheet("color: #888888; font-size: 10px;")
        lbl_left.setFixedWidth(60)
        slider_row.addWidget(lbl_left)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(50)
        slider.setProperty("dim_name", dim_name)
        slider_row.addWidget(slider)

        lbl_right = QtWidgets.QLabel(right_label)
        lbl_right.setStyleSheet("color: #888888; font-size: 10px;")
        lbl_right.setFixedWidth(60)
        lbl_right.setAlignment(QtCore.Qt.AlignRight)
        slider_row.addWidget(lbl_right)

        val_label = QtWidgets.QLabel("0.50")
        val_label.setStyleSheet("color: #888; font-size: 10px;")
        val_label.setFixedWidth(30)
        val_label.setAlignment(QtCore.Qt.AlignRight)
        slider_row.addWidget(val_label)

        layout.addLayout(slider_row)

        self._sliders[dim_name] = (slider, val_label)

    def _connect_signals(self):
        """Wire internal signals."""
        self.btn_toggle.toggled.connect(self._on_toggle)
        self.btn_propose.clicked.connect(self.proposal_requested)
        self.btn_apply.clicked.connect(self._on_apply)

        for dim_name, (slider, val_label) in self._sliders.items():
            slider.valueChanged.connect(
                lambda _val, dn=dim_name, s=slider, vl=val_label: self._on_slider_changed(dn, s, vl)
            )

    def _on_toggle(self, checked: bool):
        """Handle discovery mode toggle."""
        self._enabled = checked
        self.btn_toggle.setText("ON" if checked else "OFF")
        self._set_controls_enabled(checked)
        self.discovery_toggled.emit(checked)

    def _on_slider_changed(self, dim_name: str, slider: QtWidgets.QSlider, val_label: QtWidgets.QLabel):
        """Handle dimensional slider change."""
        value = slider.value() / 100.0
        val_label.setText(f"{value:.2f}")
        self.dimension_changed.emit(dim_name, value)

    def _on_apply(self):
        """Emit proposal_applied with empty dict (controller fills in actual params)."""
        self.proposal_applied.emit({})

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable all controls based on discovery mode state."""
        self._dimensions_group.setEnabled(enabled)
        self.btn_propose.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)
        self.history_strip.setEnabled(enabled)
        # Dim the panel visually when disabled
        opacity = "1.0" if enabled else "0.5"
        self._dimensions_group.setStyleSheet(f"QGroupBox {{ opacity: {opacity}; }}")

    def get_dimension_values(self) -> dict[str, float]:
        """Get current values of all dimensional sliders.

        Returns:
            Dict mapping dimension_name -> value in [0, 1].
        """
        return {
            dim_name: slider.value() / 100.0
            for dim_name, (slider, _) in self._sliders.items()
        }

    def set_dimension_values(self, values: dict[str, float]) -> None:
        """Programmatically set dimensional slider values.

        Args:
            values: Dict mapping dimension_name -> value in [0, 1].
        """
        for dim_name, value in values.items():
            if dim_name in self._sliders:
                slider, val_label = self._sliders[dim_name]
                slider.blockSignals(True)
                slider.setValue(int(value * 100))
                slider.blockSignals(False)
                val_label.setText(f"{value:.2f}")
