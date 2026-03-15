"""QGraphicsScene-based patch bay editor for feature-to-parameter mapping.

Provides a visual node-wire interface where feature outputs on the left
connect to parameter inputs on the right via draggable Bezier wires.
Each wire has an adjustable strength control.

Designed as a standalone overlay widget for MainWindow integration.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPen,
    QPainter,
    QPainterPath,
    QFont,
    QLinearGradient,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QGraphicsProxyWidget,
)

from apollo7.mapping.connections import MappingConnection, MappingGraph
from apollo7.mapping.engine import FEATURE_SOURCES, TARGET_PARAMS


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

_BG_COLOR = QColor("#1A1A1A")
_NODE_BG = QColor("#1E1E1E")
_NODE_BORDER = QColor("#333333")
_FEATURE_ACCENT = QColor("#0078FF")
_PARAM_ACCENT = QColor("#00CC66")
_TEXT_COLOR = QColor("#CCCCCC")
_PORT_DEFAULT = QColor("#888888")
_PORT_HOVER = QColor("#FFFFFF")
_WIRE_SELECTED = QColor("#FFCC00")

# Wire colors by feature type
_WIRE_COLORS: dict[str, QColor] = {
    "semantic": QColor("#FF6644"),  # warm orange-red
    "color": QColor("#44AAFF"),     # cool blue
    "depth": QColor("#999999"),     # grey
    "edge": QColor("#777777"),      # dark grey
}

_DEFAULT_WIRE_COLOR = QColor("#AAAAAA")

# Layout constants
_NODE_WIDTH = 160
_PORT_SPACING = 24
_PORT_RADIUS = 6
_COLUMN_GAP = 400
_LEFT_X = 40
_RIGHT_X = _LEFT_X + _COLUMN_GAP
_TOP_Y = 60


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------

class Port(QGraphicsEllipseItem):
    """A connection port on a node (output on left, input on right)."""

    def __init__(
        self,
        name: str,
        is_output: bool,
        node: NodeItem,
        parent: QGraphicsItem | None = None,
    ) -> None:
        r = _PORT_RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r, parent)
        self.name = name
        self.is_output = is_output
        self.node = node
        self._hovered = False

        self.setBrush(QBrush(_PORT_DEFAULT))
        self.setPen(QPen(Qt.NoPen))
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    @property
    def center_scene_pos(self) -> QPointF:
        """Port center in scene coordinates."""
        return self.scenePos()

    def hoverEnterEvent(self, event):  # noqa: N802
        self._hovered = True
        self.setBrush(QBrush(_PORT_HOVER))
        self.update()

    def hoverLeaveEvent(self, event):  # noqa: N802
        self._hovered = False
        self.setBrush(QBrush(_PORT_DEFAULT))
        self.update()


# ---------------------------------------------------------------------------
# NodeItem
# ---------------------------------------------------------------------------

class NodeItem(QGraphicsRectItem):
    """A fixed-position node with a label and ports.

    Feature nodes sit on the left column (output ports on right edge).
    Parameter nodes sit on the right column (input ports on left edge).
    """

    def __init__(
        self,
        label: str,
        port_names: list[str],
        is_feature: bool,
        x: float,
        y: float,
        parent: QGraphicsItem | None = None,
    ) -> None:
        header_h = 28
        body_h = max(len(port_names) * _PORT_SPACING + 8, 32)
        total_h = header_h + body_h
        super().__init__(0, 0, _NODE_WIDTH, total_h, parent)

        self.label = label
        self.is_feature = is_feature
        self.ports: list[Port] = []

        self.setPos(x, y)
        self.setBrush(QBrush(_NODE_BG))
        self.setPen(QPen(_NODE_BORDER, 1))
        self.setZValue(1)

        # Rounded rect via custom paint
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)

        # Header label
        accent = _FEATURE_ACCENT if is_feature else _PARAM_ACCENT
        title = QGraphicsSimpleTextItem(label, self)
        title.setBrush(QBrush(accent))
        title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title.setPos(8, 4)

        # Create ports
        for i, port_name in enumerate(port_names):
            port = Port(
                name=port_name,
                is_output=is_feature,
                node=self,
            )
            port.setParentItem(self)

            # Position: outputs on right edge, inputs on left edge
            port_y = header_h + 12 + i * _PORT_SPACING
            if is_feature:
                port_x = _NODE_WIDTH  # right edge
            else:
                port_x = 0  # left edge

            port.setPos(port_x, port_y)
            self.ports.append(port)

            # Port label
            plabel = QGraphicsSimpleTextItem(port_name, self)
            plabel.setBrush(QBrush(_TEXT_COLOR))
            plabel.setFont(QFont("Segoe UI", 8))
            if is_feature:
                # Label to left of port
                plabel.setPos(8, port_y - 7)
            else:
                # Label to right of port
                plabel.setPos(12, port_y - 7)


# ---------------------------------------------------------------------------
# Wire
# ---------------------------------------------------------------------------

class Wire(QGraphicsPathItem):
    """A Bezier curve connecting an output port to an input port."""

    def __init__(
        self,
        source_port: Port,
        target_port: Port,
        strength: float = 1.0,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.source_port = source_port
        self.target_port = target_port
        self.strength = strength

        # Determine wire color from source feature type
        feature_name = source_port.node.label.split(":")[0].strip().lower()
        # Map node labels back to feature types
        color = _DEFAULT_WIRE_COLOR
        for key, c in _WIRE_COLORS.items():
            if key in feature_name or key in source_port.name.lower():
                color = c
                break

        self._base_color = color
        self._selected = False

        pen = QPen(color, 2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(5)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        # Strength label at midpoint
        self._strength_label = QGraphicsSimpleTextItem(self)
        self._strength_label.setFont(QFont("Segoe UI", 7))
        self._strength_label.setBrush(QBrush(_TEXT_COLOR))

        self._update_path()

    def _update_path(self) -> None:
        """Redraw the Bezier curve between source and target ports."""
        p1 = self.source_port.center_scene_pos
        p2 = self.target_port.center_scene_pos

        dx = abs(p2.x() - p1.x()) / 3.0
        path = QPainterPath(p1)
        path.cubicTo(
            QPointF(p1.x() + dx, p1.y()),
            QPointF(p2.x() - dx, p2.y()),
            p2,
        )
        self.setPath(path)

        # Position strength label at midpoint
        mid = path.pointAtPercent(0.5)
        self._strength_label.setText(f"{self.strength:.2f}")
        self._strength_label.setPos(mid.x() - 12, mid.y() - 14)

    def set_strength(self, value: float) -> None:
        """Update strength value and redraw label."""
        self.strength = value
        self._strength_label.setText(f"{self.strength:.2f}")

    def paint(self, painter, option, widget=None):
        """Custom paint with selection highlight."""
        if self.isSelected():
            pen = QPen(_WIRE_SELECTED, 3, Qt.SolidLine)
            pen.setCapStyle(Qt.RoundCap)
            self.setPen(pen)
        else:
            pen = QPen(self._base_color, 2, Qt.SolidLine)
            pen.setCapStyle(Qt.RoundCap)
            self.setPen(pen)
        super().paint(painter, option, widget)


# ---------------------------------------------------------------------------
# Temporary drag wire
# ---------------------------------------------------------------------------

class _TempWire(QGraphicsPathItem):
    """Temporary wire shown during drag from an output port."""

    def __init__(self, start: QPointF) -> None:
        super().__init__()
        self._start = start
        pen = QPen(QColor("#FFFFFF"), 2, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(20)

    def update_end(self, end: QPointF) -> None:
        """Update the drag endpoint."""
        dx = abs(end.x() - self._start.x()) / 3.0
        path = QPainterPath(self._start)
        path.cubicTo(
            QPointF(self._start.x() + dx, self._start.y()),
            QPointF(end.x() - dx, end.y()),
            end,
        )
        self.setPath(path)


# ---------------------------------------------------------------------------
# PatchBayScene
# ---------------------------------------------------------------------------

class PatchBayScene(QGraphicsScene):
    """Scene managing feature nodes, parameter nodes, and wires.

    Signals:
        connection_added: Emitted when a new wire is created.
        connection_removed: Emitted when a wire is deleted.
        strength_changed: Emitted when a wire's strength is changed.
    """

    connection_added = Signal(object)    # MappingConnection
    connection_removed = Signal(object)  # MappingConnection
    strength_changed = Signal(object)    # MappingConnection

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, _RIGHT_X + _NODE_WIDTH + 80, 800)

        self._feature_nodes: list[NodeItem] = []
        self._param_nodes: list[NodeItem] = []
        self._wires: list[Wire] = []
        self._temp_wire: _TempWire | None = None
        self._drag_source: Port | None = None
        self._strength_editor: QGraphicsProxyWidget | None = None

        self._build_nodes()

    def _build_nodes(self) -> None:
        """Create feature output and parameter input nodes."""
        # Group feature sources by feature type for node organization
        feature_groups: dict[str, list[str]] = {}
        for (feat, key), label in FEATURE_SOURCES.items():
            feature_groups.setdefault(feat, []).append(key)

        # Feature nodes (left column)
        y = _TOP_Y
        group_labels = {
            "semantic": "Semantic",
            "color": "Color",
            "depth": "Depth",
            "edge": "Edge",
        }
        for feat_type in ["semantic", "color", "depth", "edge"]:
            keys = feature_groups.get(feat_type, [])
            if not keys:
                continue
            node = NodeItem(
                label=group_labels.get(feat_type, feat_type.title()),
                port_names=keys,
                is_feature=True,
                x=_LEFT_X,
                y=y,
            )
            self.addItem(node)
            self._feature_nodes.append(node)
            y += node.rect().height() + 16

        # Parameter nodes (right column)
        param_names = list(TARGET_PARAMS.keys())
        # Split into two groups for better layout
        mid = len(param_names) // 2
        groups = [param_names[:mid], param_names[mid:]]
        y = _TOP_Y
        for group in groups:
            node = NodeItem(
                label="Parameters",
                port_names=group,
                is_feature=False,
                x=_RIGHT_X,
                y=y,
            )
            self.addItem(node)
            self._param_nodes.append(node)
            y += node.rect().height() + 16

        # Adjust scene rect to fit content
        self.setSceneRect(
            0, 0,
            _RIGHT_X + _NODE_WIDTH + 80,
            max(y + 40, 600),
        )

    def _find_port_at(self, scene_pos: QPointF) -> Port | None:
        """Find a Port item near the given scene position."""
        for item in self.items(scene_pos):
            if isinstance(item, Port):
                return item
        return None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Start wire drag from output port, or handle selection."""
        port = self._find_port_at(event.scenePos())
        if port is not None and port.is_output:
            # Start dragging a new wire
            self._drag_source = port
            self._temp_wire = _TempWire(port.center_scene_pos)
            self.addItem(self._temp_wire)
            return

        # Check if clicking on a wire for strength editing
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else __import__("PySide6.QtGui", fromlist=["QTransform"]).QTransform())
        if isinstance(item, Wire) and event.button() == Qt.RightButton:
            self._show_strength_editor(item, event.scenePos())
            return

        # Handle wire deletion on right-click
        if isinstance(item, Wire) and event.button() == Qt.RightButton:
            self._remove_wire(item)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Update temporary wire during drag."""
        if self._temp_wire is not None:
            self._temp_wire.update_end(event.scenePos())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # noqa: N802
        """Complete wire creation on release over input port."""
        if self._temp_wire is not None and self._drag_source is not None:
            target_port = self._find_port_at(event.scenePos())
            if (
                target_port is not None
                and not target_port.is_output
                and target_port is not self._drag_source
            ):
                self._create_wire(self._drag_source, target_port)

            # Clean up temp wire
            self.removeItem(self._temp_wire)
            self._temp_wire = None
            self._drag_source = None
            return

        super().mouseReleaseEvent(event)

    def _create_wire(self, source: Port, target: Port) -> None:
        """Create a permanent wire and emit connection_added."""
        wire = Wire(source, target)
        self.addItem(wire)
        self._wires.append(wire)

        conn = MappingConnection(
            source_feature=self._port_feature_name(source),
            source_key=source.name,
            target_param=target.name,
            strength=wire.strength,
        )
        self.connection_added.emit(conn)

    def _remove_wire(self, wire: Wire) -> None:
        """Remove a wire and emit connection_removed."""
        conn = MappingConnection(
            source_feature=self._port_feature_name(wire.source_port),
            source_key=wire.source_port.name,
            target_param=wire.target_port.name,
            strength=wire.strength,
        )
        self.removeItem(wire)
        if wire in self._wires:
            self._wires.remove(wire)
        self.connection_removed.emit(conn)

    def _show_strength_editor(self, wire: Wire, pos: QPointF) -> None:
        """Show a small strength spinner on right-click."""
        # Remove any existing editor
        if self._strength_editor is not None:
            self.removeItem(self._strength_editor)
            self._strength_editor = None

        spin = QDoubleSpinBox()
        spin.setRange(-10.0, 10.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(2)
        spin.setValue(wire.strength)
        spin.setFixedWidth(80)
        spin.setStyleSheet(
            "QDoubleSpinBox { background: #2B2B2B; color: #CCCCCC; "
            "border: 1px solid #555; padding: 2px; }"
        )

        def on_value_changed(val: float) -> None:
            wire.set_strength(val)
            conn = MappingConnection(
                source_feature=self._port_feature_name(wire.source_port),
                source_key=wire.source_port.name,
                target_param=wire.target_port.name,
                strength=val,
            )
            self.strength_changed.emit(conn)

        spin.valueChanged.connect(on_value_changed)

        proxy = self.addWidget(spin)
        proxy.setPos(pos.x() - 40, pos.y() - 12)
        proxy.setZValue(50)
        self._strength_editor = proxy

        # Auto-remove after losing focus
        spin.editingFinished.connect(lambda: self._dismiss_strength_editor())

    def _dismiss_strength_editor(self) -> None:
        """Remove the strength editor proxy widget."""
        if self._strength_editor is not None:
            self.removeItem(self._strength_editor)
            self._strength_editor = None

    def _port_feature_name(self, port: Port) -> str:
        """Derive the feature extractor name from a port's parent node label."""
        label = port.node.label.lower()
        for key in ["semantic", "color", "depth", "edge"]:
            if key in label:
                return key
        return label

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Delete selected wire on Delete key."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                if isinstance(item, Wire):
                    self._remove_wire(item)
            return
        super().keyPressEvent(event)

    def set_graph(self, graph: MappingGraph) -> None:
        """Load existing connections as wires.

        Clears current wires and rebuilds from the graph.
        """
        # Remove existing wires
        for wire in list(self._wires):
            self.removeItem(wire)
        self._wires.clear()

        # Build port lookup tables
        output_ports: dict[tuple[str, str], Port] = {}
        for node in self._feature_nodes:
            feat_name = self._port_feature_name(node.ports[0]) if node.ports else ""
            for port in node.ports:
                output_ports[(feat_name, port.name)] = port

        input_ports: dict[str, Port] = {}
        for node in self._param_nodes:
            for port in node.ports:
                input_ports[port.name] = port

        # Create wires for each connection
        for conn in graph.get_connections():
            src = output_ports.get((conn.source_feature, conn.source_key))
            tgt = input_ports.get(conn.target_param)
            if src is not None and tgt is not None:
                wire = Wire(src, tgt, strength=conn.strength)
                self.addItem(wire)
                self._wires.append(wire)

    def get_graph(self) -> MappingGraph:
        """Export current wire state as a MappingGraph."""
        graph = MappingGraph()
        for wire in self._wires:
            conn = MappingConnection(
                source_feature=self._port_feature_name(wire.source_port),
                source_key=wire.source_port.name,
                target_param=wire.target_port.name,
                strength=wire.strength,
            )
            graph.add_connection(conn)
        return graph

    def clear_all_wires(self) -> None:
        """Remove all wires from the scene."""
        for wire in list(self._wires):
            self._remove_wire(wire)


