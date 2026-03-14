---
phase: 01-pipeline-foundation
verified: 2026-03-14T16:30:00Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Launch the app and confirm dark theme, 3D viewport, orbit/zoom/pan, and overall visual quality"
    expected: "Dark-themed window with electric blue accents, 3D viewport loads, camera controls work smoothly"
    why_human: "Visual aesthetics, interaction smoothness, and 30+ FPS cannot be verified programmatically in a headless environment"
  - test: "Load a folder of 3-5 photos via Load Folder button, then click Extract Features"
    expected: "Thumbnails appear in library panel progressively; progress bar shows 'Processing X/Y photos...'; point cloud grows in viewport as each photo completes"
    why_human: "End-to-end GUI flow with real file I/O and progressive UI updates requires human observation"
  - test: "Click a photo thumbnail after extraction, check feature strip"
    expected: "Feature strip at bottom shows Color Palette (swatches), Edge Map (grayscale thumb), and Depth Map (blue-yellow heatmap) cards"
    why_human: "Visual feature card rendering can only be confirmed by human inspection"
  - test: "Move the Point Size, Opacity, and Depth Exaggeration sliders"
    expected: "Viewport updates in real-time — points grow/shrink, become transparent, sculpture stretches/compresses"
    why_human: "Real-time parameter binding effectiveness requires human observation of frame-by-frame responsiveness"
  - test: "Toggle Layout Mode to Feature-clustered and Multi-photo Mode to Merged"
    expected: "Viewport clears and regenerates with new layout; no UI freeze during regeneration"
    why_human: "Mode-switch correctness and UI responsiveness during regeneration require human observation"
---

# Phase 1: Pipeline Foundation Verification Report

**Phase Goal:** User can load photos, see extracted features, and explore a 3D point cloud sculpture in a real-time desktop viewport
**Verified:** 2026-03-14T16:30:00Z
**Status:** human_needed (all automated checks PASSED — 5 human items pending)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can drag-drop or browse to load a single photo or a folder of photos, with progress feedback during batch ingestion | VERIFIED | `LibraryPanel` has `btn_load_photo` and `btn_load_folder` wired in `main_window.py`; `IngestionWorker(QRunnable)` runs background loading; `ExtractionProgressBar.update(current, total)` fires per photo |
| 2 | User can view extracted color palettes, edge maps, and depth maps for any ingested photo | VERIFIED | `FeatureStripPanel.update_features()` creates `ColorPaletteCard`, `EdgeMapCard`, `DepthMapCard` from `ExtractionResult`; triggered via `photo_selected` signal and `photo_complete` in `main_window.py` |
| 3 | User sees a 3D point cloud generated from extracted features, rendered in a real-time viewport with orbit, zoom, and pan at 30+ FPS | VERIFIED (automated) / HUMAN PENDING (FPS) | `ViewportWidget` uses `QRenderWidget(update_mode="continuous")` + `WgpuRenderer`; `OrbitController` registered to renderer; `add_photo_cloud()` wired to `ExtractionWorker.photo_complete`; 30+ FPS requires human confirmation |
| 4 | Point cloud rendering supports configurable point size, color mapping, opacity, and additive blending | VERIFIED | `ControlsPanel` sliders emit `point_size_changed`, `opacity_changed`, connected to `viewport.update_point_material()`; `PointsGaussianBlobMaterial(color_mode="vertex", size_mode="vertex")`; BLEND_MODE_AVAILABLE=False with documented alpha=0.7 falloff |
| 5 | Application runs on Windows 11 with AMD RX 9060 XT (no CUDA), UI stays responsive during long extraction runs | VERIFIED (no CUDA) / HUMAN PENDING (responsiveness) | Zero CUDA references found in codebase; wgpu uses DX12/Vulkan; all extraction via `QThreadPool`; UI responsiveness during long runs requires human observation |

**Score:** 5/5 truths structurally verified. 5 human items pending for behavioral confirmation.

---

### Required Artifacts

