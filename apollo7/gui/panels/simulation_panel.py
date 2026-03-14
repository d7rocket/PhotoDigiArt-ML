"""Simulation controls panel with collapsible sections for force/speed/turbulence sliders.

Provides all user-facing controls for the particle simulation engine.
Organized in collapsible QGroupBox sections with per-section reset buttons.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import (
    SIM_ATTRACTION_DEFAULT,
    SIM_ATTRACTION_RANGE,
    SIM_GRAVITY_Y_DEFAULT,
    SIM_GRAVITY_Y_RANGE,
    SIM_NOISE_AMP_DEFAULT,
    SIM_NOISE_AMP_RANGE,
    SIM_NOISE_FREQ_DEFAULT,
    SIM_NOISE_FREQ_RANGE,
    SIM_NOISE_OCTAVES_DEFAULT,
    SIM_NOISE_OCTAVES_RANGE,
    SIM_PRESSURE_DEFAULT,
    SIM_PRESSURE_RANGE,
    SIM_REPULSION_DEFAULT,
    SIM_REPULSION_RADIUS_DEFAULT,
    SIM_REPULSION_RADIUS_RANGE,
    SIM_REPULSION_RANGE,
    SIM_SPEED_DEFAULT,
    SIM_SPEED_RANGE,
    SIM_SURFACE_TENSION_DEFAULT,
    SIM_SURFACE_TENSION_RANGE,
    SIM_TURBULENCE_DEFAULT,
    SIM_TURBULENCE_RANGE,
    SIM_VISCOSITY_DEFAULT,
    SIM_VISCOSITY_RANGE,
    SIM_WIND_DEFAULT,
    SIM_WIND_RANGE,
)


# Slider spec: (param_name, label, min, max, default, format_str, is_integer)
_CONTROL_SLIDERS = [
    ("speed", "Speed", *SIM_SPEED_RANGE, SIM_SPEED_DEFAULT, "{:.1f}", False),
    ("turbulence_scale", "Turbulence", *SIM_TURBULENCE_RANGE, SIM_TURBULENCE_DEFAULT, "{:.1f}", False),
]

_FLOW_SLIDERS = [
    ("noise_frequency", "Noise Frequency", *SIM_NOISE_FREQ_RANGE, SIM_NOISE_FREQ_DEFAULT, "{:.2f}", False),
    ("noise_amplitude", "Noise Amplitude", *SIM_NOISE_AMP_RANGE, SIM_NOISE_AMP_DEFAULT, "{:.2f}", False),
    ("noise_octaves", "Noise Octaves", *SIM_NOISE_OCTAVES_RANGE, SIM_NOISE_OCTAVES_DEFAULT, "{:d}", True),
]

_FORCES_SLIDERS = [
    ("attraction_strength", "Attraction", *SIM_ATTRACTION_RANGE, SIM_ATTRACTION_DEFAULT, "{:.2f}", False),
    ("repulsion_strength", "Repulsion", *SIM_REPULSION_RANGE, SIM_REPULSION_DEFAULT, "{:.2f}", False),
    ("repulsion_radius", "Repulsion Radius", *SIM_REPULSION_RADIUS_RANGE, SIM_REPULSION_RADIUS_DEFAULT, "{:.3f}", False),
    ("gravity_y", "Gravity Y", *SIM_GRAVITY_Y_RANGE, SIM_GRAVITY_Y_DEFAULT, "{:.2f}", False),
    ("wind_x", "Wind X", *SIM_WIND_RANGE, SIM_WIND_DEFAULT, "{:.2f}", False),
    ("wind_z", "Wind Z", *SIM_WIND_RANGE, SIM_WIND_DEFAULT, "{:.2f}", False),
]

_FLUID_SLIDERS = [
    ("viscosity", "Viscosity", *SIM_VISCOSITY_RANGE, SIM_VISCOSITY_DEFAULT, "{:.3f}", False),
    ("pressure_strength", "Pressure", *SIM_PRESSURE_RANGE, SIM_PRESSURE_DEFAULT, "{:.2f}", False),
    ("surface_tension", "Surface Tension", *SIM_SURFACE_TENSION_RANGE, SIM_SURFACE_TENSION_DEFAULT, "{:.4f}", False),
]

# Section name -> slider specs
_SECTIONS = {
    "control": _CONTROL_SLIDERS,
    "flow": _FLOW_SLIDERS,
    "forces": _FORCES_SLIDERS,
    "fluid": _FLUID_SLIDERS,
}


class SimulationPanel(QtWidgets.QWidget):
    """Simulation controls panel with collapsible sections."""

    # Signals
    simulate_clicked = QtCore.Signal()
    pause_toggled = QtCore.Signal(bool)  # True = paused
    performance_mode_changed = QtCore.Signal(bool)
    param_changed = QtCore.Signal(str, float)  # (param_name, new_value)
    section_reset = QtCore.Signal(str)  # section name
    reset_all = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("simulation-panel")

        # Slider references: {param_name: (slider, label_widget, spec)}
        self._sliders: dict[str, tuple[QtWidgets.QSlider, QtWidgets.QLabel, tuple]] = {}

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Simulation")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # -- Simulation Control section (always visible) --
        ctrl_group = QtWidgets.QGroupBox("Simulation Control")
        ctrl_group.setObjectName("sim-control-group")
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_group)

        self.btn_simulate = QtWidgets.QPushButton("Simulate")
        self.btn_simulate.setObjectName("btn-simulate")
        self.btn_simulate.setMinimumHeight(36)
        ctrl_layout.addWidget(self.btn_simulate)

        self.btn_pause = QtWidgets.QPushButton("Pause")
        self.btn_pause.setObjectName("btn-pause")
        self.btn_pause.setEnabled(False)
        ctrl_layout.addWidget(self.btn_pause)

        self.chk_performance = QtWidgets.QCheckBox("Performance Mode")
        self.chk_performance.setToolTip("Reduce sim quality for smooth interaction")
        ctrl_layout.addWidget(self.chk_performance)

        # Control sliders (speed, turbulence)
        for spec in _CONTROL_SLIDERS:
            self._add_slider(ctrl_layout, spec)

        self.btn_reset_control = QtWidgets.QPushButton("Reset Simulation")
        self.btn_reset_control.setObjectName("btn-reset-section")
        ctrl_layout.addWidget(self.btn_reset_control)

        layout.addWidget(ctrl_group)

        # -- Flow Field section (collapsible) --
        flow_group = self._make_collapsible_group("Flow Field")
        flow_layout = flow_group.layout()
        for spec in _FLOW_SLIDERS:
            self._add_slider(flow_layout, spec)
        self.btn_reset_flow = QtWidgets.QPushButton("Reset Flow")
        self.btn_reset_flow.setObjectName("btn-reset-section")
        flow_layout.addWidget(self.btn_reset_flow)
        layout.addWidget(flow_group)

        # -- Forces section (collapsible) --
        forces_group = self._make_collapsible_group("Forces")
        forces_layout = forces_group.layout()
        for spec in _FORCES_SLIDERS:
            self._add_slider(forces_layout, spec)
        self.btn_reset_forces = QtWidgets.QPushButton("Reset Forces")
        self.btn_reset_forces.setObjectName("btn-reset-section")
        forces_layout.addWidget(self.btn_reset_forces)
        layout.addWidget(forces_group)

        # -- Fluid (SPH) section (collapsible) --
        fluid_group = self._make_collapsible_group("Fluid (SPH)")
        fluid_layout = fluid_group.layout()
        for spec in _FLUID_SLIDERS:
            self._add_slider(fluid_layout, spec)
        self.btn_reset_fluid = QtWidgets.QPushButton("Reset Fluid")
        self.btn_reset_fluid.setObjectName("btn-reset-section")
        fluid_layout.addWidget(self.btn_reset_fluid)
        layout.addWidget(fluid_group)

        # -- Global reset --
        self.btn_reset_all = QtWidgets.QPushButton("Reset All")
        self.btn_reset_all.setObjectName("btn-reset-all")
        layout.addWidget(self.btn_reset_all)

        layout.addStretch(1)

        scroll.setWidget(container)

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _make_collapsible_group(self, title: str) -> QtWidgets.QGroupBox:
        """Create a collapsible QGroupBox."""
        group = QtWidgets.QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(True)
        group.toggled.connect(lambda checked, g=group: self._toggle_group(g, checked))
        vbox = QtWidgets.QVBoxLayout(group)
        return group

    def _toggle_group(self, group: QtWidgets.QGroupBox, checked: bool):
        """Show/hide group contents when toggled."""
        for i in range(group.layout().count()):
            item = group.layout().itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(checked)

    def _add_slider(self, layout, spec: tuple):
        """Add a labeled slider for a parameter.

        spec: (param_name, label, min_val, max_val, default, fmt, is_integer)
        """
        param_name, label_text, min_val, max_val, default, fmt, is_integer = spec

        lbl = QtWidgets.QLabel(label_text)
        layout.addWidget(lbl)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        # Map default to tick
        if max_val > min_val:
            tick = int((default - min_val) / (max_val - min_val) * 100)
        else:
            tick = 0
        slider.setValue(tick)
        slider.setProperty("min_val", float(min_val))
        slider.setProperty("max_val", float(max_val))
        slider.setProperty("param_name", param_name)
        slider.setProperty("is_integer", is_integer)
        layout.addWidget(slider)

        if is_integer:
            val_label = QtWidgets.QLabel(fmt.format(int(default)))
        else:
            val_label = QtWidgets.QLabel(fmt.format(default))
        val_label.setAlignment(QtCore.Qt.AlignRight)
        val_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(val_label)

        self._sliders[param_name] = (slider, val_label, spec)

    def _slider_value(self, slider: QtWidgets.QSlider) -> float:
        """Convert slider tick to float value."""
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")
        t = slider.value() / 100.0
        val = min_val + t * (max_val - min_val)
        if slider.property("is_integer"):
            val = round(val)
        return val

    def _connect_signals(self):
        """Wire internal signals."""
        self.btn_simulate.clicked.connect(self.simulate_clicked)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        self.chk_performance.toggled.connect(self.performance_mode_changed)

        # All sliders emit param_changed
        for param_name, (slider, val_label, spec) in self._sliders.items():
            slider.valueChanged.connect(
                lambda _val, s=slider, vl=val_label, sp=spec: self._on_slider_changed(s, vl, sp)
            )

        # Section resets
        self.btn_reset_control.clicked.connect(lambda: self._reset_section("control"))
        self.btn_reset_flow.clicked.connect(lambda: self._reset_section("flow"))
        self.btn_reset_forces.clicked.connect(lambda: self._reset_section("forces"))
        self.btn_reset_fluid.clicked.connect(lambda: self._reset_section("fluid"))
        self.btn_reset_all.clicked.connect(self._on_reset_all)

    def _on_slider_changed(self, slider, val_label, spec):
        """Handle slider value change."""
        param_name, _label, _min, _max, _default, fmt, is_integer = spec
        val = self._slider_value(slider)
        if is_integer:
            val_label.setText(fmt.format(int(val)))
        else:
            val_label.setText(fmt.format(val))
        self.param_changed.emit(param_name, float(val))

    def _on_pause_clicked(self):
        """Toggle pause text and emit signal."""
        is_paused = self.btn_pause.text() == "Pause"
        if is_paused:
            self.btn_pause.setText("Resume")
        else:
            self.btn_pause.setText("Pause")
        self.pause_toggled.emit(is_paused)

    def _reset_section(self, section_name: str):
        """Reset all sliders in a section to defaults."""
        specs = _SECTIONS.get(section_name, [])
        for spec in specs:
            param_name = spec[0]
            default = spec[4]
            if param_name in self._sliders:
                slider, val_label, _ = self._sliders[param_name]
                min_val = slider.property("min_val")
                max_val = slider.property("max_val")
                tick = int((default - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
                slider.setValue(tick)
        self.section_reset.emit(section_name)

    def _on_reset_all(self):
        """Reset all sections."""
        for section_name in _SECTIONS:
            specs = _SECTIONS[section_name]
            for spec in specs:
                param_name = spec[0]
                default = spec[4]
                if param_name in self._sliders:
                    slider, val_label, _ = self._sliders[param_name]
                    min_val = slider.property("min_val")
                    max_val = slider.property("max_val")
                    tick = int((default - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
                    slider.setValue(tick)
        self.reset_all.emit()

    def set_simulate_enabled(self, enabled: bool):
        """Enable/disable the Simulate button."""
        self.btn_simulate.setEnabled(enabled)

    def set_simulation_running(self, running: bool):
        """Update UI state when simulation starts/stops."""
        self.btn_pause.setEnabled(running)
        if running:
            self.btn_simulate.setText("Restart")
            self.btn_pause.setText("Pause")
        else:
            self.btn_simulate.setText("Simulate")
            self.btn_pause.setText("Pause")
            self.btn_pause.setEnabled(False)

    def get_param_value(self, param_name: str) -> float | None:
        """Get current value of a parameter slider."""
        if param_name not in self._sliders:
            return None
        slider, _, _ = self._sliders[param_name]
        return self._slider_value(slider)

    def set_param_value(self, param_name: str, value: float):
        """Programmatically set a slider value (without emitting signals)."""
        if param_name not in self._sliders:
            return
        slider, val_label, spec = self._sliders[param_name]
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")
        tick = int((value - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
        slider.blockSignals(True)
        slider.setValue(tick)
        slider.blockSignals(False)
        _, _, _, _, _, fmt, is_integer = spec
        if is_integer:
            val_label.setText(fmt.format(int(value)))
        else:
            val_label.setText(fmt.format(value))