# ---------------------------------------------------------------------------
# PatchBayEditor
# ---------------------------------------------------------------------------

class PatchBayEditor(QWidget):
    """Full overlay widget containing the patch bay scene.

    Designed to be shown as a modal overlay in MainWindow.

    Signals:
        mapping_changed: Emitted on any connection add/remove/strength change.
        close_requested: Emitted when user clicks close or presses Escape.
    """

    mapping_changed = Signal(object)  # MappingGraph
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PatchBayEditor")
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the editor layout: header, graphics view, footer."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet(
            "background-color: #2B2B2B; border-bottom: 1px solid #444;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)

        title = QLabel("Feature Mapping")
        title.setStyleSheet("color: #0078FF; font-size: 13px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #CCCCCC; "
            "font-weight: bold; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #FF4444; }"
        )
        close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Graphics view
        self._scene = PatchBayScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setBackgroundBrush(QBrush(_BG_COLOR))
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setStyleSheet(
            "QGraphicsView { border: none; }"
            "QScrollBar:vertical { background: #1A1A1A; width: 8px; }"
            "QScrollBar::handle:vertical { background: #444; border-radius: 4px; }"
        )
        layout.addWidget(self._view)

        # Footer bar
        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(
            "background-color: #2B2B2B; border-top: 1px solid #444;"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(
            "QPushButton { background: #3A3A3A; color: #CCCCCC; "
            "border: 1px solid #555; border-radius: 3px; padding: 4px 12px; }"
            "QPushButton:hover { background: #FF4444; color: white; }"
        )
        clear_btn.clicked.connect(self._on_clear_all)
        footer_layout.addWidget(clear_btn)

        footer_layout.addStretch()
        layout.addWidget(footer)

        # Overall styling
        self.setStyleSheet("background-color: #1A1A1A;")

    def _connect_signals(self) -> None:
        """Wire up scene signals to emit mapping_changed."""
        self._scene.connection_added.connect(self._on_mapping_changed)
        self._scene.connection_removed.connect(self._on_mapping_changed)
        self._scene.strength_changed.connect(self._on_mapping_changed)

    def _on_mapping_changed(self, _conn=None) -> None:
        """Emit the full graph on any change."""
        self.mapping_changed.emit(self._scene.get_graph())

    def _on_clear_all(self) -> None:
        """Clear all wires."""
        self._scene.clear_all_wires()
        self.mapping_changed.emit(self._scene.get_graph())

    def set_graph(self, graph: MappingGraph) -> None:
        """Load an existing mapping graph into the editor."""
        self._scene.set_graph(graph)

    def get_graph(self) -> MappingGraph:
        """Export the current mapping state."""
        return self._scene.get_graph()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Escape closes the editor."""
        if event.key() == Qt.Key_Escape:
            self.close_requested.emit()
            return
        super().keyPressEvent(event)
