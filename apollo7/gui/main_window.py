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

Wiring:
  - Library: load photos -> ingestion worker -> thumbnails in library panel
  - Extract: button triggers ExtractionWorker for all loaded photos
  - Progressive build: each photo_complete adds point cloud to viewport
  - Controls: sliders update viewport in real-time, mode toggles regenerate
"""

from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from apollo7.config.settings import (
    DEPTH_EXAGGERATION_DEFAULT,
    MIN_WINDOW_SIZE,
    WINDOW_SIZE,
)
from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.cache import FeatureCache
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.depth import DepthExtractor
from apollo7.extraction.edges import EdgeExtractor
from apollo7.extraction.pipeline import ExtractionPipeline
from apollo7.gui.panels.controls_panel import ControlsPanel
from apollo7.gui.panels.feature_strip import FeatureStripPanel
from apollo7.gui.panels.library_panel import LibraryPanel
from apollo7.gui.widgets.progress_bar import ExtractionProgressBar
from apollo7.gui.widgets.viewport_widget import ViewportWidget
from apollo7.ingestion.loader import load_image
from apollo7.pointcloud.generator import PointCloudGenerator
from apollo7.workers.extraction_worker import ExtractionWorker
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

        # Photo data storage: {path: image_array}
        self._loaded_images: dict[str, np.ndarray] = {}
        # Loaded photo paths in order
        self._photo_paths: list[str] = []
        # Extraction results per photo: {path: {extractor_name: ExtractionResult}}
        self._extraction_results: dict[str, dict[str, ExtractionResult]] = {}
        # Currently selected photo
        self._selected_photo: str | None = None
        # Current depth exaggeration value
        self._depth_exaggeration: float = DEPTH_EXAGGERATION_DEFAULT

        # Extraction pipeline and point cloud generator
        self._pipeline = ExtractionPipeline(
            [ColorExtractor(), EdgeExtractor(), DepthExtractor()]
        )
        self._generator = PointCloudGenerator()

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

        # --- Connect all signals ---
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Wire all inter-component signals."""
        # Library: load buttons
        self.library_panel.btn_load_photo.clicked.connect(self._on_load_photo)
        self.library_panel.btn_load_folder.clicked.connect(self._on_load_folder)

        # Library: photo selection -> show features
        self.library_panel.photo_selected.connect(self._on_photo_selected)

        # Controls: extract button
        self.controls_panel.btn_extract.clicked.connect(self._on_extract)
        self.controls_panel.btn_reextract.clicked.connect(self._on_reextract)

        # Controls: sliders -> viewport
        self.controls_panel.point_size_changed.connect(
            lambda v: self.viewport.update_point_material(point_size=v)
        )
        self.controls_panel.opacity_changed.connect(
            lambda v: self.viewport.update_point_material(opacity=v)
        )
        self.controls_panel.depth_exaggeration_changed.connect(
            self._on_depth_exaggeration_changed
        )

        # Controls: layout mode toggle -> viewport
        self.controls_panel.layout_mode_changed.connect(
            self.viewport.set_layout_mode
        )

        # Controls: multi-photo mode toggle -> viewport
        self.controls_panel.multi_photo_mode_changed.connect(
            self.viewport.set_multi_photo_mode
        )

        # Viewport: layout change requested -> regenerate all clouds
        self.viewport.layout_change_requested.connect(
            self._regenerate_all_clouds
        )

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
        and add to the library panel. Also load the full image for extraction.
        """
        buf = io.BytesIO()
        pil_thumbnail.save(buf, format="PNG")  # type: ignore[union-attr]
        buf.seek(0)
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(buf.read(), "PNG")

        self.library_panel.add_photo(path, pixmap, metadata)

        # Load full image into memory for extraction
        try:
            image = load_image(path)
            self._loaded_images[path] = image
            if path not in self._photo_paths:
                self._photo_paths.append(path)
        except Exception as exc:
            logger.warning("Failed to load full image %s: %s", path, exc)

        # Enable extract button once we have at least one photo
        if self._loaded_images:
            self.controls_panel.btn_extract.setEnabled(True)

    def _on_ingestion_progress(self, current: int, total: int) -> None:
        """Update progress bar during ingestion."""
        self.progress_bar.update(current, total)

    def _on_ingestion_finished(self) -> None:
        """Hide progress bar when ingestion completes."""
        self.progress_bar.finish()

    # ------------------------------------------------------------------
    # Photo selection
    # ------------------------------------------------------------------

    def _on_photo_selected(self, photo_path: str) -> None:
        """Handle photo thumbnail click in library panel."""
        self._selected_photo = photo_path
        self.controls_panel.btn_reextract.setEnabled(True)

        # Show cached extraction results in feature strip if available
        results = self._extraction_results.get(photo_path)
        if results:
            self.feature_strip.update_features(photo_path, results)
        else:
            self.feature_strip.clear()

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _on_extract(self) -> None:
        """Launch background extraction for all loaded photos."""
        if not self._loaded_images:
            return

        paths = list(self._photo_paths)
        total = len(paths)
        self.progress_bar.start(total)

        worker = ExtractionWorker(
            photo_paths=paths,
            images=self._loaded_images,
            pipeline=self._pipeline,
            generator=self._generator,
            cache=self._cache,
            mode=self.viewport.layout_mode,
            depth_exaggeration=self._depth_exaggeration,
            multi_photo_mode=self.viewport.multi_photo_mode,
        )
        worker.signals.photo_complete.connect(self._on_extraction_photo_complete)
        worker.signals.progress.connect(self._on_extraction_progress)
        worker.signals.finished.connect(self._on_extraction_finished)
        worker.signals.error.connect(self._on_extraction_error)

        self._thread_pool.start(worker)

    def _on_reextract(self) -> None:
        """Re-extract selected photo, clearing cache first."""
        if not self._selected_photo:
            return
        path = self._selected_photo
        if path not in self._loaded_images:
            return

        # Clear cache for this photo
        self._cache.invalidate(path)
        # Remove existing cloud
        self.viewport.remove_photo_cloud(path)
        # Clear stored results
        self._extraction_results.pop(path, None)

        # Run extraction for just this photo
        self.progress_bar.start(1)
        worker = ExtractionWorker(
            photo_paths=[path],
            images=self._loaded_images,
            pipeline=self._pipeline,
            generator=self._generator,
            cache=self._cache,
            mode=self.viewport.layout_mode,
            depth_exaggeration=self._depth_exaggeration,
            multi_photo_mode=self.viewport.multi_photo_mode,
        )
        worker.signals.photo_complete.connect(self._on_extraction_photo_complete)
        worker.signals.progress.connect(self._on_extraction_progress)
        worker.signals.finished.connect(self._on_extraction_finished)
        worker.signals.error.connect(self._on_extraction_error)

        self._thread_pool.start(worker)

    def _on_extraction_photo_complete(
        self, photo_path: str, features: dict, cloud_data: object
    ) -> None:
        """Handle single photo extraction completion.

        - Add point cloud to viewport (progressive build)
        - Update feature strip if this is the selected photo
        - Store results for later re-generation
        """
        # Store extraction results
        self._extraction_results[photo_path] = features

        # Add point cloud to viewport (main thread -- pygfx scene modification)
        if cloud_data is not None:
            positions, colors, sizes = cloud_data
            layer_index = self._photo_paths.index(photo_path) if photo_path in self._photo_paths else 0
            self.viewport.add_photo_cloud(
                photo_id=photo_path,
                positions=positions,
                colors=colors,
                sizes=sizes,
                layer_index=layer_index,
            )

        # Update feature strip if this photo is selected (or auto-select first)
        if self._selected_photo == photo_path or self._selected_photo is None:
            self._selected_photo = photo_path
            self.feature_strip.update_features(photo_path, features)

        # Update library panel status
        logger.info("Extraction complete for %s", photo_path)

    def _on_extraction_progress(self, current: int, total: int) -> None:
        """Update progress bar during extraction."""
        self.progress_bar.update(current, total)

    def _on_extraction_finished(self) -> None:
        """Finalize extraction batch."""
        self.progress_bar.finish()
        # Final auto-frame to show entire sculpture
        self.viewport.auto_frame()
        logger.info("All extractions complete")

    def _on_extraction_error(self, photo_path: str, error_msg: str) -> None:
        """Log extraction errors."""
        logger.error("Extraction failed for %s: %s", photo_path, error_msg)

    # ------------------------------------------------------------------
    # Layout regeneration
    # ------------------------------------------------------------------

    def _on_depth_exaggeration_changed(self, value: float) -> None:
        """Handle depth exaggeration slider change -- triggers regeneration."""
        self._depth_exaggeration = value
        self._regenerate_all_clouds()

    def _regenerate_all_clouds(self) -> None:
        """Regenerate all point clouds from stored extraction results.

        Called when layout mode, multi-photo mode, or depth exaggeration changes.
        """
        if not self._extraction_results:
            return

        mode = self.viewport.layout_mode
        multi_mode = self.viewport.multi_photo_mode

        for i, path in enumerate(self._photo_paths):
            features = self._extraction_results.get(path)
            image = self._loaded_images.get(path)
            if features is None or image is None:
                continue

            kwargs: dict[str, Any] = {}
            if mode == "depth_projected":
                kwargs["depth_exaggeration"] = self._depth_exaggeration
                if multi_mode == "stacked":
                    kwargs["layer_offset"] = i * (self._depth_exaggeration + 2.0)

            try:
                positions, colors, sizes = self._generator.generate(
                    image, features, mode=mode, **kwargs
                )
                self.viewport.add_photo_cloud(
                    photo_id=path,
                    positions=positions,
                    colors=colors,
                    sizes=sizes,
                    layer_index=i,
                )
            except Exception as exc:
                logger.warning("Cloud regeneration failed for %s: %s", path, exc)

        self.viewport.auto_frame()

    # ------------------------------------------------------------------
    # Legacy extraction API (kept for backward compatibility)
    # ------------------------------------------------------------------

    def run_extraction(self, photo_path: str, image: np.ndarray) -> None:
        """Launch background extraction for a single photo (legacy API).

        Args:
            photo_path: Filesystem path to the photo (used as cache key).
            image: RGB float32 [0-1] numpy array.
        """
        self._loaded_images[photo_path] = image
        if photo_path not in self._photo_paths:
            self._photo_paths.append(photo_path)

        self._on_extract()
