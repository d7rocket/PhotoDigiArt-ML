"""Post-processing effects controls panel.

Provides toggles and sliders for bloom, depth of field, ambient
occlusion, and motion trails. Organized in collapsible QGroupBox
sections with per-section and global reset buttons.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import (
    BLOOM_STRENGTH_DEFAULT,
    BLOOM_STRENGTH_RANGE,
    DOF_APERTURE_DEFAULT,
    DOF_APERTURE_RANGE,
    DOF_FOCAL_DEFAULT,
    DOF_FOCAL_RANGE,
    SSAO_INTENSITY_DEFAULT,
    SSAO_INTENSITY_RANGE,
    SSAO_RADIUS_DEFAULT,
    SSAO_RADIUS_RANGE,
    TRAIL_LENGTH_DEFAULT,
    TRAIL_LENGTH_RANGE,
)
from apollo7.postfx.ssao_pass import SSAOPass

# Slider spec: (param_name, label, min, max, default, format_str)
_BLOOM_SLIDERS = [
    ("bloom_strength", "Strength", *BLOOM_STRENGTH_RANGE, BLOOM_STRENGTH_DEFAULT, "{:.3f}"),
]

_DOF_SLIDERS = [
    ("dof_focal_distance", "Focal Distance", *DOF_FOCAL_RANGE, DOF_FOCAL_DEFAULT, "{:.1f}"),
    ("dof_aperture", "Aperture", *DOF_APERTURE_RANGE, DOF_APERTURE_DEFAULT, "{:.1f}"),
]

_SSAO_SLIDERS = [
    ("ssao_radius", "Radius", *SSAO_RADIUS_RANGE, SSAO_RADIUS_DEFAULT, "{:.2f}"),
    ("ssao_intensity", "Intensity", *SSAO_INTENSITY_RANGE, SSAO_INTENSITY_DEFAULT, "{:.2f}"),
]

_TRAIL_SLIDERS = [
    ("trail_length", "Trail Length", *TRAIL_LENGTH_RANGE, TRAIL_LENGTH_DEFAULT, "{:.2f}"),
]

# Section name -> (slider specs, enable_default, checkbox_param_name)
_SECTIONS = {
    "bloom": (_BLOOM_SLIDERS, True, "bloom_enabled"),
    "dof": (_DOF_SLIDERS, False, "dof_enabled"),
    "ssao": (_SSAO_SLIDERS, False, "ssao_enabled"),
    "trails": (_TRAIL_SLIDERS, False, "trails_enabled"),
}


class PostFXPanel(QtWidgets.QWidget):
    """Post-processing effects controls panel with toggleable sections."""

    # Emitted when any postfx slider value changes: (param_name, value)
    postfx_param_changed = QtCore.Signal(str, float)

    # Emitted when an effect is toggled on/off: (effect_name, enabled)
    postfx_toggled = QtCore.Signal(str, bool)

    # Emitted when a section is reset: (section_name)
    postfx_section_reset = QtCore.Signal(str)

    # Emitted when all post-fx are reset
    postfx_reset_all = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("postfx-panel")

        # Slider references: {param_name: (slider, value_label, spec)}
        self._sliders: dict[str, tuple[QtWidgets.QSlider, QtWidgets.QLabel, tuple]] = {}

        # Checkbox references: {section_name: QCheckBox}
        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Post-FX")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # -- Bloom section --
        bloom_group = QtWidgets.QGroupBox("Bloom")
        bloom_layout = QtWidgets.QVBoxLayout(bloom_group)

        self.chk_bloom = QtWidgets.QCheckBox("Enable")
        self.chk_bloom.setChecked(True)
        self.chk_bloom.setObjectName("chk-bloom")
        bloom_layout.addWidget(self.chk_bloom)
        self._checkboxes["bloom"] = self.chk_bloom

        for spec in _BLOOM_SLIDERS:
            self._add_slider(bloom_layout, spec)

        self.btn_reset_bloom = QtWidgets.QPushButton("Reset Bloom")
        self.btn_reset_bloom.setObjectName("btn-reset-section")
        bloom_layout.addWidget(self.btn_reset_bloom)

        layout.addWidget(bloom_group)

        # -- Depth of Field section --
        dof_group = QtWidgets.QGroupBox("Depth of Field")
        dof_layout = QtWidgets.QVBoxLayout(dof_group)

        self.chk_dof = QtWidgets.QCheckBox("Enable")
        self.chk_dof.setChecked(False)
        self.chk_dof.setObjectName("chk-dof")
        dof_layout.addWidget(self.chk_dof)
        self._checkboxes["dof"] = self.chk_dof

        for spec in _DOF_SLIDERS:
            self._add_slider(dof_layout, spec)

        self.btn_reset_dof = QtWidgets.QPushButton("Reset DoF")
        self.btn_reset_dof.setObjectName("btn-reset-section")
        dof_layout.addWidget(self.btn_reset_dof)

        layout.addWidget(dof_group)

        # -- Ambient Occlusion section --
        ssao_group = QtWidgets.QGroupBox("Ambient Occlusion")
        ssao_layout = QtWidgets.QVBoxLayout(ssao_group)

        self.chk_ssao = QtWidgets.QCheckBox("Enable")
        self.chk_ssao.setChecked(False)
        self.chk_ssao.setObjectName("chk-ssao")
        ssao_layout.addWidget(self.chk_ssao)
        self._checkboxes["ssao"] = self.chk_ssao

        if not SSAOPass.GPU_AVAILABLE:
            coming_soon = QtWidgets.QLabel("Parameter-only mode (GPU SSAO pending)")
            coming_soon.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
            ssao_layout.addWidget(coming_soon)

        for spec in _SSAO_SLIDERS:
            self._add_slider(ssao_layout, spec)

        self.btn_reset_ssao = QtWidgets.QPushButton("Reset AO")
        self.btn_reset_ssao.setObjectName("btn-reset-section")
        ssao_layout.addWidget(self.btn_reset_ssao)

        layout.addWidget(ssao_group)

        # -- Motion Trails section --
        trails_group = QtWidgets.QGroupBox("Motion Trails")
        trails_layout = QtWidgets.QVBoxLayout(trails_group)

        self.chk_trails = QtWidgets.QCheckBox("Enable")
        self.chk_trails.setChecked(False)
        self.chk_trails.setObjectName("chk-trails")
        trails_layout.addWidget(self.chk_trails)
        self._checkboxes["trails"] = self.chk_trails

        for spec in _TRAIL_SLIDERS:
            self._add_slider(trails_layout, spec)

        self.btn_reset_trails = QtWidgets.QPushButton("Reset Trails")
        self.btn_reset_trails.setObjectName("btn-reset-section")
        trails_layout.addWidget(self.btn_reset_trails)

        layout.addWidget(trails_group)

        # -- Global reset --
        self.btn_reset_all = QtWidgets.QPushButton("Reset All Post-FX")
        self.btn_reset_all.setObjectName("btn-reset-all-postfx")
        layout.addWidget(self.btn_reset_all)

        layout.addStretch(1)

    def _add_slider(self, layout: QtWidgets.QVBoxLayout, spec: tuple):
        """Add a labeled slider for a postfx parameter.

        spec: (param_name, label, min_val, max_val, default, fmt)
        """
        param_name, label_text, min_val, max_val, default, fmt = spec

        lbl = QtWidgets.QLabel(label_text)
        layout.addWidget(lbl)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        if max_val > min_val:
            tick = int((default - min_val) / (max_val - min_val) * 100)
        else:
            tick = 0
        slider.setValue(tick)
        slider.setProperty("min_val", float(min_val))
        slider.setProperty("max_val", float(max_val))
        slider.setProperty("param_name", param_name)
        layout.addWidget(slider)

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
        return min_val + t * (max_val - min_val)

    def _connect_signals(self):
        """Wire internal signals to panel signals."""
        # All sliders emit postfx_param_changed
        for param_name, (slider, val_label, spec) in self._sliders.items():
            slider.valueChanged.connect(
                lambda _val, s=slider, vl=val_label, sp=spec: self._on_slider_changed(s, vl, sp)
            )

        # Checkboxes emit postfx_toggled
        self.chk_bloom.toggled.connect(lambda checked: self.postfx_toggled.emit("bloom", checked))
        self.chk_dof.toggled.connect(lambda checked: self.postfx_toggled.emit("dof", checked))
        self.chk_ssao.toggled.connect(lambda checked: self.postfx_toggled.emit("ssao", checked))
        self.chk_trails.toggled.connect(lambda checked: self.postfx_toggled.emit("trails", checked))

        # Section resets
        self.btn_reset_bloom.clicked.connect(lambda: self._reset_section("bloom"))
        self.btn_reset_dof.clicked.connect(lambda: self._reset_section("dof"))
        self.btn_reset_ssao.clicked.connect(lambda: self._reset_section("ssao"))
        self.btn_reset_trails.clicked.connect(lambda: self._reset_section("trails"))
        self.btn_reset_all.clicked.connect(self._on_reset_all)

    def _on_slider_changed(self, slider, val_label, spec):
        """Handle slider value change."""
        param_name, _label, _min, _max, _default, fmt = spec
        val = self._slider_value(slider)
        val_label.setText(fmt.format(val))
        self.postfx_param_changed.emit(param_name, val)

    def _reset_section(self, section_name: str):
        """Reset all sliders and checkbox in a section to defaults."""
        specs, enable_default, checkbox_name = _SECTIONS[section_name]
        for spec in specs:
            param_name = spec[0]
            default = spec[4]
            if param_name in self._sliders:
                slider, val_label, _ = self._sliders[param_name]
                min_val = slider.property("min_val")
                max_val = slider.property("max_val")
                tick = int((default - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
                slider.setValue(tick)

        # Reset checkbox
        if section_name in self._checkboxes:
            self._checkboxes[section_name].setChecked(enable_default)

        self.postfx_section_reset.emit(section_name)

    def _on_reset_all(self):
        """Reset all sections."""
        for section_name in _SECTIONS:
            self._reset_section(section_name)
        self.postfx_reset_all.emit()

    def get_param_value(self, param_name: str) -> float | None:
        """Get current value of a parameter slider."""
        if param_name not in self._sliders:
            return None
        slider, _, _ = self._sliders[param_name]
        return self._slider_value(slider)
