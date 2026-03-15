"""Feature viewer panel showing detailed inspection of all extracted features.

Displays color palette with swatches and hex values, edge map as full-width
image with stats, depth map as blue-to-yellow heatmap with min/max/mean
statistics, and semantic tags as colored pills with confidence scores.
Each section is collapsible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from apollo7.extraction.base import ExtractionResult

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_ACCENT = "#0078FF"
_BG_SECTION = "#242424"
_BG_DARK = "#1a1a1a"
_BORDER = "#3a3a3a"
_TEXT_PRIMARY = "#e0e0e0"
_TEXT_SECONDARY = "#808080"
_TEXT_DIM = "#555555"
_SWATCH_SIZE = 28
_STAT_STYLE = "color: #888; font-size: 11px;"


class _Section(QtWidgets.QWidget):
    """A section with a styled header and content area."""

    def __init__(self, title: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header label
        self._header = QtWidgets.QLabel(f"  {title}")
        self._header.setStyleSheet(f"""
            QLabel {{
                background: {_BG_SECTION};
                color: {_ACCENT};
                border: 1px solid {_BORDER};
                border-radius: 4px;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
                padding: 6px 8px;
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._header)

        # Content container
        self._content = QtWidgets.QWidget()
        self._content.setStyleSheet(f"""
            QWidget {{
                background: {_BG_SECTION};
                border: 1px solid {_BORDER};
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 8, 10, 8)
        self._content_layout.setSpacing(6)
        layout.addWidget(self._content)

    @property
    def content_layout(self) -> QtWidgets.QVBoxLayout:
        """Layout for adding content widgets."""
        return self._content_layout


class _ColorSwatchWidget(QtWidgets.QWidget):
    """Widget that paints a colored rectangle with hex label."""

    def __init__(
        self, r: int, g: int, b: int, weight: float = 0.0,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor(r, g, b)
        self._hex = f"#{r:02x}{g:02x}{b:02x}"
        self._weight = weight
        self.setFixedHeight(_SWATCH_SIZE + 18)
        self.setMinimumWidth(_SWATCH_SIZE + 4)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Swatch rectangle
        rect = QtCore.QRect(
            (self.width() - _SWATCH_SIZE) // 2, 0, _SWATCH_SIZE, _SWATCH_SIZE
        )
        painter.setBrush(self._color)
        painter.setPen(QtGui.QColor(_BORDER))
        painter.drawRoundedRect(rect, 3, 3)

        # Hex text below
        painter.setPen(QtGui.QColor(_TEXT_SECONDARY))
        font = painter.font()
        font.setPixelSize(9)
        painter.setFont(font)
        text_rect = QtCore.QRect(0, _SWATCH_SIZE + 2, self.width(), 16)
        painter.drawText(text_rect, QtCore.Qt.AlignCenter, self._hex)
        painter.end()


class _HistogramWidget(QtWidgets.QWidget):
    """Simple bar chart for RGB histogram painted via QPainter."""

    def __init__(
        self, histogram: np.ndarray, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._histogram = histogram  # shape (3, N) or (N,) for grayscale
        self.setFixedHeight(60)
        self.setMinimumWidth(100)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        if self._histogram.ndim == 1:
            # Single channel
            self._draw_channel(painter, self._histogram, QtGui.QColor(180, 180, 180), w, h)
        elif self._histogram.ndim == 2 and self._histogram.shape[0] >= 3:
            colors = [
                QtGui.QColor(220, 60, 60, 120),   # R
                QtGui.QColor(60, 220, 60, 120),    # G
                QtGui.QColor(60, 60, 220, 120),    # B
            ]
            for ch in range(3):
                self._draw_channel(painter, self._histogram[ch], colors[ch], w, h)

        painter.end()

    def _draw_channel(
        self,
        painter: QtGui.QPainter,
        data: np.ndarray,
        color: QtGui.QColor,
        w: int,
        h: int,
    ) -> None:
        if len(data) == 0:
            return
        max_val = float(data.max()) if data.max() > 0 else 1.0
        n = len(data)
        bar_w = max(1, w / n)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        for i, val in enumerate(data):
            bar_h = int((val / max_val) * h * 0.9)
            x = int(i * bar_w)
            painter.drawRect(QtCore.QRectF(x, h - bar_h, bar_w, bar_h))


# ---------------------------------------------------------------------------
# Mood and object color mappings for semantic pills
# ---------------------------------------------------------------------------
_MOOD_COLORS: dict[str, str] = {
    "serene": "#4488CC",
    "chaotic": "#CC4444",
    "melancholic": "#6644AA",
    "joyful": "#DDAA22",
    "dramatic": "#CC6622",
    "mysterious": "#554488",
    "peaceful": "#44AACC",
    "energetic": "#EE5522",
}

_OBJECT_COLOR = "#22AA88"  # Teal/green for all object tags


class _TagPillWidget(QtWidgets.QWidget):
    """Rounded pill/badge showing a semantic tag label and confidence."""

    def __init__(
        self,
        label: str,
        confidence: float,
        bg_color: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._confidence = confidence
        self._bg_color = bg_color
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.setFixedHeight(24)
        # Calculate width from text
        fm = QtGui.QFontMetrics(QtGui.QFont("", 10))
        text = f"{label} {confidence:.2f}"
        self.setFixedWidth(fm.horizontalAdvance(text) + 20)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = QtCore.QRectF(0, 0, self.width(), self.height())

        # Background with opacity modulated by confidence
        bg = QtGui.QColor(self._bg_color)
        alpha = int(120 + 135 * self._confidence)  # 120-255 range
        bg.setAlpha(min(alpha, 255))
        painter.setBrush(bg)

        # Accent border
        painter.setPen(QtGui.QPen(QtGui.QColor(_ACCENT), 1))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)

        # Text
        painter.setPen(QtGui.QColor(_TEXT_PRIMARY))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        text = f"{self._label} {self._confidence:.2f}"
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)
        painter.end()


class _FlowLayout(QtWidgets.QLayout):
    """Simple flow layout that wraps widgets to the next line when full."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QtWidgets.QLayoutItem] = []
        self._h_spacing = 6
        self._v_spacing = 4

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QtWidgets.QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QtWidgets.QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def sizeHint(self) -> QtCore.QSize:
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return QtCore.QSize(
            size.width() + margins.left() + margins.right(),
            size.height() + margins.top() + margins.bottom(),
        )

    def setGeometry(self, rect: QtCore.QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QtCore.QRect(0, 0, width, 0), test_only=True)

    def _do_layout(self, rect: QtCore.QRect, test_only: bool = False) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + self._v_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(x, y, w, h))
            x += w + self._h_spacing
            line_height = max(line_height, h)

        return y + line_height - rect.y() + margins.bottom()


class FeatureViewerPanel(QtWidgets.QWidget):
    """Scrollable panel showing all extracted features for the selected photo."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feature-viewer")

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll area
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {_BG_DARK};
                border: none;
            }}
        """)

        self._container = QtWidgets.QWidget()
        self._container.setStyleSheet(f"background: {_BG_DARK};")
        self._content_layout = QtWidgets.QVBoxLayout(self._container)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(10)

        self._scroll.setWidget(self._container)
        outer_layout.addWidget(self._scroll)

        # Placeholder
        self._placeholder = QtWidgets.QLabel("Select a photo to view features")
        self._placeholder.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 12px;")
        self._placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self._content_layout.addWidget(self._placeholder)
        self._content_layout.addStretch()

        self._sections: list[QtWidgets.QWidget] = []

    def update_features(
        self, photo_path: str, features: dict[str, "ExtractionResult"]
    ) -> None:
        """Populate all sections from extraction results."""
        self._clear_sections()
        self._placeholder.hide()

        # Color palette section
        self._build_color_section(features.get("color"))

        # Edge map section
        self._build_edge_section(features.get("edge"))

        # Depth map section
        self._build_depth_section(features.get("depth"))

        # Semantic tags section
        self._build_semantic_section(features.get("semantic"))

        self._content_layout.addStretch()

    def clear(self) -> None:
        """Reset to empty state with placeholder message."""
        self._clear_sections()
        self._placeholder.show()

    def _clear_sections(self) -> None:
        """Remove all section widgets."""
        for section in self._sections:
            self._content_layout.removeWidget(section)
            section.deleteLater()
        self._sections.clear()
        # Remove trailing stretch if present
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(self._content_layout.count() - 1)
            w = item.widget()
            if w and w is not self._placeholder:
                w.deleteLater()

    # ------------------------------------------------------------------
    # Color palette section
    # ------------------------------------------------------------------

    def _build_color_section(self, result: "ExtractionResult | None") -> None:
        section = _Section("Color Palette")
        layout = section.content_layout

        if result is None:
            lbl = QtWidgets.QLabel("Not extracted")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)
            self._add_section(section)
            return

        colors = result.data.get("dominant_colors", [])
        weights = result.data.get("color_weights", [])

        if colors:
            swatch_container = QtWidgets.QWidget()
            swatch_container.setStyleSheet("border: none;")
            swatch_layout = QtWidgets.QGridLayout(swatch_container)
            swatch_layout.setContentsMargins(0, 0, 0, 0)
            swatch_layout.setSpacing(6)
            cols = 6
            for i, rgb in enumerate(colors[:18]):
                r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
                w = weights[i] if i < len(weights) else 0.0
                swatch = _ColorSwatchWidget(r, g, b, w)
                swatch_layout.addWidget(swatch, i // cols, i % cols)
            layout.addWidget(swatch_container)

        # RGB histogram if available
        histogram = result.arrays.get("rgb_histogram")
        if histogram is not None:
            hist_label = QtWidgets.QLabel("RGB Histogram")
            hist_label.setStyleSheet(
                f"color: {_TEXT_SECONDARY}; font-size: 10px; font-weight: 600; border: none;"
            )
            layout.addWidget(hist_label)
            layout.addWidget(_HistogramWidget(histogram))

        self._add_section(section)

    # ------------------------------------------------------------------
    # Edge map section
    # ------------------------------------------------------------------

    def _build_edge_section(self, result: "ExtractionResult | None") -> None:
        section = _Section("Edge Map")
        layout = section.content_layout

        if result is None:
            lbl = QtWidgets.QLabel("Not extracted")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)
            self._add_section(section)
            return

        edge_map = result.arrays.get("edge_map")
        if edge_map is not None:
            img_label = QtWidgets.QLabel()
            img_label.setAlignment(QtCore.Qt.AlignCenter)
            img_label.setStyleSheet("border: none;")

            h, w = edge_map.shape[:2]
            qimg = QtGui.QImage(
                edge_map.data, w, h, w, QtGui.QImage.Format_Grayscale8
            )
            pixmap = QtGui.QPixmap.fromImage(qimg)
            # Scale to reasonable width while keeping aspect ratio
            scaled = pixmap.scaledToWidth(
                min(400, pixmap.width()), QtCore.Qt.SmoothTransformation
            )
            img_label.setPixmap(scaled)
            layout.addWidget(img_label)

            # Stats
            total_pixels = edge_map.size
            edge_pixels = int(np.count_nonzero(edge_map))
            pct = (edge_pixels / total_pixels * 100) if total_pixels > 0 else 0
            contour_count = result.data.get("contour_count", "N/A")

            stats_text = f"Edge pixels: {pct:.1f}%"
            if contour_count != "N/A":
                stats_text += f"  |  Contours: {contour_count}"
            stats_label = QtWidgets.QLabel(stats_text)
            stats_label.setStyleSheet(f"{_STAT_STYLE} border: none;")
            layout.addWidget(stats_label)
        else:
            lbl = QtWidgets.QLabel("No edge data available")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)

        self._add_section(section)

    # ------------------------------------------------------------------
    # Depth map section
    # ------------------------------------------------------------------

    def _build_depth_section(self, result: "ExtractionResult | None") -> None:
        section = _Section("Depth Map")
        layout = section.content_layout

        if result is None:
            lbl = QtWidgets.QLabel("Not extracted")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)
            self._add_section(section)
            return

        depth_map = result.arrays.get("depth_map")
        if depth_map is not None:
            img_label = QtWidgets.QLabel()
            img_label.setAlignment(QtCore.Qt.AlignCenter)
            img_label.setStyleSheet("border: none;")

            h, w = depth_map.shape[:2]

            # Blue-to-yellow heatmap
            d = np.clip(depth_map, 0.0, 1.0)
            r_ch = (d * 255).astype(np.uint8)
            g_ch = (d * 255).astype(np.uint8)
            b_ch = (128 * (1.0 - d)).astype(np.uint8)
            rgb = np.stack([r_ch, g_ch, b_ch], axis=-1)
            rgb_c = np.ascontiguousarray(rgb)

            qimg = QtGui.QImage(
                rgb_c.data, w, h, w * 3, QtGui.QImage.Format_RGB888
            )
            pixmap = QtGui.QPixmap.fromImage(qimg)
            scaled = pixmap.scaledToWidth(
                min(400, pixmap.width()), QtCore.Qt.SmoothTransformation
            )
            img_label.setPixmap(scaled)
            layout.addWidget(img_label)

            # Stats
            min_d = float(depth_map.min())
            max_d = float(depth_map.max())
            mean_d = float(depth_map.mean())
            stats_label = QtWidgets.QLabel(
                f"Min: {min_d:.3f}  |  Max: {max_d:.3f}  |  Mean: {mean_d:.3f}"
            )
            stats_label.setStyleSheet(f"{_STAT_STYLE} border: none;")
            layout.addWidget(stats_label)
        else:
            lbl = QtWidgets.QLabel("No depth data available")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)

        self._add_section(section)

    # ------------------------------------------------------------------
    # Semantic tags section
    # ------------------------------------------------------------------

    def _build_semantic_section(self, result: "ExtractionResult | None") -> None:
        section = _Section("Semantic Tags")
        layout = section.content_layout

        if result is None:
            lbl = QtWidgets.QLabel("Run extraction to see semantic tags")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)
            self._add_section(section)
            return

        mood_tags = result.data.get("mood_tags", [])
        object_tags = result.data.get("object_tags", [])

        if mood_tags:
            mood_label = QtWidgets.QLabel("Mood")
            mood_label.setStyleSheet(
                f"color: {_TEXT_SECONDARY}; font-size: 10px; font-weight: 600; border: none;"
            )
            layout.addWidget(mood_label)

            mood_container = QtWidgets.QWidget()
            mood_container.setStyleSheet("border: none;")
            mood_flow = _FlowLayout(mood_container)
            mood_flow.setContentsMargins(0, 0, 0, 0)
            for label, conf in mood_tags:
                color = _MOOD_COLORS.get(label, "#888888")
                pill = _TagPillWidget(label, conf, color)
                mood_flow.addWidget(pill)
            layout.addWidget(mood_container)

        if object_tags:
            obj_label = QtWidgets.QLabel("Objects")
            obj_label.setStyleSheet(
                f"color: {_TEXT_SECONDARY}; font-size: 10px; font-weight: 600; border: none;"
            )
            layout.addWidget(obj_label)

            obj_container = QtWidgets.QWidget()
            obj_container.setStyleSheet("border: none;")
            obj_flow = _FlowLayout(obj_container)
            obj_flow.setContentsMargins(0, 0, 0, 0)
            for label, conf in object_tags:
                pill = _TagPillWidget(label, conf, _OBJECT_COLOR)
                obj_flow.addWidget(pill)
            layout.addWidget(obj_container)

        if not mood_tags and not object_tags:
            lbl = QtWidgets.QLabel("No semantic tags available")
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; border: none;")
            layout.addWidget(lbl)

        self._add_section(section)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_section(self, section: QtWidgets.QWidget) -> None:
        """Add a section widget to the content layout."""
        # Insert before the stretch
        self._content_layout.addWidget(section)
        self._sections.append(section)
