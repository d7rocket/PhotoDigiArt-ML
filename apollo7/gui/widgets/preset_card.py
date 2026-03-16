"""Gradient thumbnail card widget for preset display.

Each card shows a generated gradient icon that visually represents the
preset's simulation parameters, plus the preset name below.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_BG_CARD = "#2d2d2d"
_BORDER_DEFAULT = "#3a3a3a"
_BORDER_HOVER = "#808080"
_BORDER_SELECTED = "#0078FF"
_TEXT_DEFAULT = "#808080"
_TEXT_SELECTED = "#e0e0e0"

_GRADIENT_HEIGHT = 60


class PresetCard(QtWidgets.QWidget):
    """A compact card displaying a gradient thumbnail and preset name.

    Parameters
    ----------
    name : str
        Display name of the preset.
    preset_data : dict
        Full preset dict with ``sim_params``, ``postfx_params``, etc.
    parent : QWidget | None
        Parent widget.
    """

    clicked = QtCore.Signal(str)

    def __init__(
        self,
        name: str,
        preset_data: dict,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preset_name = name
        self._preset_data = preset_data
        self._selected = False

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._setup_ui()
        self._apply_style()

    # -- Public API ---------------------------------------------------------

    @property
    def preset_name(self) -> str:
        """Read-only preset name."""
        return self._preset_name

    @property
    def preset_data(self) -> dict:
        """Full preset data dict."""
        return self._preset_data

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool) -> None:
        """Update selection state and visual style."""
        self._selected = selected
        self._apply_style()

    # -- Internal -----------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Gradient thumbnail
        self._icon_label = QtWidgets.QLabel()
        self._icon_label.setFixedHeight(_GRADIENT_HEIGHT)
        self._icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self._icon_label.setScaledContents(True)
        pixmap = self._generate_gradient_icon(self._preset_data)
        self._icon_label.setPixmap(pixmap)
        layout.addWidget(self._icon_label)

        # Name label
        self._name_label = QtWidgets.QLabel(self._preset_name)
        self._name_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self._name_label)

    def _apply_style(self) -> None:
        """Apply card border and text styling based on selection state."""
        border = _BORDER_SELECTED if self._selected else _BORDER_DEFAULT
        text_color = _TEXT_SELECTED if self._selected else _TEXT_DEFAULT
        self.setStyleSheet(f"""
            PresetCard {{
                background: {_BG_CARD};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            PresetCard:hover {{
                border-color: {_BORDER_HOVER if not self._selected else _BORDER_SELECTED};
            }}
        """)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {text_color};
                font-size: 11px;
                padding: 4px 8px;
            }}
        """)

    def _generate_gradient_icon(self, preset_data: dict) -> QtGui.QPixmap:
        """Generate a gradient thumbnail from preset simulation parameters.

        Maps key PBF parameters to gradient hue, saturation, and value
        to produce a visually distinct icon for each preset.
        """
        sp = preset_data.get("sim_params", {})

        # Extract key parameters with safe defaults
        solver_iterations = sp.get("solver_iterations", 2)
        noise_amplitude = sp.get("noise_amplitude", 1.0)
        home_strength = sp.get("home_strength", 5.0)

        # Map params to HSV color components
        hue = 0.58 + (noise_amplitude / 5.0) * 0.25
        saturation = 0.4 + (solver_iterations / 6.0) * 0.4
        value = 0.2 + (home_strength / 20.0) * 0.4

        # Clamp to valid ranges
        hue = max(0.0, min(1.0, hue))
        saturation = max(0.0, min(1.0, saturation))
        value = max(0.0, min(1.0, value))

        width = 80
        height = _GRADIENT_HEIGHT
        pixmap = QtGui.QPixmap(width, height)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        gradient = QtGui.QLinearGradient(0, 0, width, height)
        color1 = QtGui.QColor.fromHsvF(hue, saturation, value)
        hue2 = (hue + 0.15) % 1.0
        color2 = QtGui.QColor.fromHsvF(hue2, saturation * 0.8, min(1.0, value + 0.15))
        gradient.setColorAt(0.0, color1)
        gradient.setColorAt(1.0, color2)

        painter.fillRect(0, 0, width, height, gradient)
        painter.end()

        return pixmap

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        """Emit clicked signal with preset name."""
        self.clicked.emit(self._preset_name)
        super().mousePressEvent(event)
