"""Library panel: scrollable grid of photo thumbnails with load buttons.

Displays ingested photos as a 2-column grid of clickable thumbnails
with filenames. Provides Load Photo and Load Folder buttons at the top.
"""

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


class LibraryPanel(QtWidgets.QWidget):
    """Photo library panel with thumbnail grid and load controls."""

    # Emitted when a photo thumbnail is clicked
    photo_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._photo_count = 0
        self._columns = 2
        self._thumb_size = 120

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QtWidgets.QLabel("Library")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # Load buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(4)

        self.btn_load_photo = QtWidgets.QPushButton("Load Photo")
        self.btn_load_photo.setToolTip("Load a single image file")
        btn_layout.addWidget(self.btn_load_photo)

        self.btn_load_folder = QtWidgets.QPushButton("Load Folder")
        self.btn_load_folder.setToolTip("Load all images from a folder")
        btn_layout.addWidget(self.btn_load_folder)

        layout.addLayout(btn_layout)

        # Photo count label
        self.count_label = QtWidgets.QLabel("0 photos loaded")
        self.count_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.count_label)

        # Scrollable grid area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self._grid_container = QtWidgets.QWidget()
        self._grid_layout = QtWidgets.QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setAlignment(QtCore.Qt.AlignTop)

        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, stretch=1)

    def add_photo(self, path: str, thumbnail_pixmap: QtGui.QPixmap, metadata: dict):
        """Add a photo entry to the library grid.

        Args:
            path: File path of the original image.
            thumbnail_pixmap: QPixmap thumbnail to display.
            metadata: Dict with at least 'width' and 'height' keys.
        """
        row = self._photo_count // self._columns
        col = self._photo_count % self._columns

        # Container widget for thumbnail + label
        card = QtWidgets.QWidget()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)
        card_layout.setSpacing(2)

        # Thumbnail label (clickable)
        thumb_label = QtWidgets.QLabel()
        scaled = thumbnail_pixmap.scaled(
            self._thumb_size,
            self._thumb_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        thumb_label.setPixmap(scaled)
        thumb_label.setAlignment(QtCore.Qt.AlignCenter)
        thumb_label.setFixedSize(self._thumb_size, self._thumb_size)
        thumb_label.setStyleSheet(
            "border: 1px solid #3a3a3a; border-radius: 4px; padding: 2px;"
        )
        thumb_label.setCursor(QtCore.Qt.PointingHandCursor)
        # Store path for click handling
        thumb_label.setProperty("photo_path", path)
        thumb_label.mousePressEvent = lambda _ev, p=path: self.photo_selected.emit(p)

        card_layout.addWidget(thumb_label, alignment=QtCore.Qt.AlignCenter)

        # Filename label
        name = Path(path).name
        if len(name) > 18:
            name = name[:15] + "..."
        name_label = QtWidgets.QLabel(name)
        name_label.setAlignment(QtCore.Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 10px;")
        card_layout.addWidget(name_label)

        self._grid_layout.addWidget(card, row, col)
        self._photo_count += 1
        self.count_label.setText(f"{self._photo_count} photo{'s' if self._photo_count != 1 else ''} loaded")