#### Plan 01-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Project config with dependencies | VERIFIED | Contains pygfx, PySide6, wgpu, onnxruntime-directml, etc. Note: pin says `>=0.6` but installed and correct version is 0.16.0 — minor spec discrepancy, not a blocker |
| `apollo7/gui/main_window.py` | Main window with splitter layout, min 40 lines | VERIFIED | 441 lines; full splitter layout, all panels wired |
| `apollo7/gui/theme.py` | Dark QSS theme with electric blue accent #0078FF | VERIFIED | Contains `accent = "#0078FF"`, comprehensive QSS covering buttons, sliders, radio buttons, scrollbars, group boxes |
| `apollo7/gui/widgets/viewport_widget.py` | pygfx viewport embedded in Qt, min 30 lines | VERIFIED | 275 lines; `QRenderWidget` embedding, `WgpuRenderer`, `gfx.Scene`, full point cloud API |
| `apollo7/rendering/camera.py` | OrbitController wrapper with auto-frame | VERIFIED | Contains `gfx.OrbitController`, `set_three_quarter_view()`, `auto_frame()` |

#### Plan 01-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apollo7/ingestion/loader.py` | Image loading, exports load_image, load_folder | VERIFIED | Both functions present and substantive; header-based format detection via Pillow; float32 [0,1] output |
| `apollo7/ingestion/thumbnailer.py` | Thumbnail generation, exports generate_thumbnail | VERIFIED | Present, uses LANCZOS resampling, aspect ratio preserved |
| `apollo7/gui/panels/library_panel.py` | Photo grid with thumbnails, min 50 lines | VERIFIED | 118 lines; 2-column scrollable grid, `photo_selected` signal, `add_photo()` method |
| `apollo7/workers/ingestion_worker.py` | Background ingestion via QRunnable | VERIFIED | Contains `QRunnable`, `WorkerSignals`, emits `photo_loaded`, `progress`, `finished`, `error` |

#### Plan 01-03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apollo7/extraction/base.py` | Abstract extractor interface, exports BaseExtractor, ExtractionResult | VERIFIED | Both classes present; `ExtractionResult` dataclass with `data` + `arrays` dicts; `BaseExtractor` ABC |
| `apollo7/extraction/color.py` | Color extraction, exports ColorExtractor | VERIFIED | `ColorExtractor(BaseExtractor)`, uses extcolors + numpy histogram; confirmed live: 12 dominant colors + (256,3) histogram from test image |
| `apollo7/extraction/edges.py` | Edge extraction, exports EdgeExtractor | VERIFIED | `EdgeExtractor(BaseExtractor)`, Canny + findContours; confirmed live: (50,50) edge map, 71 contours from test image |
| `apollo7/extraction/cache.py` | Feature caching, exports FeatureCache | VERIFIED | `get/store/invalidate/clear` API; confirmed live: cache hit and invalidation work |
| `apollo7/gui/panels/feature_strip.py` | Bottom strip showing feature thumbnails, min 40 lines | VERIFIED | 296 lines; `ColorPaletteCard`, `EdgeMapCard`, `DepthMapCard`, horizontal scrollable layout, collapse toggle |

#### Plan 01-04 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apollo7/extraction/depth.py` | Depth Anything V2 ONNX inference, exports DepthExtractor | VERIFIED | `DepthExtractor(BaseExtractor)`, lazy ONNX loading, ImageNet normalization, DirectML/CPU fallback, bilinear resize, [0,1] normalization |
| `apollo7/extraction/pipeline.py` | Extraction orchestrator, exports ExtractionPipeline | VERIFIED | Cache-first sequential orchestration; runs extractors in configured order |
| `apollo7/pointcloud/generator.py` | Point cloud generation facade, exports PointCloudGenerator | VERIFIED | Delegates to depth_projected/feature_clustered; auto LOD at 5M point budget |
| `apollo7/pointcloud/depth_projection.py` | Depth-projected layout, exports generate_depth_projected_cloud | VERIFIED | Full pixel density confirmed live: 20x20 image = 400 points (N=H*W); correct (N,3) positions, (N,4) colors |
| `apollo7/pointcloud/feature_cluster.py` | Feature-clustered layout, exports generate_feature_clustered_cloud | VERIFIED | Color-similarity grouping, downsampled pixels, scatter around cluster centers in 3D |
| `apollo7/pointcloud/lod.py` | LOD decimation, exports decimate_points | VERIFIED | Grid-based spatial decimation confirmed live: 400 → 119 points at factor=0.5 |

