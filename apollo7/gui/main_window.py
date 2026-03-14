"""Apollo 7 main window with viewport-dominant splitter layout.

Layout:
  Progress bar (hidden by default, shown during processing)
  Horizontal splitter (~73% left, ~27% right):
    Left: Vertical splitter
      - Top: 3D viewport (~85%)
      - Bottom: Feature viewer (~15%, collapsible)
    Right: Vertical splitter
      - Top: Controls panel
      - Middle: Simulation panel
      - Middle: PostFX panel
      - Bottom: Library panel

Wiring:
  - Library: load photos -> ingestion worker -> thumbnails in library panel
  - Extract: button triggers ExtractionWorker for all loaded photos
  - Progressive build: each photo_complete adds point cloud to viewport
  - Controls: sliders update viewport in real-time, mode toggles regenerate
  - Simulation: Simulate button -> init engine -> start animation loop
"""

from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QUndoStack

from apollo7.config.settings import (
    DEPTH_EXAGGERATION_DEFAULT,
    MIN_WINDOW_SIZE,
    OPACITY_DEFAULT,
    POINT_SIZE_DEFAULT,
    WINDOW_SIZE,
)
from apollo7.gui.widgets.undo_commands import ParameterChangeCommand, ResetSectionCommand
from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.cache import FeatureCache
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.depth import DepthExtractor
from apollo7.extraction.edges import EdgeExtractor
from apollo7.extraction.pipeline import ExtractionPipeline
from apollo7.config.settings import (
    BLOOM_STRENGTH_DEFAULT,
    DOF_APERTURE_DEFAULT,
    DOF_FOCAL_DEFAULT,
    SSAO_INTENSITY_DEFAULT,
    SSAO_RADIUS_DEFAULT,
    TRAIL_LENGTH_DEFAULT,
)
from apollo7.gui.panels.controls_panel import ControlsPanel
from apollo7.gui.panels.feature_strip import FeatureStripPanel
from apollo7.gui.panels.feature_viewer import FeatureViewerPanel
from apollo7.gui.panels.library_panel import LibraryPanel
from apollo7.gui.panels.postfx_panel import PostFXPanel
from apollo7.gui.panels.simulation_panel import SimulationPanel
from apollo7.gui.widgets.progress_bar import ExtractionProgressBar
from apollo7.gui.widgets.viewport_widget import ViewportWidget
from apollo7.ingestion.loader import load_image
from apollo7.pointcloud.generator import PointCloudGenerator
from apollo7.simulation.parameters import SimulationParams
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

        # Undo/redo stack
        self._undo_stack = QUndoStack(self)

        # Track previous slider values for undo commands
        self._prev_values: dict[str, float] = {
            "point_size": POINT_SIZE_DEFAULT,
            "opacity": OPACITY_DEFAULT,
            "depth_exaggeration": DEPTH_EXAGGERATION_DEFAULT,
            "bloom_strength": BLOOM_STRENGTH_DEFAULT,
            "dof_focal_distance": DOF_FOCAL_DEFAULT,
            "dof_aperture": DOF_APERTURE_DEFAULT,
            "ssao_radius": SSAO_RADIUS_DEFAULT,
            "ssao_intensity": SSAO_INTENSITY_DEFAULT,
            "trail_length": TRAIL_LENGTH_DEFAULT,
        }

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

        # Left side: viewport + bottom feature viewer
        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.viewport = ViewportWidget()
        self.feature_strip = FeatureStripPanel()  # kept for backward compat
        self.feature_viewer = FeatureViewerPanel()
        left_splitter.addWidget(self.viewport)
        left_splitter.addWidget(self.feature_viewer)
        left_splitter.setSizes([850, 150])
        left_splitter.setCollapsible(1, True)

        # Right side: controls + simulation + postfx + library (real panels)
        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.controls_panel = ControlsPanel()
        self.simulation_panel = SimulationPanel()
        self.postfx_panel = PostFXPanel()
        self.library_panel = LibraryPanel()
        right_splitter.addWidget(self.controls_panel)
        right_splitter.addWidget(self.simulation_panel)
        right_splitter.addWidget(self.postfx_panel)
        right_splitter.addWidget(self.library_panel)
        right_splitter.setSizes([250, 300, 250, 200])

        h_splitter.addWidget(left_splitter)
        h_splitter.addWidget(right_splitter)
        h_splitter.setSizes([1400, 520])  # ~73% viewport

        main_layout.addWidget(h_splitter)

        # --- Initialize post-processing effects ---
        self.viewport.init_postfx()

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

        # Controls: sliders -> viewport (wrapped with undo support)
        self.controls_panel.point_size_changed.connect(
            lambda v: self._push_param_change("point_size", v, 0)
        )
        self.controls_panel.opacity_changed.connect(
            lambda v: self._push_param_change("opacity", v, 1)
        )
        self.controls_panel.depth_exaggeration_changed.connect(
            lambda v: self._push_param_change("depth_exaggeration", v, 2)
        )

        # Undo/redo keyboard shortcuts
        undo_action = self._undo_stack.createUndoAction(self, "Undo")
        undo_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_Z))
        self.addAction(undo_action)

        redo_action = self._undo_stack.createRedoAction(self, "Redo")
        redo_action.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.SHIFT | QtCore.Qt.Key_Z)
        )
        self.addAction(redo_action)

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

        # --- PostFX panel signals ---
        # PostFX param changes -> undo stack -> viewport
        # Merge ID offsets 100+ to avoid collision with sim params
        self.postfx_panel.postfx_param_changed.connect(
            self._on_postfx_param_changed
        )

        # PostFX toggle -> viewport (no undo for toggles)
        self.postfx_panel.postfx_toggled.connect(
            self.viewport.toggle_postfx
        )

        # PostFX resets
        self.postfx_panel.postfx_section_reset.connect(
            self._on_postfx_section_reset
        )
        self.postfx_panel.postfx_reset_all.connect(
            self._on_postfx_reset_all
        )

        # --- Simulation panel signals ---
        self.simulation_panel.simulate_clicked.connect(self._on_simulate)
        self.simulation_panel.pause_toggled.connect(self._on_pause_toggled)
        self.simulation_panel.performance_mode_changed.connect(
            self._on_performance_mode_changed
        )
        self.simulation_panel.param_changed.connect(self._on_sim_param_changed)
        self.simulation_panel.section_reset.connect(self._on_section_reset)
        self.simulation_panel.reset_all.connect(self._on_reset_all_sim)

        # --- Keyboard shortcuts ---
        # Space: toggle pause/resume simulation
        space_action = QtGui.QAction("Toggle Pause", self)
        space_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space))
        space_action.triggered.connect(self._on_space_pressed)
        self.addAction(space_action)

        # Ctrl+S: save project (placeholder)
        save_action = QtGui.QAction("Save", self)
        save_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_S))
        save_action.triggered.connect(lambda: logger.info("Save: placeholder"))
        self.addAction(save_action)

        # Ctrl+E: export image (placeholder)
        export_action = QtGui.QAction("Export", self)
        export_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_E))
        export_action.triggered.connect(lambda: logger.info("Export: placeholder"))
        self.addAction(export_action)

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

        # Show cached extraction results in feature viewer if available
        results = self._extraction_results.get(photo_path)
        if results:
            self.feature_viewer.update_features(photo_path, results)
        else:
            self.feature_viewer.clear()

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

        # Update feature viewer if this photo is selected (or auto-select first)
        if self._selected_photo == photo_path or self._selected_photo is None:
            self._selected_photo = photo_path
            self.feature_viewer.update_features(photo_path, features)

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

    # ------------------------------------------------------------------
    # Undo/redo parameter change support
    # ------------------------------------------------------------------

    def _push_param_change(
        self, param_name: str, new_value: float, merge_id_offset: int
    ) -> None:
        """Push an undoable parameter change onto the undo stack."""
        old_value = self._prev_values.get(param_name, new_value)
        if old_value == new_value:
            return
        cmd = ParameterChangeCommand(
            param_name=param_name,
            old_value=old_value,
            new_value=new_value,
            apply_fn=self._apply_param,
            merge_id_offset=merge_id_offset,
        )
        self._prev_values[param_name] = new_value
        self._undo_stack.push(cmd)

    def _apply_param(self, param_name: str, value: float) -> None:
        """Apply a parameter value to the viewport (called by undo/redo)."""
        self._prev_values[param_name] = value
        if param_name == "point_size":
            self.viewport.update_point_material(point_size=value)
        elif param_name == "opacity":
            self.viewport.update_point_material(opacity=value)
        elif param_name == "depth_exaggeration":
            self._on_depth_exaggeration_changed(value)
        elif param_name.startswith(("bloom_", "dof_", "ssao_", "trail_")):
            self.viewport.update_postfx_param(param_name, value)
        else:
            # Route simulation params to viewport
            self.viewport.update_sim_param(param_name, value)

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
    # PostFX parameter handling
    # ------------------------------------------------------------------

    # Merge ID offsets for postfx params (100+ to avoid sim param collisions)
    _POSTFX_MERGE_IDS: dict[str, int] = {
        "bloom_strength": 100,
        "dof_focal_distance": 101,
        "dof_aperture": 102,
        "ssao_radius": 103,
        "ssao_intensity": 104,
        "trail_length": 105,
    }

    def _on_postfx_param_changed(self, param_name: str, value: float) -> None:
        """Handle postfx slider change via undo stack."""
        merge_id = self._POSTFX_MERGE_IDS.get(param_name, 100)
        self._push_param_change(param_name, value, merge_id)

    def _on_postfx_section_reset(self, section_name: str) -> None:
        """Handle postfx section reset via undo stack."""
        from apollo7.gui.panels.postfx_panel import _SECTIONS

        specs, enable_default, checkbox_name = _SECTIONS.get(section_name, ([], False, ""))
        params: dict[str, tuple[float, float]] = {}
        for spec in specs:
            param_name = spec[0]
            default = spec[4]
            old_value = self._prev_values.get(param_name, default)
            params[param_name] = (old_value, default)

        if params:
            cmd = ResetSectionCommand(params, self._apply_param)
            self._undo_stack.push(cmd)

    def _on_postfx_reset_all(self) -> None:
        """Handle global postfx reset via undo stack."""
        from apollo7.gui.panels.postfx_panel import _SECTIONS

        params: dict[str, tuple[float, float]] = {}
        for section_name, (specs, _, _) in _SECTIONS.items():
            for spec in specs:
                param_name = spec[0]
                default = spec[4]
                old_value = self._prev_values.get(param_name, default)
                params[param_name] = (old_value, default)

        if params:
            cmd = ResetSectionCommand(params, self._apply_param)
            self._undo_stack.push(cmd)

    # ------------------------------------------------------------------
    # Simulation controls
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        """Handle Simulate button click: init engine and start animation."""
        if not self._extraction_results:
            logger.warning("Cannot simulate: no extraction results")
            return

        # Gather all positions and colors from photo clouds
        all_positions = []
        all_colors = []
        for path in self._photo_paths:
            cloud = self.viewport._photo_clouds.get(path)
            if cloud is None:
                continue
            geo = cloud.geometry
            if geo.positions is not None:
                all_positions.append(geo.positions.data.copy())
            if geo.colors is not None:
                all_colors.append(geo.colors.data.copy())

        if not all_positions:
            logger.warning("Cannot simulate: no point clouds in viewport")
            return

        positions = np.concatenate(all_positions, axis=0)
        colors = np.concatenate(all_colors, axis=0)

        # Gather feature textures from extraction results
        feature_textures: dict[str, np.ndarray] = {}
        for path, features in self._extraction_results.items():
            for name, result in features.items():
                if hasattr(result, "arrays") and result.arrays:
                    if "edge_map" in result.arrays and "edge_map" not in feature_textures:
                        feature_textures["edge_map"] = result.arrays["edge_map"]
                    if "depth_map" in result.arrays and "depth_map" not in feature_textures:
                        feature_textures["depth_map"] = result.arrays["depth_map"]

        try:
            self.viewport.init_simulation(
                positions, colors,
                feature_textures if feature_textures else None,
            )
            self.viewport.start_simulation()
            self.simulation_panel.set_simulation_running(True)
            logger.info("Simulation started with %d particles", positions.shape[0])
        except Exception as exc:
            logger.error("Failed to start simulation: %s", exc)

    def _on_pause_toggled(self, paused: bool) -> None:
        """Handle pause/resume toggle from simulation panel."""
        if paused:
            self.viewport.pause_simulation()
        else:
            self.viewport.resume_simulation()

    def _on_performance_mode_changed(self, enabled: bool) -> None:
        """Handle performance mode toggle."""
        if self.viewport._sim_engine:
            self.viewport._sim_engine.set_performance_mode(enabled)

    def _on_sim_param_changed(self, param_name: str, value: float) -> None:
        """Handle simulation parameter change from panel slider.

        Wraps in ParameterChangeCommand for undo support.
        Merge IDs start at 10 (0-2 used by existing rendering sliders).
        """
        param_list = sorted(self.simulation_panel._sliders.keys())
        try:
            offset = 10 + param_list.index(param_name)
        except ValueError:
            offset = 10

        self._push_param_change(param_name, value, offset)

    def _on_section_reset(self, section_name: str) -> None:
        """Handle section reset from simulation panel."""
        logger.info("Section reset: %s", section_name)

    def _on_reset_all_sim(self) -> None:
        """Handle Reset All from simulation panel."""
        logger.info("Reset all simulation parameters")

    def _on_space_pressed(self) -> None:
        """Toggle simulation pause/resume on Space bar."""
        if self.viewport._sim_engine and (
            self.viewport._sim_engine.running or self.viewport._sim_engine.paused
        ):
            self.viewport.toggle_pause()
            is_paused = self.viewport._sim_engine.paused
            self.simulation_panel.btn_pause.setText(
                "Resume" if is_paused else "Pause"
            )

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
