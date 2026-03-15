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

Phase 3 additions:
  - Discovery panel in right sidebar (below simulation)
  - PatchBayEditor as overlay (Ctrl+M toggle)
  - Crossfade widget via preset panel
  - ParameterAnimator in render loop
  - Collection analysis trigger after batch extraction
  - Enrichment service wiring
  - Intelligence menu with keyboard shortcuts

Wiring:
  - Library: load photos -> ingestion worker -> thumbnails in library panel
  - Extract: button triggers ExtractionWorker for all loaded photos
  - Progressive build: each photo_complete adds point cloud to viewport
  - Controls: sliders update viewport in real-time, mode toggles regenerate
  - Simulation: Simulate button -> init engine -> start animation loop
  - Discovery: dimensional sliders -> random walk proposals -> apply to sim
  - Mapping: feature-to-param connections -> MappingEngine evaluation
  - Collection: batch extraction -> CLIP embeddings -> DBSCAN/UMAP -> embedding cloud
  - Enrichment: Claude API toggle -> background worker -> richer descriptions
"""

from __future__ import annotations

import io
import logging
import time
from typing import Any

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QUndoStack

from apollo7.config.settings import (
    CLAUDE_API_KEY,
    DEPTH_EXAGGERATION_DEFAULT,
    ENRICHMENT_ENABLED,
    MIN_WINDOW_SIZE,
    OPACITY_DEFAULT,
    POINT_SIZE_DEFAULT,
    WINDOW_SIZE,
)
from apollo7.gui.widgets.undo_commands import ParameterChangeCommand, ResetSectionCommand
from apollo7.extraction.base import ExtractionResult
from apollo7.extraction.cache import FeatureCache
from apollo7.extraction.clip import ClipExtractor
from apollo7.extraction.color import ColorExtractor
from apollo7.extraction.depth import DepthExtractor
from apollo7.extraction.edges import EdgeExtractor
from apollo7.extraction.pipeline import ExtractionPipeline
from apollo7.config.settings import (
    BLOOM_STRENGTH_DEFAULT,
    DOF_APERTURE_DEFAULT,
    DOF_FOCAL_DEFAULT,
    PROJECT_FILE_EXTENSION,
    SIM_ATTRACTION_DEFAULT,
    SIM_GRAVITY_Y_DEFAULT,
    SIM_NOISE_AMP_DEFAULT,
    SIM_NOISE_FREQ_DEFAULT,
    SIM_NOISE_OCTAVES_DEFAULT,
    SIM_PRESSURE_DEFAULT,
    SIM_REPULSION_DEFAULT,
    SIM_REPULSION_RADIUS_DEFAULT,
    SIM_SPEED_DEFAULT,
    SIM_SURFACE_TENSION_DEFAULT,
    SIM_TURBULENCE_DEFAULT,
    SIM_VISCOSITY_DEFAULT,
    SIM_WIND_DEFAULT,
    SSAO_INTENSITY_DEFAULT,
    SSAO_RADIUS_DEFAULT,
    TRAIL_LENGTH_DEFAULT,
)
from apollo7.gui.panels.controls_panel import ControlsPanel
from apollo7.gui.panels.export_panel import ExportPanel
from apollo7.gui.panels.feature_strip import FeatureStripPanel
from apollo7.gui.panels.feature_viewer import FeatureViewerPanel
from apollo7.gui.panels.library_panel import LibraryPanel
from apollo7.gui.panels.postfx_panel import PostFXPanel
from apollo7.gui.panels.preset_panel import PresetPanel
from apollo7.gui.panels.simulation_panel import SimulationPanel
from apollo7.gui.panels.discovery_panel import DiscoveryPanel
from apollo7.gui.widgets.node_editor import PatchBayEditor
from apollo7.gui.widgets.progress_bar import ExtractionProgressBar
from apollo7.gui.widgets.viewport_widget import ViewportWidget
from apollo7.ingestion.loader import load_image
from apollo7.pointcloud.generator import PointCloudGenerator
from apollo7.project.export import export_image
from apollo7.project.save_load import ProjectState, save_project, load_project
from apollo7.simulation.parameters import SimulationParams
from apollo7.animation.animator import ParameterAnimator
from apollo7.discovery.random_walk import RandomWalk
from apollo7.discovery.dimensional import DimensionalMapper
from apollo7.discovery.history import ProposalHistory, Proposal
from apollo7.mapping.engine import MappingEngine
from apollo7.mapping.connections import MappingGraph
from apollo7.collection.analyzer import CollectionAnalyzer
from apollo7.api.enrichment import EnrichmentService, EnrichmentWorker
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


class _CollectionAnalysisWorker(QtCore.QRunnable):
    """Background worker for collection analysis (DBSCAN + UMAP)."""

    class Signals(QtCore.QObject):
        result_ready = QtCore.Signal(object)  # CollectionResult
        error = QtCore.Signal(str)

    def __init__(self, embeddings: dict[str, np.ndarray]) -> None:
        super().__init__()
        self.signals = self.Signals()
        self.setAutoDelete(True)
        self._embeddings = embeddings

    def run(self) -> None:
        try:
            analyzer = CollectionAnalyzer()
            result = analyzer.analyze(self._embeddings)
            self.signals.result_ready.emit(result)
        except Exception as exc:
            logger.error("Collection analysis failed: %s", exc)
            self.signals.error.emit(str(exc))


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

        # Project file path (None = unsaved new project)
        self._project_path: str | None = None

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
            # Simulation params
            "speed": SIM_SPEED_DEFAULT,
            "turbulence_scale": SIM_TURBULENCE_DEFAULT,
            "noise_frequency": SIM_NOISE_FREQ_DEFAULT,
            "noise_amplitude": SIM_NOISE_AMP_DEFAULT,
            "noise_octaves": float(SIM_NOISE_OCTAVES_DEFAULT),
            "attraction_strength": SIM_ATTRACTION_DEFAULT,
            "repulsion_strength": SIM_REPULSION_DEFAULT,
            "repulsion_radius": SIM_REPULSION_RADIUS_DEFAULT,
            "gravity_y": SIM_GRAVITY_Y_DEFAULT,
            "wind_x": SIM_WIND_DEFAULT,
            "wind_z": SIM_WIND_DEFAULT,
            "viscosity": SIM_VISCOSITY_DEFAULT,
            "pressure_strength": SIM_PRESSURE_DEFAULT,
            "surface_tension": SIM_SURFACE_TENSION_DEFAULT,
        }

        # Extraction pipeline and point cloud generator
        self._pipeline = ExtractionPipeline(
            [ColorExtractor(), EdgeExtractor(), DepthExtractor(), ClipExtractor()]
        )
        self._generator = PointCloudGenerator()

        # --- Phase 3 state ---
        self._mapping_graph = MappingGraph()
        self._mapping_engine = MappingEngine()
        self._random_walk = RandomWalk()
        self._dimensional_mapper = DimensionalMapper()
        self._proposal_history = ProposalHistory()
        self._animator = ParameterAnimator()
        self._enrichment_service = EnrichmentService(
            api_key=CLAUDE_API_KEY,
            enabled=ENRICHMENT_ENABLED,
        )
        self._enrichment_enabled = ENRICHMENT_ENABLED
        self._embedding_cloud_visible = False
        self._current_proposal: dict[str, Any] | None = None
        self._animation_start_time: float = 0.0

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

        # Right side: scrollable panel stack (avoids overlap from splitter)
        self.controls_panel = ControlsPanel()
        self.simulation_panel = SimulationPanel()
        self.postfx_panel = PostFXPanel()
        self.preset_panel = PresetPanel()
        self.export_panel = ExportPanel()
        self.library_panel = LibraryPanel()
        self.discovery_panel = DiscoveryPanel()

        right_container = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        right_layout.addWidget(self.controls_panel)
        right_layout.addWidget(self.simulation_panel)
        right_layout.addWidget(self.discovery_panel)
        right_layout.addWidget(self.postfx_panel)
        right_layout.addWidget(self.preset_panel)
        right_layout.addWidget(self.export_panel)
        right_layout.addWidget(self.library_panel)
        right_layout.addStretch()

        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_container)
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(340)

        h_splitter.addWidget(left_splitter)
        h_splitter.addWidget(right_scroll)
        h_splitter.setSizes([1400, 520])  # ~73% viewport

        main_layout.addWidget(h_splitter)

        # --- Patch bay editor overlay (hidden by default) ---
        self.patch_bay_editor = PatchBayEditor(self)
        self.patch_bay_editor.setVisible(False)

        # --- Initialize post-processing effects ---
        self.viewport.init_postfx()

        # --- Build menus ---
        self._build_intelligence_menu()

        # --- Connect all signals ---
        self._connect_signals()

    def _build_intelligence_menu(self) -> None:
        """Create Intelligence menu with Phase 3 feature toggles."""
        menu_bar = self.menuBar()

        intelligence_menu = menu_bar.addMenu("Intelligence")

        # Discovery mode toggle (Ctrl+D)
        self._act_discovery = QtGui.QAction("Toggle Discovery Mode", self)
        self._act_discovery.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_D))
        self._act_discovery.setCheckable(True)
        self._act_discovery.triggered.connect(self._on_toggle_discovery)
        intelligence_menu.addAction(self._act_discovery)

        # Feature mapping overlay (Ctrl+M)
        self._act_mapping = QtGui.QAction("Open Feature Mapping", self)
        self._act_mapping.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_M))
        self._act_mapping.triggered.connect(self._on_toggle_mapping_editor)
        intelligence_menu.addAction(self._act_mapping)

        intelligence_menu.addSeparator()

        # Embedding cloud toggle (Ctrl+Shift+E to avoid conflict with export Ctrl+E)
        self._act_cloud = QtGui.QAction("Toggle Embedding Cloud", self)
        self._act_cloud.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.SHIFT | QtCore.Qt.Key_E)
        )
        self._act_cloud.setCheckable(True)
        self._act_cloud.triggered.connect(self._on_toggle_embedding_cloud)
        intelligence_menu.addAction(self._act_cloud)

        intelligence_menu.addSeparator()

        # Enhance with AI toggle
        self._act_enrichment = QtGui.QAction("Enhance with AI", self)
        self._act_enrichment.setCheckable(True)
        self._act_enrichment.setChecked(self._enrichment_enabled)
        self._act_enrichment.triggered.connect(self._on_toggle_enrichment)
        intelligence_menu.addAction(self._act_enrichment)

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
        self.simulation_panel.reset_camera_clicked.connect(
            lambda: self.viewport.reset_camera()
        )

        # --- Keyboard shortcuts ---
        # Space: toggle pause/resume simulation
        space_action = QtGui.QAction("Toggle Pause", self)
        space_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space))
        space_action.triggered.connect(self._on_space_pressed)
        self.addAction(space_action)

        # Ctrl+S: save project
        save_action = QtGui.QAction("Save", self)
        save_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_S))
        save_action.triggered.connect(self._on_save_project)
        self.addAction(save_action)

        # Ctrl+O: open project
        open_action = QtGui.QAction("Open", self)
        open_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_O))
        open_action.triggered.connect(self._on_open_project)
        self.addAction(open_action)

        # Ctrl+E: export image
        export_action = QtGui.QAction("Export", self)
        export_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL | QtCore.Qt.Key_E))
        export_action.triggered.connect(
            lambda: self.export_panel._on_export_clicked()
        )
        self.addAction(export_action)

        # --- Export panel signals ---
        self.export_panel.export_requested.connect(self._on_export_image)

        # --- Preset panel signals ---
        self.preset_panel.preset_applied.connect(self._on_preset_applied)
        self.preset_panel.save_current_requested.connect(
            self._on_save_current_preset
        )

        # --- Phase 3: Discovery panel signals ---
        self.discovery_panel.proposal_requested.connect(self._on_discovery_propose)
        self.discovery_panel.proposal_applied.connect(self._on_discovery_apply)
        self.discovery_panel.dimension_changed.connect(self._on_dimension_changed)

        # --- Phase 3: Mapping editor signals ---
        self.patch_bay_editor.mapping_changed.connect(self._on_mapping_changed)
        self.patch_bay_editor.close_requested.connect(
            lambda: self.patch_bay_editor.setVisible(False)
        )

        # --- Phase 3: Enrichment signals ---
        self.feature_viewer.enrichment_requested.connect(self._on_enrichment_requested)

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
        worker.signals.batch_complete.connect(self._on_batch_extraction_complete)

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
        worker.signals.batch_complete.connect(self._on_batch_extraction_complete)

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

        # Re-evaluate mapping graph with new feature data
        self._evaluate_mapping_graph()

    def _on_extraction_error(self, photo_path: str, error_msg: str) -> None:
        """Log extraction errors."""
        logger.error("Extraction failed for %s: %s", photo_path, error_msg)

    def _on_batch_extraction_complete(self, all_results: dict) -> None:
        """Trigger collection analysis after all photos in batch are extracted.

        Gathers CLIP embeddings from extraction results and runs
        CollectionAnalyzer in a background worker.
        """
        embeddings: dict[str, np.ndarray] = {}
        for path, features in all_results.items():
            # Look for CLIP embeddings in the semantic/clip extractor results
            for ext_name, result in features.items():
                if hasattr(result, "data") and isinstance(result.data, dict):
                    embedding = result.data.get("embedding")
                    if embedding is not None and isinstance(embedding, np.ndarray):
                        embeddings[path] = embedding
                        break

        if len(embeddings) < 2:
            logger.info("Not enough embeddings for collection analysis (%d)", len(embeddings))
            return

        logger.info("Starting collection analysis with %d embeddings", len(embeddings))
        worker = _CollectionAnalysisWorker(embeddings)
        worker.signals.result_ready.connect(self._on_collection_analysis_complete)
        worker.signals.error.connect(
            lambda msg: logger.error("Collection analysis error: %s", msg)
        )
        self._thread_pool.start(worker)

    def _on_collection_analysis_complete(self, result: object) -> None:
        """Handle collection analysis results.

        Update embedding cloud in viewport and set attractors in simulation.
        """
        self.viewport.update_embedding_cloud(result)

        # Set force attractors in simulation if running
        if self.viewport._sim_engine and hasattr(result, "cluster_positions_3d"):
            attractors = []
            for cluster_id, pos in result.cluster_positions_3d.items():
                attractors.append((pos, 1.0))
            if attractors:
                self.viewport._sim_engine.set_attractors(attractors)

        logger.info("Collection analysis complete: %d clusters", getattr(result, "n_clusters", 0))

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
            self._animation_start_time = time.monotonic()
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
    # Phase 3: Discovery mode
    # ------------------------------------------------------------------

    def _on_toggle_discovery(self, checked: bool) -> None:
        """Toggle discovery mode via menu action."""
        self.discovery_panel.btn_toggle.setChecked(checked)

    def _on_dimension_changed(self, dim_name: str, value: float) -> None:
        """Handle dimensional slider change in discovery panel."""
        self._dimensional_mapper.set_dimension(dim_name, value)

    def _on_discovery_propose(self) -> None:
        """Generate a new parameter proposal using RandomWalk with dimensional constraints."""
        constraints = self._dimensional_mapper.get_constraints()

        current_params = None
        if self.viewport._sim_engine:
            current_params = self.viewport._sim_engine.params

        proposal_params = self._random_walk.propose(
            constraints=constraints,
            current=current_params,
        )

        # Convert to dict for storage and display
        from dataclasses import fields as dc_fields, asdict
        param_dict: dict[str, Any] = {}
        for f in dc_fields(proposal_params):
            if not f.name.startswith("_") and f.name != "UNIFORM_SIZE":
                val = getattr(proposal_params, f.name)
                if isinstance(val, tuple):
                    val = list(val)
                param_dict[f.name] = val

        self._current_proposal = param_dict

        # Store in history with thumbnail
        thumbnail = None
        try:
            # Capture viewport thumbnail for history strip
            thumbnail = self.viewport.grab().scaled(
                80, 60, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
        except Exception:
            pass

        proposal = Proposal(params=param_dict, thumbnail=thumbnail)
        self._proposal_history.add(proposal)

        # Update history strip in discovery panel
        self.discovery_panel.history_strip.add_proposal(thumbnail)

        logger.info("Discovery proposal generated with %d constrained params", len(constraints))

    def _on_discovery_apply(self, _params: dict) -> None:
        """Apply the current proposal to simulation parameters."""
        if self._current_proposal is None:
            logger.warning("No proposal to apply")
            return

        for name, value in self._current_proposal.items():
            if name in ("gravity", "wind") and isinstance(value, list):
                if self.viewport._sim_engine:
                    self.viewport._sim_engine.update_physics_param(name, tuple(value))
            elif isinstance(value, (int, float)):
                self.viewport.update_sim_param(name, value)

        logger.info("Discovery proposal applied")

    # ------------------------------------------------------------------
    # Phase 3: Feature-to-visual mapping
    # ------------------------------------------------------------------

    def _on_toggle_mapping_editor(self) -> None:
        """Toggle the PatchBayEditor overlay visibility."""
        visible = not self.patch_bay_editor.isVisible()
        self.patch_bay_editor.setVisible(visible)
        if visible:
            # Resize overlay to fill the viewport area
            self.patch_bay_editor.setGeometry(self.centralWidget().rect())
            self.patch_bay_editor.raise_()

    def _on_mapping_changed(self, graph: object) -> None:
        """Handle mapping connection changes from the patch bay editor."""
        if isinstance(graph, MappingGraph):
            self._mapping_graph = graph
            self._evaluate_mapping_graph()

    def _evaluate_mapping_graph(self) -> None:
        """Evaluate current mapping graph against latest feature data and apply results."""
        if not self._mapping_graph.get_connections():
            return
        if not self._extraction_results:
            return

        # Use the first photo's features for evaluation (or selected)
        features = None
        if self._selected_photo and self._selected_photo in self._extraction_results:
            features = self._extraction_results[self._selected_photo]
        elif self._extraction_results:
            features = next(iter(self._extraction_results.values()))

        if features is None:
            return

        try:
            updates = self._mapping_engine.evaluate(self._mapping_graph, features)
            for name, value in updates.items():
                self.viewport.update_sim_param(name, value)
            logger.info("Mapping evaluation applied: %d params updated", len(updates))
        except Exception as exc:
            logger.warning("Mapping evaluation failed: %s", exc)

    # ------------------------------------------------------------------
    # Phase 3: Embedding cloud
    # ------------------------------------------------------------------

    def _on_toggle_embedding_cloud(self, checked: bool) -> None:
        """Toggle embedding cloud visibility in viewport."""
        self._embedding_cloud_visible = checked
        self.viewport.toggle_embedding_cloud()

    # ------------------------------------------------------------------
    # Phase 3: Enrichment service
    # ------------------------------------------------------------------

    def _on_toggle_enrichment(self, checked: bool) -> None:
        """Toggle AI enrichment on/off."""
        self._enrichment_enabled = checked
        self._enrichment_service._enabled = checked
        logger.info("Enrichment %s", "enabled" if checked else "disabled")

    def _on_enrichment_requested(self, image_path: str, tags: list) -> None:
        """Handle enrichment request from feature viewer.

        Launches an EnrichmentWorker in background.
        """
        if not self._enrichment_enabled:
            return

        worker = EnrichmentWorker(
            service=self._enrichment_service,
            image_path=image_path,
            basic_tags=tags,
            mode="enrich",
        )
        worker.signals.enrichment_ready.connect(self.feature_viewer.set_enrichment)
        worker.signals.error.connect(
            lambda msg: logger.warning("Enrichment failed: %s", msg)
        )
        self._thread_pool.start(worker)

    # ------------------------------------------------------------------
    # Phase 3: Animation system
    # ------------------------------------------------------------------

    def tick_animation(self, elapsed: float) -> None:
        """Tick the parameter animator (call from render loop if active).

        Args:
            elapsed: Seconds since animation start.
        """
        if not self._animator.bindings:
            return
        if self.viewport._sim_engine is None:
            return

        params = self.viewport._sim_engine.params
        updated = self._animator.tick(elapsed, params)
        if updated != params:
            self.viewport._sim_engine.params = updated

    # ------------------------------------------------------------------
    # Project save/load
    # ------------------------------------------------------------------

    def _collect_project_state(self) -> ProjectState:
        """Gather all current state into a ProjectState for saving."""
        # Simulation parameters
        sim_params: dict[str, Any] = {}
        if self.viewport._sim_engine:
            params = self.viewport._sim_engine.params
            from dataclasses import fields as dc_fields
            for f in dc_fields(params):
                if not f.name.startswith("_") and f.name != "UNIFORM_SIZE":
                    val = getattr(params, f.name)
                    if isinstance(val, tuple):
                        val = list(val)
                    sim_params[f.name] = val

        # PostFX parameters
        postfx_params: dict[str, Any] = {}
        for name in self._POSTFX_MERGE_IDS:
            postfx_params[name] = self._prev_values.get(name, 0.0)

        # Rendering parameters
        rendering_params = {
            "point_size": self._prev_values.get("point_size", POINT_SIZE_DEFAULT),
            "opacity": self._prev_values.get("opacity", OPACITY_DEFAULT),
            "depth_exaggeration": self._depth_exaggeration,
        }

        # Camera state
        camera_state: dict[str, Any] = {}
        try:
            cam = self.viewport._camera
            pos = cam.world.position
            camera_state["position"] = [float(pos[0]), float(pos[1]), float(pos[2])]
            rot = cam.world.rotation
            camera_state["rotation"] = [float(rot[0]), float(rot[1]), float(rot[2]), float(rot[3])]
        except Exception:
            pass

        # Point cloud snapshot (positions + colors from first cloud)
        snapshot = None
        if self.viewport._point_objects:
            try:
                pts = self.viewport._point_objects[0]
                geo = pts.geometry
                if geo.positions is not None and geo.colors is not None:
                    snapshot = {
                        "positions": geo.positions.data.tolist(),
                        "colors": geo.colors.data.tolist(),
                    }
            except Exception:
                pass

        # Phase 3 state
        mapping_graph_dict = self._mapping_graph.to_dict() if self._mapping_graph.get_connections() else None
        discovery_dims = self.discovery_panel.get_dimension_values()

        return ProjectState(
            photo_paths=list(self._photo_paths),
            sim_params=sim_params,
            postfx_params=postfx_params,
            rendering_params=rendering_params,
            camera_state=camera_state,
            layout_mode=self.viewport.layout_mode,
            multi_photo_mode=self.viewport.multi_photo_mode,
            depth_exaggeration=self._depth_exaggeration,
            point_cloud_snapshot=snapshot,
            mapping_graph=mapping_graph_dict,
            discovery_dimensions=discovery_dims,
            enrichment_enabled=self._enrichment_enabled,
        )

    def _on_save_project(self) -> None:
        """Save the current project to file."""
        if self._project_path:
            # Save to existing path
            state = self._collect_project_state()
            save_project(state, self._project_path)
            logger.info("Project saved to %s", self._project_path)
        else:
            # New project -- open save dialog
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Project", "",
                f"Apollo 7 Project (*{PROJECT_FILE_EXTENSION})",
            )
            if not path:
                return
            if not path.endswith(PROJECT_FILE_EXTENSION):
                path += PROJECT_FILE_EXTENSION
            self._project_path = path
            state = self._collect_project_state()
            save_project(state, path)
            self.setWindowTitle(f"Apollo 7 - {path}")

    def _on_open_project(self) -> None:
        """Open a project file and restore all state."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Project", "",
            f"Apollo 7 Project (*{PROJECT_FILE_EXTENSION})",
        )
        if not path:
            return

        try:
            state = load_project(path)
        except Exception as exc:
            logger.error("Failed to load project: %s", exc)
            QtWidgets.QMessageBox.warning(
                self, "Load Error", f"Failed to load project:\n{exc}"
            )
            return

        self._project_path = path
        self.setWindowTitle(f"Apollo 7 - {path}")

        # Restore photo paths (load images that still exist)
        self._photo_paths.clear()
        self._loaded_images.clear()
        for p in state.photo_paths:
            import os
            if os.path.exists(p):
                try:
                    image = load_image(p)
                    self._loaded_images[p] = image
                    self._photo_paths.append(p)
                except Exception as exc:
                    logger.warning("Failed to load photo %s: %s", p, exc)
            else:
                logger.warning("Photo not found, skipping: %s", p)
                self._photo_paths.append(p)  # Keep reference

        # Restore rendering params
        rp = state.rendering_params
        if "point_size" in rp:
            self.viewport.update_point_material(point_size=rp["point_size"])
            self._prev_values["point_size"] = rp["point_size"]
        if "opacity" in rp:
            self.viewport.update_point_material(opacity=rp["opacity"])
            self._prev_values["opacity"] = rp["opacity"]
        if "depth_exaggeration" in rp:
            self._depth_exaggeration = rp["depth_exaggeration"]
            self._prev_values["depth_exaggeration"] = rp["depth_exaggeration"]

        # Restore layout mode
        if state.layout_mode != self.viewport.layout_mode:
            self.viewport._layout_mode = state.layout_mode

        # Restore point cloud from snapshot if available
        if state.point_cloud_snapshot:
            try:
                positions = np.array(
                    state.point_cloud_snapshot["positions"], dtype=np.float32
                )
                colors = np.array(
                    state.point_cloud_snapshot["colors"], dtype=np.float32
                )
                sizes = np.full(len(positions), POINT_SIZE_DEFAULT, dtype=np.float32)
                self.viewport.add_photo_cloud(
                    photo_id="__snapshot__",
                    positions=positions,
                    colors=colors,
                    sizes=sizes,
                )
            except Exception as exc:
                logger.warning("Failed to restore point cloud snapshot: %s", exc)

        # Restore Phase 3 state
        if state.mapping_graph:
            try:
                self._mapping_graph = MappingGraph.from_dict(state.mapping_graph)
            except Exception as exc:
                logger.warning("Failed to restore mapping graph: %s", exc)

        if state.discovery_dimensions:
            self.discovery_panel.set_dimension_values(state.discovery_dimensions)
            for dim_name, value in state.discovery_dimensions.items():
                self._dimensional_mapper.set_dimension(dim_name, value)

        self._enrichment_enabled = state.enrichment_enabled
        self._enrichment_service._enabled = state.enrichment_enabled
        self._act_enrichment.setChecked(state.enrichment_enabled)

        logger.info("Project loaded from %s", path)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export_image(
        self, width: int, height: int, transparent: bool, output_path: str
    ) -> None:
        """Handle export request from ExportPanel."""
        try:
            export_image(
                scene=self.viewport._scene,
                camera=self.viewport._camera,
                width=width,
                height=height,
                output_path=output_path,
                transparent=transparent,
            )
            logger.info("Export complete: %s (%dx%d)", output_path, width, height)
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            QtWidgets.QMessageBox.warning(
                self, "Export Error", f"Export failed:\n{exc}"
            )

    # ------------------------------------------------------------------
    # Preset integration
    # ------------------------------------------------------------------

    def _on_preset_applied(
        self, sim_params: dict, postfx_params: dict
    ) -> None:
        """Apply a loaded preset to simulation and post-processing parameters."""
        # Apply sim params to viewport
        for name, value in sim_params.items():
            if name in ("gravity", "wind") and isinstance(value, list):
                # Compound params: apply via viewport
                if self.viewport._sim_engine:
                    self.viewport._sim_engine.update_physics_param(name, tuple(value))
            else:
                self.viewport.update_sim_param(name, value)

        # Apply postfx params
        for name, value in postfx_params.items():
            self.viewport.update_postfx_param(name, value)

        # Push compound undo for the whole preset application
        logger.info("Preset applied: %d sim params, %d postfx params",
                     len(sim_params), len(postfx_params))

    def _on_save_current_preset(self) -> None:
        """Collect current params and show save preset dialog."""
        sim_params: dict[str, Any] = {}
        if self.viewport._sim_engine:
            params = self.viewport._sim_engine.params
            from dataclasses import fields as dc_fields
            for f in dc_fields(params):
                if not f.name.startswith("_") and f.name != "UNIFORM_SIZE":
                    val = getattr(params, f.name)
                    if isinstance(val, tuple):
                        val = list(val)
                    sim_params[f.name] = val

        postfx_params: dict[str, Any] = {}
        for name in self._POSTFX_MERGE_IDS:
            postfx_params[name] = self._prev_values.get(name, 0.0)

        self.preset_panel.save_preset_dialog(sim_params, postfx_params)

    # ------------------------------------------------------------------
    # Overlay resize handling
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        """Resize the patch bay overlay when the window resizes."""
        super().resizeEvent(event)
        if self.patch_bay_editor.isVisible():
            self.patch_bay_editor.setGeometry(self.centralWidget().rect())

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