#### Plan 01-05 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apollo7/workers/extraction_worker.py` | Background extraction + point cloud generation worker, contains QRunnable | VERIFIED | `ExtractionWorker(QRunnable)`, `WorkerSignals` with `photo_complete`, `progress`, `finished`, `error`; runs pipeline + generator in background |
| `apollo7/gui/main_window.py` | Full end-to-end wiring, min 100 lines | VERIFIED | 441 lines; all signals wired: ingestion → thumbnails, extract → progressive build, sliders → viewport, layout toggles → regeneration |

---

### Key Link Verification

#### Plan 01-01 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `main_window.py` | `viewport_widget.py` | ViewportWidget embedding in splitter | VERIFIED | `self.viewport = ViewportWidget()` at line 113; added to `left_splitter` |
| `viewport_widget.py` | `camera.py` | OrbitController integration | VERIFIED | `self._camera_controller = CameraController(self._camera, self._renderer)` at line 69-71 |
| `app.py` | `main_window.py` | QApplication bootstrap | VERIFIED | `from apollo7.gui.main_window import MainWindow; window = MainWindow(); window.show()` |

#### Plan 01-02 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `library_panel.py` | `loader.py` | load_image/load_folder calls | NOT DIRECTLY WIRED (by design) | LibraryPanel does not call loader directly — this is delegated to `IngestionWorker` and `main_window.py`. The panel only emits signals. This is correct architecture, not a gap. |
| `ingestion_worker.py` | `loader.py` | background loading | VERIFIED | `from apollo7.ingestion.loader import SUPPORTED_EXTENSIONS, load_image` at line 16; called in `run()` |
| `main_window.py` | `library_panel.py` | replacing placeholder panel | VERIFIED | `self.library_panel = LibraryPanel()` at line 123; `btn_load_photo.clicked.connect(self._on_load_photo)` |

#### Plan 01-03 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `color.py` | `base.py` | implements BaseExtractor | VERIFIED | `class ColorExtractor(BaseExtractor)` |
| `edges.py` | `base.py` | implements BaseExtractor | VERIFIED | `class EdgeExtractor(BaseExtractor)` |
| `feature_strip.py` | `base.py` | displays ExtractionResult data | VERIFIED | `from apollo7.extraction.base import ExtractionResult` (TYPE_CHECKING); `result.data.get(...)` and `result.arrays.get(...)` used in card constructors |

#### Plan 01-04 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `depth.py` | `base.py` | implements BaseExtractor | VERIFIED | `class DepthExtractor(BaseExtractor)` |
| `pipeline.py` | `base.py` | orchestrates extractors | VERIFIED | `from apollo7.extraction.base import BaseExtractor, ExtractionResult`; type-annotated `list[BaseExtractor]` |
| `depth_projection.py` | `base.py` | consumes ExtractionResult arrays | VERIFIED | `depth_map` parameter received from `features.get("depth").arrays["depth_map"]` in generator.py |
| `generator.py` | `depth_projection.py` | delegates to layout mode | VERIFIED | `from apollo7.pointcloud.depth_projection import generate_depth_projected_cloud`; called on mode=="depth_projected" |

