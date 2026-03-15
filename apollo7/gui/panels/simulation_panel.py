"""Simulation controls panel with PBF-oriented sliders and cohesion crossfade.

Provides all user-facing controls for the PBF particle simulation engine.
Essential sliders (Cohesion, Home Strength, Flow Intensity, Breathing Rate)
are always visible. Advanced sliders are in a collapsible section.

Cohesion slider (solver_iterations) uses crossfade interpolation over ~0.5s
to smooth transitions between iteration counts.
"""

from __future__ import annotations

import time as _time

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import (
    SIM_BREATHING_DEPTH_DEFAULT,
    SIM_BREATHING_DEPTH_RANGE,
    SIM_BREATHING_RATE_DEFAULT,
    SIM_BREATHING_RATE_RANGE,
    SIM_COHESION_DEFAULT,
    SIM_COHESION_RANGE,
    SIM_DAMPING_DEFAULT,
    SIM_DAMPING_RANGE,
    SIM_FLOW_INTENSITY_DEFAULT,
    SIM_FLOW_INTENSITY_RANGE,
    SIM_FLOW_SCALE_DEFAULT,
    SIM_FLOW_SCALE_RANGE,
    SIM_HOME_STRENGTH_DEFAULT,
    SIM_HOME_STRENGTH_RANGE,
    SIM_SMOOTHING_DEFAULT,
    SIM_SMOOTHING_RANGE,
    SIM_SWIRL_DEFAULT,
    SIM_SWIRL_RANGE,
)

# Crossfade duration in seconds for cohesion transitions
_CROSSFADE_DURATION = 0.5

# Slider spec: (param_name, label, min, max, default, format_str, is_integer)
_ESSENTIAL_SLIDERS = [
    ("solver_iterations", "Cohesion", *SIM_COHESION_RANGE, SIM_COHESION_DEFAULT, "{:d}", True),
    ("home_strength", "Home Strength", *SIM_HOME_STRENGTH_RANGE, SIM_HOME_STRENGTH_DEFAULT, "{:.1f}", False),
    ("noise_amplitude", "Flow Intensity", *SIM_FLOW_INTENSITY_RANGE, SIM_FLOW_INTENSITY_DEFAULT, "{:.2f}", False),
    ("breathing_rate", "Breathing Rate", *SIM_BREATHING_RATE_RANGE, SIM_BREATHING_RATE_DEFAULT, "{:.2f}", False),
]

_ADVANCED_SLIDERS = [
    ("noise_frequency", "Flow Scale", *SIM_FLOW_SCALE_RANGE, SIM_FLOW_SCALE_DEFAULT, "{:.2f}", False),
    ("vorticity_epsilon", "Swirl", *SIM_SWIRL_RANGE, SIM_SWIRL_DEFAULT, "{:.3f}", False),
    ("xsph_c", "Smoothing", *SIM_SMOOTHING_RANGE, SIM_SMOOTHING_DEFAULT, "{:.3f}", False),
    ("damping", "Damping", *SIM_DAMPING_RANGE, SIM_DAMPING_DEFAULT, "{:.3f}", False),
    ("breathing_amplitude", "Breathing Depth", *SIM_BREATHING_DEPTH_RANGE, SIM_BREATHING_DEPTH_DEFAULT, "{:.2f}", False),
]

# Section name -> slider specs (used for reset)
_SECTIONS = {
    "essential": _ESSENTIAL_SLIDERS,
    "advanced": _ADVANCED_SLIDERS,
}


