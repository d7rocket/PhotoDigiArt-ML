"""Apollo 7 main window with viewport-dominant splitter layout.

Layout:
  Progress bar (hidden by default, shown during processing)
  Horizontal splitter (~73% left, ~27% right):
    Left: Vertical splitter
      - Top: 3D viewport (~85%)
      - Bottom: Feature strip (~15%, collapsible)
    Right: Vertical splitter
      - Top: Controls panel
      - Bottom: Library panel
"""

from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from apollo7.config.settings import MIN_WINDOW_SIZE, WINDOW_SIZE
from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.cache import FeatureCache
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.edges import EdgeExtractor
from apollo7.gui.panels.controls_panel import ControlsPanel
from apollo7.gui.panels.feature_strip import FeatureStripPanel
from apollo7.gui.panels.library_panel import LibraryPanel
from apollo7.gui.widgets.progress_bar import ExtractionProgressBar
from apollo7.gui.widgets.viewport_widget import ViewportWidget
from apollo7.workers.ingestion_worker import IngestionWorker

logger = logging.getLogger(__name__)


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


class _ExtractionWorker(QtCore.QRunnable):
    """Runs feature extraction in a background thread."""

    class Signals(QtCore.QObject):
        finished = QtCore.Signal(str, dict)  # photo_path, results dict
        error = QtCore.Signal(str, str)  # photo_path, error message

    def __init__(
        self,
        photo_path: str,
        image: np.ndarray,
        cache: FeatureCache,
    ) -> None:
        super().__init__()
        self.signals = self.Signals()
        self._photo_path = photo_path
        self._image = image
        self._cache = cache
        self.setAutoDelete(True)

    def run(self) -> None:
        """Extract color and edge features, respecting cache."""
        try:
            results: dict[str, ExtractionResult] = {}
            extractors = [ColorExtractor(), EdgeExtractor()]

            for extractor in extractors:
                cached = self._cache.get(self._photo_path, extractor.name)
                if cached is not None:
                    results[extractor.name] = cached
                    logger.debug(
                        "Cache hit: %s for %s", extractor.name, self._photo_path
                    )
                else:
                    result = extractor.extract(self._image)
                    self._cache.store(self._photo_path, extractor.name, result)
                    results[extractor.name] = result

            self.signals.finished.emit(self._photo_path, results)
        except Exception as exc:
            self.signals.error.emit(self._photo_path, str(exc))


class MainWindow(QtWidgets.QMainWindow):
    """Primary application window for Apollo 7."""

    _IMAGE_FILTER = "Images (*.jpg *.jpeg *.png *.tiff *.tif)"

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Apollo 7")
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MIN_WINDOW_SIZE)

        # Shared state
        self._cache = FeatureCache()
        self._thread_pool = QtCore.QThreadPool.globalInstance()

        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Progress bar (above viewport, hidden until needed) ---
        self.progress_bar = ExtractionProgressBar()
        main_layout.addWidget(self.progress_bar)

        # --- Horizontal splitter: viewport area | right panels ---
        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Left side: viewport + bottom feature strip
        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.viewport = ViewportWidget()
        self.feature_strip = FeatureStripPanel()
        left_splitter.addWidget(self.viewport)
        left_splitter.addWidget(self.feature_strip)
        left_splitter.setSizes([850, 150])
        left_splitter.setCollapsible(1, True)

        # Right side: controls + library (real panels)
        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.controls_panel = ControlsPanel()
        self.library_panel = LibraryPanel()
        right_splitter.addWidget(self.controls_panel)
        right_splitter.addWidget(self.library_panel)
        right_splitter.setSizes([400, 600])

        h_splitter.addWidget(left_splitter)
        h_splitter.addWidget(right_splitter)
        h_splitter.setSizes([1400, 520])  # ~73% viewport

        main_layout.addWidget(h_splitter)

        # --- Connect signals ---
        self.library_panel.btn_load_photo.clicked.connect(self._on_load_photo)
        self.library_panel.btn_load_folder.clicked.connect(self._on_load_folder)

    # ------------------------------------------------------------------
    # Ingestion (load photo / folder)
    # ------------------------------------------------------------------

    def _on_load_photo(self) -> None:
        """Open file dialog for a single image and ingest it."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Photo", "", self._IMAGE_FILTER,
        )
        if not path:
            return
        self._start_ingestion(file_paths=[path])

    def _on_load_folder(self) -> None:
        """Open folder dialog and batch-ingest all images."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Load Folder", "",
        )
        if not folder:
            return
        self._start_ingestion(folder=folder)

    def _start_ingestion(
        self,
        file_paths: list[str] | None = None,
        folder: str | None = None,
    ) -> None:
        """Create and start an IngestionWorker in the thread pool."""
        worker = IngestionWorker(file_paths=file_paths, folder=folder)
        worker.signals.photo_loaded.connect(self._on_photo_loaded)
        worker.signals.progress.connect(self._on_ingestion_progress)
        worker.signals.finished.connect(self._on_ingestion_finished)

        # Show progress bar
        total = len(worker._paths)
        if total > 0:
            self.progress_bar.start(total)

        self._thread_pool.start(worker)

    def _on_photo_loaded(self, path: str, pil_thumbnail: object, metadata: dict) -> None:
        """Handle a single photo loaded by the worker.

        Convert PIL thumbnail to QPixmap in the main thread (Qt requirement)
        and add to the library panel.
        """
        buf = io.BytesIO()
        pil_thumbnail.save(buf, format="PNG")  # type: ignore[union-attr]
        buf.seek(0)
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(buf.read(), "PNG")

        self.library_panel.add_photo(path, pixmap, metadata)

    def _on_ingestion_progress(self, current: int, total: int) -> None:
        """Update progress bar during ingestion."""
        self.progress_bar.update(current, total)

    def _on_ingestion_finished(self) -> None:
        """Hide progress bar when ingestion completes."""
        self.progress_bar.finish()

    # ------------------------------------------------------------------
    # Extraction API (called by library panel photo_selected signal)
    # ------------------------------------------------------------------

    def run_extraction(self, photo_path: str, image: np.ndarray) -> None:
        """Launch background extraction for a photo and update the feature strip.

        Args:
            photo_path: Filesystem path to the photo (used as cache key).
            image: RGB float32 [0-1] numpy array.
        """
        worker = _ExtractionWorker(photo_path, image, self._cache)
        worker.signals.finished.connect(self._on_extraction_finished)
        worker.signals.error.connect(self._on_extraction_error)
        self._thread_pool.start(worker)

    def _on_extraction_finished(
        self, photo_path: str, results: dict[str, Any]
    ) -> None:
        """Update feature strip with extraction results."""
        self.feature_strip.update_features(photo_path, results)
        logger.info("Extraction complete for %s", photo_path)

    def _on_extraction_error(self, photo_path: str, error_msg: str) -> None:
        """Log extraction errors."""
        logger.error("Extraction failed for %s: %s", photo_path, error_msg)