#### Plan 01-05 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `extraction_worker.py` | `pipeline.py` | runs pipeline in background | VERIFIED | `features = self._pipeline.run(image, path, cache=self._cache)` in `run()` |
| `extraction_worker.py` | `generator.py` | generates point cloud from features | VERIFIED | `positions, colors, sizes = self._generator.generate(image, features, mode=self._mode, **kwargs)` |
| `main_window.py` | `viewport_widget.py` | adds generated points to viewport | VERIFIED | `self.viewport.add_photo_cloud(photo_id=photo_path, positions=positions, ...)` in `_on_extraction_photo_complete()` |
| `controls_panel.py` | `viewport_widget.py` | controls update viewport parameters | VERIFIED | `controls_panel.point_size_changed.connect(lambda v: self.viewport.update_point_material(point_size=v))` in `_connect_signals()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| INGEST-01 | 01-02 | User can load a single photo (JPEG, PNG, TIFF) | SATISFIED | `load_image()` with Pillow header detection; `btn_load_photo` opens file dialog wired to `IngestionWorker` |
| INGEST-02 | 01-02 | User can batch-ingest a folder with progress feedback | SATISFIED | `load_folder()` + `IngestionWorker` + `ExtractionProgressBar.update(current, total)` |
| INGEST-03 | 01-02 | User can view thumbnails and metadata in library panel | SATISFIED | `LibraryPanel.add_photo(path, pixmap, metadata)` populates 2-column scrollable grid |
| EXTRACT-01 | 01-03 | Pipeline extracts dominant colors, gradients, color distributions | SATISFIED | `ColorExtractor`: extcolors dominant colors + numpy per-channel histogram; confirmed live |
| EXTRACT-02 | 01-03 | Pipeline extracts edges, contours, geometric structure | SATISFIED | `EdgeExtractor`: OpenCV Canny + findContours; confirmed live |
| EXTRACT-03 | 01-04 | Pipeline generates monocular depth maps via Depth Anything V2 (ONNX/DirectML) | SATISFIED | `DepthExtractor`: lazy ONNX session, DirectML/CPU fallback, ImageNet normalization, bilinear resize. Note: ONNX model file must be separately downloaded. |
| RENDER-01 | 01-04 | Pipeline generates 3D point clouds from extracted features | SATISFIED | `generate_depth_projected_cloud` (full pixel density, N=H*W) and `generate_feature_clustered_cloud`; confirmed live |
| RENDER-02 | 01-01 | Real-time 3D viewport with orbit, zoom, pan at 30+ FPS via Vulkan/wgpu | SATISFIED (automated) / HUMAN PENDING (FPS) | `QRenderWidget(update_mode="continuous")` + `WgpuRenderer` + `OrbitController` |
| RENDER-03 | 01-01, 01-05 | Point cloud with configurable size, color mapping, opacity, additive blending | SATISFIED | `PointsGaussianBlobMaterial(color_mode="vertex", size_mode="vertex")`; sliders wired; BLEND_MODE_AVAILABLE=False with alpha=0.7 falloff workaround documented |
| APP-01 | 01-01 | Desktop GUI with PySide6 — professional layout with docking panels | SATISFIED | `QMainWindow` with horizontal/vertical `QSplitter` layout; panel structure with controls, library, viewport, feature strip |
| APP-02 | 01-01 | Runs on Windows 11 with AMD RX 9060 XT — no CUDA dependencies | SATISFIED | Zero CUDA references in codebase; wgpu uses DX12/Vulkan; onnxruntime-directml for AMD GPU |
| APP-03 | 01-05 | Full GPU/CPU/RAM utilization for generation (hours-long runs acceptable) | SATISFIED | `QThreadPool` with unlimited workers; extraction + point cloud generation fully offloaded; LOD manages memory |
| APP-04 | 01-05 | UI remains responsive during long generation runs | SATISFIED (architecture) / HUMAN PENDING (feel) | All extraction in `QRunnable`; pygfx scene modifications queued to main thread; no blocking calls in main thread |

**Orphaned Requirements Check:** All 13 Phase 1 requirement IDs (INGEST-01 through INGEST-03, EXTRACT-01 through EXTRACT-03, RENDER-01 through RENDER-03, APP-01 through APP-04) appear in plan frontmatter and are covered. No orphans.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pyproject.toml` | 8 | `pygfx>=0.6` should be `>=0.16` per plan spec | Info | Installed version (0.16.0) satisfies the requirement — version constraint is underspecified but not broken |
| `viewport_widget.py` | 273 | `pass` in `except ValueError` for empty scene auto_frame | Info | Intentional guard against empty bounding sphere error — documented in code comment. Not a stub. |
| `camera.py` | 55-57 | `pass` in `except (AttributeError, TypeError)` for three-quarter view | Info | Graceful fallback when OrbitController doesn't expose azimuth/elevation — acceptable defensive coding |
| `main_window.py` | 53-62 | `_make_placeholder()` function defined but never called | Info | Dead code — placeholder function was superseded when real panels replaced placeholders. No functional impact. |

