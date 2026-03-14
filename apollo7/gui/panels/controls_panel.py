"""Controls panel: extraction settings, layout/multi-photo toggles, and sliders.

Provides all user-facing controls for the extraction pipeline and
viewport rendering parameters. Emits signals for real-time updates.
"""

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import (
    DEPTH_EXAGGERATION_DEFAULT,
    DEPTH_EXAGGERATION_RANGE,
    OPACITY_DEFAULT,
    OPACITY_RANGE,
    POINT_SIZE_DEFAULT,
    POINT_SIZE_RANGE,
)


class ControlsPanel(QtWidgets.QWidget):
    """Controls panel with extraction, layout mode, multi-photo mode, and sliders."""

    # Emitted when point size slider changes (float value)
    point_size_changed = QtCore.Signal(float)

    # Emitted when opacity slider changes (float value)
    opacity_changed = QtCore.Signal(float)

    # Emitted when depth exaggeration slider changes (float value)
    depth_exaggeration_changed = QtCore.Signal(float)

    # Emitted when layout mode radio button changes ("depth_projected" or "feature_clustered")
    layout_mode_changed = QtCore.Signal(str)

    # Emitted when multi-photo mode radio button changes ("stacked" or "merged")
    multi_photo_mode_changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

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

        self.btn_reextract = QtWidgets.QPushButton("Re-extract Selected")
        self.btn_reextract.setEnabled(False)
        self.btn_reextract.setToolTip(
            "Re-run extraction on selected photo(s), clearing cache first"
        )
        ext_layout.addWidget(self.btn_reextract)

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

        # --- Multi-photo Mode group ---
        mp_group = QtWidgets.QGroupBox("Multi-photo Mode")
        mp_layout = QtWidgets.QVBoxLayout(mp_group)

        self.radio_stacked = QtWidgets.QRadioButton("Stacked layers")
        self.radio_stacked.setChecked(True)
        self.radio_stacked.setToolTip("Photos as Z-separated layers")
        mp_layout.addWidget(self.radio_stacked)

        self.radio_merged = QtWidgets.QRadioButton("Merged cloud")
        self.radio_merged.setToolTip("All photos merged into one cloud")
        mp_layout.addWidget(self.radio_merged)

        layout.addWidget(mp_group)

        # --- Rendering group ---
        render_group = QtWidgets.QGroupBox("Rendering")
        render_layout = QtWidgets.QVBoxLayout(render_group)

        # Point size slider
        render_layout.addWidget(QtWidgets.QLabel("Point Size"))
        self.slider_point_size = self._create_slider(
            POINT_SIZE_RANGE[0], POINT_SIZE_RANGE[1], POINT_SIZE_DEFAULT
        )
        render_layout.addWidget(self.slider_point_size)
        self._point_size_label = QtWidgets.QLabel(f"{POINT_SIZE_DEFAULT:.1f}")
        self._point_size_label.setAlignment(QtCore.Qt.AlignRight)
        self._point_size_label.setStyleSheet("color: #888; font-size: 10px;")
        render_layout.addWidget(self._point_size_label)

        # Opacity slider
        render_layout.addWidget(QtWidgets.QLabel("Opacity"))
        self.slider_opacity = self._create_slider(
            OPACITY_RANGE[0], OPACITY_RANGE[1], OPACITY_DEFAULT
        )
        render_layout.addWidget(self.slider_opacity)
        self._opacity_label = QtWidgets.QLabel(f"{OPACITY_DEFAULT:.2f}")
        self._opacity_label.setAlignment(QtCore.Qt.AlignRight)
        self._opacity_label.setStyleSheet("color: #888; font-size: 10px;")
        render_layout.addWidget(self._opacity_label)

        # Depth exaggeration slider
        render_layout.addWidget(QtWidgets.QLabel("Depth Exaggeration"))
        self.slider_depth_exaggeration = self._create_slider(
            DEPTH_EXAGGERATION_RANGE[0],
            DEPTH_EXAGGERATION_RANGE[1],
            DEPTH_EXAGGERATION_DEFAULT,
        )
        render_layout.addWidget(self.slider_depth_exaggeration)
        self._depth_exag_label = QtWidgets.QLabel(
            f"{DEPTH_EXAGGERATION_DEFAULT:.1f}x"
        )
        self._depth_exag_label.setAlignment(QtCore.Qt.AlignRight)
        self._depth_exag_label.setStyleSheet("color: #888; font-size: 10px;")
        render_layout.addWidget(self._depth_exag_label)

        layout.addWidget(render_group)

        # Spacer to push content to top
        layout.addStretch(1)

    def _create_slider(
        self, min_val: float, max_val: float, default: float
    ) -> QtWidgets.QSlider:
        """Create a horizontal slider mapping float range to int ticks.

        Uses 100 ticks for the range for smooth control.
        """
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        # Map default to tick position
        if max_val > min_val:
            tick = int((default - min_val) / (max_val - min_val) * 100)
        else:
            tick = 0
        slider.setValue(tick)
        # Store range for value conversion
        slider.setProperty("min_val", min_val)
        slider.setProperty("max_val", max_val)
        return slider

    def _slider_value(self, slider: QtWidgets.QSlider) -> float:
        """Convert slider tick position back to float value."""
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")
        t = slider.value() / 100.0
        return min_val + t * (max_val - min_val)

    def _connect_signals(self) -> None:
        """Wire internal slider/radio signals to typed panel signals."""
        # Point size
        self.slider_point_size.valueChanged.connect(self._on_point_size_changed)

        # Opacity
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)

        # Depth exaggeration
        self.slider_depth_exaggeration.valueChanged.connect(
            self._on_depth_exaggeration_changed
        )

        # Layout mode
        self.radio_depth.toggled.connect(self._on_layout_mode_toggled)

        # Multi-photo mode
        self.radio_stacked.toggled.connect(self._on_multi_photo_mode_toggled)

    def _on_point_size_changed(self) -> None:
        val = self._slider_value(self.slider_point_size)
        self._point_size_label.setText(f"{val:.1f}")
        self.point_size_changed.emit(val)

    def _on_opacity_changed(self) -> None:
        val = self._slider_value(self.slider_opacity)
        self._opacity_label.setText(f"{val:.2f}")
        self.opacity_changed.emit(val)

    def _on_depth_exaggeration_changed(self) -> None:
        val = self._slider_value(self.slider_depth_exaggeration)
        self._depth_exag_label.setText(f"{val:.1f}x")
        self.depth_exaggeration_changed.emit(val)

    def _on_layout_mode_toggled(self, checked: bool) -> None:
        if checked:
            self.layout_mode_changed.emit("depth_projected")
        else:
            self.layout_mode_changed.emit("feature_clustered")

    def _on_multi_photo_mode_toggled(self, checked: bool) -> None:
        if checked:
            self.multi_photo_mode_changed.emit("stacked")
        else:
            self.multi_photo_mode_changed.emit("merged")

    @property
    def depth_exaggeration(self) -> float:
        """Current depth exaggeration value from slider."""
        return self._slider_value(self.slider_depth_exaggeration)
