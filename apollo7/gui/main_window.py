"""Apollo 7 main window with viewport-dominant splitter layout.

Layout:
  Horizontal splitter (~73% left, ~27% right):
    Left: Vertical splitter
      - Top: 3D viewport (~85%)
      - Bottom: Feature strip placeholder (~15%, collapsible)
    Right: Vertical splitter
      - Top: Controls placeholder
      - Bottom: Library placeholder
"""

from PySide6 import QtCore, QtWidgets

from apollo7.config.settings import MIN_WINDOW_SIZE, WINDOW_SIZE
from apollo7.gui.widgets.viewport_widget import ViewportWidget


def _make_placeholder(name: str) -> QtWidgets.QWidget:
    """Create a placeholder panel with a centered label."""
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(12, 12, 12, 12)
    label = QtWidgets.QLabel(name)
    label.setObjectName("panel-title")
    label.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(label)
    return widget


class MainWindow(QtWidgets.QMainWindow):
    """Primary application window for Apollo 7."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apollo 7")
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MIN_WINDOW_SIZE)

        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Horizontal splitter: viewport area | right panels ---
        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Left side: viewport + bottom feature strip
        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.viewport = ViewportWidget()
        self.feature_strip = _make_placeholder("Features")
        left_splitter.addWidget(self.viewport)
        left_splitter.addWidget(self.feature_strip)
        left_splitter.setSizes([850, 150])
        left_splitter.setCollapsible(1, True)

        # Right side: controls + library
        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.controls_panel = _make_placeholder("Controls")
        self.library_panel = _make_placeholder("Library")
        right_splitter.addWidget(self.controls_panel)
        right_splitter.addWidget(self.library_panel)
        right_splitter.setSizes([400, 600])

        h_splitter.addWidget(left_splitter)
        h_splitter.addWidget(right_splitter)
        h_splitter.setSizes([1400, 520])  # ~73% viewport

        main_layout.addWidget(h_splitter)