class SimulationPanel(QtWidgets.QWidget):
    """Simulation controls panel with PBF-specific sliders and crossfade."""

    # Signals
    simulate_clicked = QtCore.Signal()
    pause_toggled = QtCore.Signal(bool)  # True = paused
    performance_mode_changed = QtCore.Signal(bool)
    param_changed = QtCore.Signal(str, float)  # (param_name, new_value)
    section_reset = QtCore.Signal(str)  # section name
    reset_all = QtCore.Signal()
    reset_camera_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("simulation-panel")

        # Slider references: {param_name: (slider, label_widget, spec)}
        self._sliders: dict[str, tuple[QtWidgets.QSlider, QtWidgets.QLabel, tuple]] = {}

        # Crossfade state for cohesion (solver_iterations)
        self._crossfade_start_home: float | None = None
        self._crossfade_target_home: float | None = None
        self._crossfade_start_time: float | None = None
        self._crossfade_target_iterations: int | None = None

        self._build_ui()
        self._connect_signals()

    def eventFilter(self, obj, event):
        """Block wheel events on sliders so scrolling the panel works."""
        if isinstance(obj, QtWidgets.QSlider) and event.type() == QtCore.QEvent.Wheel:
            event.ignore()
            return True
        return super().eventFilter(obj, event)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
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

        self.btn_reset_camera = QtWidgets.QPushButton("Reset Camera")
        self.btn_reset_camera.setObjectName("btn-reset-camera")
        ctrl_layout.addWidget(self.btn_reset_camera)

        layout.addWidget(ctrl_group)

        # -- Essential PBF Controls (always visible) --
        essential_group = QtWidgets.QGroupBox("PBF Controls")
        essential_layout = QtWidgets.QVBoxLayout(essential_group)

        # Add cohesion label spectrum hint
        cohesion_hint = QtWidgets.QLabel("Ethereal (1) \u2014\u2014\u2014 Liquid (6)")
        cohesion_hint.setAlignment(QtCore.Qt.AlignCenter)
        cohesion_hint.setStyleSheet("color: #888; font-size: 9px; font-style: italic;")

        for i, spec in enumerate(_ESSENTIAL_SLIDERS):
            self._add_slider(essential_layout, spec)
            # Insert cohesion hint after the first slider (Cohesion)
            if i == 0:
                essential_layout.addWidget(cohesion_hint)

        self.btn_reset_essential = QtWidgets.QPushButton("Reset Controls")
        self.btn_reset_essential.setObjectName("btn-reset-section")
        essential_layout.addWidget(self.btn_reset_essential)

        layout.addWidget(essential_group)

        # -- Advanced PBF Controls (collapsible) --
        self.advanced_group = QtWidgets.QGroupBox("Advanced")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QtWidgets.QVBoxLayout(self.advanced_group)

        self._advanced_widget = QtWidgets.QWidget()
        adv_inner_layout = QtWidgets.QVBoxLayout(self._advanced_widget)
        adv_inner_layout.setContentsMargins(0, 0, 0, 0)

        for spec in _ADVANCED_SLIDERS:
            self._add_slider(adv_inner_layout, spec)

        self.btn_reset_advanced = QtWidgets.QPushButton("Reset Advanced")
        self.btn_reset_advanced.setObjectName("btn-reset-section")
        adv_inner_layout.addWidget(self.btn_reset_advanced)

        advanced_layout.addWidget(self._advanced_widget)
        self._advanced_widget.setVisible(False)

        layout.addWidget(self.advanced_group)

        # -- Global reset --
        self.btn_reset_all = QtWidgets.QPushButton("Reset All")
        self.btn_reset_all.setObjectName("btn-reset-all")
        layout.addWidget(self.btn_reset_all)

        layout.addStretch(1)

    def _add_slider(self, layout, spec: tuple):
        """Add a labeled slider for a parameter.

        spec: (param_name, label, min_val, max_val, default, fmt, is_integer)
        """
        param_name, label_text, min_val, max_val, default, fmt, is_integer = spec

        lbl = QtWidgets.QLabel(label_text)
        layout.addWidget(lbl)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.installEventFilter(self)
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
        self.btn_reset_camera.clicked.connect(self.reset_camera_clicked)

        # All sliders emit param_changed
        for param_name, (slider, val_label, spec) in self._sliders.items():
            slider.valueChanged.connect(
                lambda _val, s=slider, vl=val_label, sp=spec: self._on_slider_changed(s, vl, sp)
            )

        # Advanced section collapse/expand
        self.advanced_group.toggled.connect(self._on_advanced_toggled)

        # Section resets
        self.btn_reset_essential.clicked.connect(lambda: self._reset_section("essential"))
        self.btn_reset_advanced.clicked.connect(lambda: self._reset_section("advanced"))
        self.btn_reset_all.clicked.connect(self._on_reset_all)

    def _on_advanced_toggled(self, checked: bool):
        """Show/hide advanced controls."""
        self._advanced_widget.setVisible(checked)

    def _on_slider_changed(self, slider, val_label, spec):
        """Handle slider value change."""
        param_name, _label, _min, _max, _default, fmt, is_integer = spec
        val = self._slider_value(slider)
        if is_integer:
            val_label.setText(fmt.format(int(val)))
        else:
            val_label.setText(fmt.format(val))

        # For cohesion (solver_iterations), initiate crossfade
        if param_name == "solver_iterations":
            self._start_cohesion_crossfade(int(val))
        else:
            self.param_changed.emit(param_name, float(val))

    def _start_cohesion_crossfade(self, target_iterations: int):
        """Start crossfade for cohesion slider change.

        Snaps solver_iterations immediately (it's discrete) but crossfades
        home_strength slightly to smooth the visual transition.
        """
        # Emit the solver_iterations change immediately (discrete)
        self.param_changed.emit("solver_iterations", float(target_iterations))

        # Get current home_strength for crossfade
        if "home_strength" in self._sliders:
            slider, _, _ = self._sliders["home_strength"]
            current_home = self._slider_value(slider)
        else:
            current_home = SIM_HOME_STRENGTH_DEFAULT

        # Set crossfade state: briefly dip home_strength then restore
        # This creates a smooth visual transition when cohesion changes
        self._crossfade_target_iterations = target_iterations
        self._crossfade_start_home = current_home
        self._crossfade_target_home = current_home
        self._crossfade_start_time = _time.monotonic()

        # Briefly reduce home_strength by 20% to allow particles to shift
        dipped_home = current_home * 0.8
        self.param_changed.emit("home_strength", dipped_home)

        # Use a timer to restore home_strength after crossfade duration
        QtCore.QTimer.singleShot(
            int(_CROSSFADE_DURATION * 1000),
            lambda: self._finish_cohesion_crossfade(current_home),
        )

    def _finish_cohesion_crossfade(self, restore_home: float):
        """Restore home_strength after cohesion crossfade."""
        self.param_changed.emit("home_strength", restore_home)
        self._crossfade_start_time = None

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