No blockers or warnings found. All four items are informational.

---

### Human Verification Required

#### 1. Visual Quality and Dark Theme

**Test:** Run `python -m apollo7` from the project root
**Expected:** Dark-themed window appears (not stock Qt gray), electric blue accent visible on buttons/sliders/group box titles, Segoe UI font, window 1920x1080 with viewport-dominant left side (~73%) and control panels on right (~27%)
**Why human:** Visual aesthetics cannot be programmatically verified

#### 2. 3D Viewport and Camera Controls

**Test:** After launching, observe the viewport
**Expected:** Dark gradient background visible; orbit via left-click-drag, zoom via scroll wheel, pan via right-click-drag all work smoothly; rendering feels fluid without visible stutter
**Why human:** Interaction smoothness and 30+ FPS require human perception

#### 3. End-to-End Photo Loading and Point Cloud Generation

**Test:** Click "Load Folder", select 3-5 JPEGs; then click "Extract Features"
**Expected:** Thumbnails appear progressively in library panel with "X photos loaded" counter; progress bar shows "Processing X/Y photos..."; point cloud grows in viewport as each photo completes (progressive build); camera auto-frames with three-quarter view
**Why human:** Progressive GUI updates and visual sculpture emergence require human observation

#### 4. Feature Strip Visual Cards

**Test:** Click a photo thumbnail in the library after extraction
**Expected:** Feature strip at bottom shows three cards left-to-right: Color Palette (colored swatches on dark cards), Edge Map (grayscale edge thumbnail), Depth Map (blue-to-yellow heatmap). Depth card shows "Available after depth extraction" if model file is absent.
**Why human:** Visual card rendering quality requires human inspection

#### 5. Real-Time Controls

**Test:** Move Point Size slider (0.5–10.0), Opacity slider (0–1.0), Depth Exaggeration slider (1x–10x); toggle Layout Mode and Multi-photo Mode radio buttons
**Expected:** Point size and opacity change instantly in the viewport; depth exaggeration slider triggers cloud regeneration with new sculpture shape; layout/multi-photo mode switches clear and rebuild the cloud
**Why human:** Real-time parameter binding effectiveness and regeneration correctness require human observation of the running application

---

### Notes

**Depth model download required:** `apollo7/extraction/depth.py` requires `models/depth_anything_v2_vits.onnx` to be present for depth extraction. Without it, `DepthExtractor._ensure_session()` raises `FileNotFoundError` with a descriptive download URL. Color and edge extraction work without the model. The `ExtractionWorker` catches this gracefully (`cloud_data = None`) and continues with other photos.

**Blending workaround:** `BLEND_MODE_AVAILABLE = False` is documented and intentional. pygfx 0.16's `PointsGaussianBlobMaterial` does not expose a `blend_mode` parameter. The alpha=0.7 falloff combined with Gaussian blob material creates soft overlap glow. This is fully acceptable for Phase 1 per the plan's contingency path.

---

## Gaps Summary

No automated gaps found. All 13 Phase 1 requirements are satisfied by substantive, non-stub implementations. All key links between components are wired and verified. The pipeline delivers the complete described flow:

```
Load Photo/Folder
  -> IngestionWorker (background)
  -> LibraryPanel thumbnails + full image in memory
  -> Extract Features button
  -> ExtractionWorker (background)
     -> ExtractionPipeline (color -> edge -> depth)
     -> PointCloudGenerator.generate()
  -> ViewportWidget.add_photo_cloud() (main thread)
  -> FeatureStripPanel.update_features()
  -> ControlsPanel sliders -> ViewportWidget.update_point_material()
```

Five items require human confirmation (visual quality, interaction smoothness, FPS, progressive build experience, real-time controls feel). These cannot be verified in a headless environment.

---

_Verified: 2026-03-14T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
