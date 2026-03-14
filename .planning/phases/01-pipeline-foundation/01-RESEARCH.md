# Phase 1: Pipeline Foundation - Research

**Researched:** 2026-03-14
**Domain:** Photo ingestion, feature extraction (color/edges/depth), 3D point cloud rendering, PySide6 desktop GUI
**Confidence:** MEDIUM-HIGH (individual components well-documented; their integration is bespoke but patterns are clear)

## Summary

Phase 1 delivers the end-to-end pipeline: load photos, extract visual features (color, edges, depth), generate 3D point clouds, and render them in an interactive viewport inside a PySide6 desktop GUI. The core technical risks are (1) PySide6 + pygfx/wgpu integration for embedding a real-time 3D viewport inside Qt, (2) Depth Anything V2 ONNX inference on AMD via DirectML, and (3) rendering 12M+ points (full pixel density from a 12MP photo) at 30+ FPS with Gaussian blob material.

pygfx provides `PointsGaussianBlobMaterial` natively -- this is the exact material needed for Anadol-style soft glowing points. The `OrbitController` provides click-drag orbit, scroll zoom, and right-click pan out of the box. rendercanvas provides `QRenderWidget` for embedding pygfx into PySide6 layouts. Depth Anything V2 has pre-built ONNX exports (opset 17, dynamic shapes) that run on ONNX Runtime with DirectML for AMD GPU acceleration.

**Primary recommendation:** Build in vertical slices: (1) skeleton GUI with embedded viewport showing test points, (2) photo ingestion + library panel, (3) color + edge extraction with feature viewer, (4) depth extraction via ONNX/DirectML, (5) point cloud generation from features, (6) progressive build + LOD.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Orbit-centric camera: click-drag to rotate around sculpture center, scroll to zoom. No free-fly mode.
- Dark gradient background (subtle dark gray to black) -- not pure black
- Self-illuminated points: points emit their own color, no external lighting. Pure data glow aesthetic.
- Auto-frame on sculpture load: camera automatically positions to show full sculpture, then user takes over
- Default three-quarter view angle to immediately reveal the 3D depth effect
- Target 30+ FPS minimum with orbit controls
- Two spatial layout modes: Depth-projected (default) and Feature-clustered
- Full pixel density: every pixel becomes a point (12MP photo = 12M points)
- Original pixel colors: points retain the photo's actual colors
- Depth exaggeration: 3-5x amplification by default for dramatic sculptural effect
- Round soft particles: Gaussian-blurred circles for organic, glowing Anadol-style look
- Multi-photo handling: Stacked layers (default) + Merged cloud toggle
- LOD (level-of-detail) system for scaling to thousands of photos
- Viewport-dominant layout: 3D viewport takes 70%+ of screen
- Right side panel split: controls on top, photo library below
- Collapsible bottom strip: feature viewer showing extracted data as thumbnail cards
- Dark theme only -- no light mode
- Visual identity: Maya x Unreal Engine x modern SaaS
- Custom-styled Qt widgets, not stock PySide6 defaults
- Electric blue accent color for interactive elements
- GUI must be polished and visually refined -- the app itself should look premium
- Overall pipeline progress bar: "Processing 47/200 photos..."
- Progressive viewport build: point cloud grows in real-time as each photo completes extraction
- Extraction order: color first, then edges, then depth
- Re-extractable: user can re-run extraction with different settings
- Feature results cached after extraction

### Claude's Discretion
- Photo library panel design (grid thumbnails vs list -- pick what suits the thin right panel best)
- Exact point size defaults and ranges
- LOD distance thresholds and simplification strategy
- Feature clustering algorithm for the alternative spatial mode
- Error handling for unsupported image formats
- Keyboard shortcuts for camera controls

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INGEST-01 | Load single photo (JPEG, PNG, TIFF, RAW) | OpenCV `imread` + Pillow for RAW/TIFF; validation via file header checks |
| INGEST-02 | Batch-ingest folder with progress feedback | QThreadPool workers + Qt signals for progress; sequential queue processing |
| INGEST-03 | View thumbnails and metadata in library panel | Pillow thumbnail generation; EXIF via Pillow; grid layout in right panel |
| EXTRACT-01 | Extract dominant colors, gradients, color distributions | extcolors for palette; OpenCV histograms; numpy for distributions |
| EXTRACT-02 | Extract edges, contours, geometric structure | OpenCV Canny/Sobel edge detection; contour finding |
| EXTRACT-03 | Generate monocular depth maps via Depth Anything V2 (ONNX/DirectML) | Depth-Anything-ONNX exports (opset 17); onnxruntime-directml provider |
| RENDER-01 | Generate 3D point clouds from extracted features | numpy arrays for positions/colors; depth-projected + feature-clustered modes |
| RENDER-02 | Real-time 3D viewport with orbit/zoom/pan at 30+ FPS | pygfx + wgpu via rendercanvas QRenderWidget; OrbitController |
| RENDER-03 | Point cloud rendering with configurable size, color mapping, opacity, additive blending | PointsGaussianBlobMaterial for soft particles; per-vertex colors/sizes |
| APP-01 | Desktop GUI with PySide6 -- professional layout with docking panels | PySide6 QMainWindow with QSplitter layout; custom QSS dark theme |
| APP-02 | Runs on Windows 11 with AMD RX 9060 XT -- no CUDA | wgpu uses Vulkan/DX12; ONNX Runtime uses DirectML; no CUDA anywhere |
| APP-03 | Full GPU/CPU/RAM utilization for generation | QThreadPool for CPU extraction; DirectML for GPU inference; wgpu for rendering |
| APP-04 | UI remains responsive during long generation runs | QRunnable workers in QThreadPool; signals for progress/completion; main thread stays free |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Required by ROCm wheels; all other deps support 3.12 |
| PySide6 | 6.8+ | Desktop GUI framework | Official Qt 6 bindings; LGPL; dockable panels, signals/slots, QSS styling |
| pygfx | 0.16.0 | 3D rendering engine | Built on wgpu (WebGPU); GPU-vendor-agnostic; has PointsGaussianBlobMaterial, OrbitController |
| wgpu-py | 0.31.0 | WebGPU bindings | Low-level GPU access; Vulkan/DX12 backend; used by pygfx internally |
| rendercanvas | 2.6.3 | Canvas abstraction | QRenderWidget for embedding pygfx viewports in PySide6 layouts |
| OpenCV (headless) | 4.10+ | Image processing | Edge detection (Canny, Sobel), contours, histograms, image I/O |
| Pillow | 11+ | Image I/O, thumbnails | Loading, resizing, EXIF extraction, thumbnail generation |
| onnxruntime-directml | 1.21+ | GPU ML inference | DirectML execution provider for AMD GPU; runs Depth Anything V2 ONNX |
| NumPy | 2.1+ | Array operations | Point cloud data, feature vectors, GPU buffer preparation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| extcolors | latest | Color palette extraction | Dominant color extraction from images; CIE76 color grouping |
| SciPy | 1.14+ | Spatial algorithms | KD-trees for LOD decimation; feature clustering |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extcolors | sklearn KMeans on pixel colors | More control but more code; extcolors handles color grouping automatically |
| Custom QSS | qt-material / PyQtDarkTheme | Pre-built themes don't match Maya x Unreal aesthetic; custom QSS gives full control |
| QThreadPool | multiprocessing | QThreadPool integrates with Qt signals natively; multiprocessing needed only if GIL becomes a bottleneck for CPU-bound work |

**Installation:**
```bash
# Create environment
conda create -n apollo7 python=3.12
conda activate apollo7

# GUI + Rendering
pip install PySide6 pygfx rendercanvas

# Image Processing
pip install opencv-python-headless Pillow extcolors

# ML Inference (AMD GPU)
pip install onnxruntime-directml

# Utilities
pip install numpy scipy

# Dev tools
pip install pytest ruff
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)

```
apollo7/
    __main__.py              # Entry point: python -m apollo7
    app.py                   # QApplication bootstrap, main window creation

    ingestion/
        __init__.py
        loader.py            # Single + batch image loading, validation
        thumbnailer.py       # Thumbnail generation (Pillow)
        metadata.py          # EXIF extraction

    extraction/
        __init__.py
        base.py              # Abstract extractor interface
        color.py             # Palette, histogram, gradient extraction
        edges.py             # Canny/Sobel edge detection, contours
        depth.py             # Depth Anything V2 ONNX inference
        pipeline.py          # Orchestrates extractors in sequence
        cache.py             # Feature caching (skip re-extraction)

    pointcloud/
        __init__.py
        generator.py         # Feature data -> point positions/colors/sizes
        depth_projection.py  # Depth-projected layout mode
        feature_cluster.py   # Feature-clustered layout mode
        lod.py               # Level-of-detail decimation

    rendering/
        __init__.py
        viewport.py          # pygfx scene setup, renderer configuration
        camera.py            # OrbitController wrapper, auto-frame, default view angle

    gui/
        __init__.py
        main_window.py       # QMainWindow with splitter layout
        theme.py             # QSS dark theme, electric blue accent
        panels/
            __init__.py
            library_panel.py   # Photo grid/list with thumbnails
            controls_panel.py  # Extraction controls, layout mode toggle
            feature_strip.py   # Bottom strip: color palette, edge map, depth map cards
        widgets/
            __init__.py
            viewport_widget.py # QRenderWidget wrapper
            progress_bar.py    # Styled extraction progress bar

    workers/
        __init__.py
        extraction_worker.py # QRunnable for background extraction
        ingestion_worker.py  # QRunnable for background photo loading

    config/
        __init__.py
        settings.py          # App defaults, point size ranges, LOD thresholds

    models/                  # ONNX model files (gitignored, downloaded on first run)
        depth_anything_v2_vits.onnx
```

### Pattern 1: QRenderWidget Embedding (GUI + Viewport Integration)

**What:** Embed pygfx's 3D renderer as a Qt widget inside the PySide6 layout using rendercanvas's QRenderWidget. The viewport is a standard QWidget that participates in Qt's layout system.

**When to use:** Always -- this is the only supported way to embed pygfx in PySide6.

**Example:**
```python
# Source: rendercanvas docs + pygfx Qt integration example
from PySide6 import QtWidgets
from rendercanvas.qt import QRenderWidget
import pygfx as gfx

class ViewportWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._canvas = QRenderWidget(self, update_mode="continuous")
        layout.addWidget(self._canvas)

        self._renderer = gfx.WgpuRenderer(self._canvas)
        self._scene = gfx.Scene()
        self._camera = gfx.PerspectiveCamera(60, 1)
        self._controller = gfx.OrbitController(self._camera, register_events=self._renderer)

        # Dark gradient background
        self._scene.add(gfx.Background.from_color("#1a1a1a", "#0a0a0a"))

        self._canvas.request_draw(self._animate)

    def _animate(self):
        self._renderer.render(self._scene, self._camera)

    def add_points(self, positions, colors, sizes):
        """Add a point cloud to the scene."""
        geometry = gfx.Geometry(
            positions=positions,  # (N, 3) float32
            colors=colors,        # (N, 4) float32
            sizes=sizes,          # (N,) float32
        )
        material = gfx.PointsGaussianBlobMaterial(
            color_mode="vertex",
            size_mode="vertex",
        )
        points = gfx.Points(geometry, material)
        self._scene.add(points)
        self._camera.show_object(self._scene)
```

### Pattern 2: Background Extraction with Qt Signals

**What:** Run feature extraction in QThreadPool workers. Workers emit Qt signals for progress updates and completion. Main thread stays responsive.

**When to use:** All extraction operations (color, edges, depth). Never block the main thread.

**Example:**
```python
# Source: Qt documentation + PySide6 threading patterns
from PySide6.QtCore import QRunnable, Signal, QObject, Slot, QThreadPool

class WorkerSignals(QObject):
    progress = Signal(int, int)      # current, total
    photo_complete = Signal(str, dict)  # photo_id, features
    finished = Signal()
    error = Signal(str)

class ExtractionWorker(QRunnable):
    def __init__(self, photo_paths, extractors):
        super().__init__()
        self.photo_paths = photo_paths
        self.extractors = extractors
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        for i, path in enumerate(self.photo_paths):
            try:
                features = {}
                for extractor in self.extractors:
                    features[extractor.name] = extractor.extract(path)
                self.signals.photo_complete.emit(path, features)
                self.signals.progress.emit(i + 1, len(self.photo_paths))
            except Exception as e:
                self.signals.error.emit(f"{path}: {e}")
        self.signals.finished.emit()

# Usage in main window:
# pool = QThreadPool.globalInstance()
# worker = ExtractionWorker(paths, [ColorExtractor(), EdgeExtractor(), DepthExtractor()])
# worker.signals.photo_complete.connect(self.on_photo_extracted)
# worker.signals.progress.connect(self.update_progress_bar)
# pool.start(worker)
```

### Pattern 3: Pluggable Extractor Interface

**What:** Each feature extractor implements a standard interface. The pipeline orchestrator runs enabled extractors in the configured order.

**When to use:** All extractors follow this pattern. Enables re-extraction, selective extraction, and future extractor additions.

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import numpy as np

@dataclass
class ExtractionResult:
    extractor_name: str
    data: dict[str, Any]       # Scalar metadata
    arrays: dict[str, np.ndarray]  # Array data (edge maps, depth maps, etc.)

class BaseExtractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def extract(self, image: np.ndarray) -> ExtractionResult: ...

class ColorExtractor(BaseExtractor):
    name = "color"

    def extract(self, image: np.ndarray) -> ExtractionResult:
        # ... palette extraction, histogram, etc.
        return ExtractionResult(
            extractor_name=self.name,
            data={"dominant_colors": palette, "histogram": hist_data},
            arrays={"color_distribution": distribution_map},
        )
```

### Pattern 4: Progressive Viewport Build

**What:** As each photo completes extraction, its point cloud is immediately added to the viewport. The sculpture grows in real-time.

**When to use:** During batch extraction. The `photo_complete` signal triggers point cloud generation and scene addition.

**How:** Worker emits `photo_complete` signal with features. Main thread generates point cloud from features. Points added to scene via `scene.add()`. pygfx re-renders on next frame automatically.

### Anti-Patterns to Avoid

- **Blocking main thread with extraction:** Never run ONNX inference or OpenCV processing on the main thread. Always use QThreadPool workers.
- **Storing points as Python objects:** Use contiguous numpy float32 arrays. A Python object has ~100 bytes overhead; 12M Python point objects = 1.2GB just for headers.
- **Multiple GPU contexts:** PySide6 and pygfx must share the same GPU context. Do not create a separate OpenGL context for Qt rendering. rendercanvas handles this correctly.
- **Polling for completion:** Use Qt signals/slots, never poll in a loop on the main thread.
- **Loading full images into GPU memory:** Only point cloud data goes to GPU. Source images are processed on CPU and discarded after extraction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Orbit camera controls | Custom mouse math for rotation/zoom/pan | `gfx.OrbitController` | Handles quaternion math, zoom-to-point, inertia, edge cases |
| Gaussian point rendering | Custom WGSL shader for soft circles | `gfx.PointsGaussianBlobMaterial` | pygfx has this built in; handles anti-aliasing and blending |
| Qt + wgpu embedding | Manual surface creation and event routing | `rendercanvas.qt.QRenderWidget` | Handles HiDPI, resize, event forwarding, vsync |
| Dark theme styling | Manual per-widget color setting | QSS stylesheet applied to QApplication | One stylesheet styles all widgets consistently |
| ONNX inference on AMD | Raw DirectML API calls | `onnxruntime-directml` package | Handles session creation, provider selection, memory management |
| Color palette extraction | Custom k-means on pixel arrays | `extcolors` library | Handles CIE76 color distance, grouping tolerance, occurrence counting |
| Image format detection | File extension checking | Pillow `Image.open()` with header validation | Handles corrupt files, wrong extensions, format variants |
| Progress bar styling | Custom paint events | QSS-styled `QProgressBar` | Qt handles animation, text overlay, platform rendering |

**Key insight:** pygfx already has the exact material (`PointsGaussianBlobMaterial`) and controller (`OrbitController`) needed for this project. The rendering layer is mostly configuration, not custom code.

## Common Pitfalls

### Pitfall 1: ONNX DirectML Silent CPU Fallback

**What goes wrong:** ONNX Runtime silently falls back to CPU when DirectML is unavailable. Depth extraction works but takes 10x longer. User thinks "it's just slow" rather than "GPU isn't being used."

**Why it happens:** `onnxruntime-directml` does not error when the GPU is unavailable -- it falls back to CPU.

**How to avoid:** Check providers explicitly at startup:
```python
import onnxruntime as ort
providers = ort.get_available_providers()
assert 'DmlExecutionProvider' in providers, "DirectML not available -- check GPU driver"
session = ort.InferenceSession("model.onnx", providers=['DmlExecutionProvider', 'CPUExecutionProvider'])
```

**Warning signs:** Depth extraction takes >5 seconds per image on a modern GPU.

### Pitfall 2: Color Space Mismatch (sRGB vs Linear)

**What goes wrong:** OpenCV loads images as BGR uint8 (sRGB gamma). pygfx expects linear float32 colors. Without conversion, point colors appear washed out or over-saturated in the viewport.

**Why it happens:** Most image formats store sRGB gamma-encoded values. GPU rendering operates in linear space.

**How to avoid:**
- Convert BGR -> RGB on load (`cv2.cvtColor(img, cv2.COLOR_BGR2RGB)`)
- Convert uint8 [0-255] to float32 [0.0-1.0] (`img.astype(np.float32) / 255.0`)
- For accurate color: apply sRGB-to-linear conversion (`np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)`)
- pygfx may handle sRGB conversion internally via texture format -- verify with test images

**Warning signs:** Colors in viewport don't match the source photo.

### Pitfall 3: Depth Map Resolution Mismatch

**What goes wrong:** Depth Anything V2 outputs at a fixed resolution (typically 518x518). The source photo may be 4000x3000. Naively mapping depth to pixels produces distorted point clouds.

**Why it happens:** The ONNX model has fixed input dimensions. Output must be resized to match source image resolution.

**How to avoid:**
- Resize depth output to match source image dimensions using bilinear interpolation
- Use `cv2.resize(depth_map, (original_width, original_height), interpolation=cv2.INTER_LINEAR)`
- Normalize depth values to [0, 1] range before applying exaggeration factor

**Warning signs:** Point cloud looks squished or stretched compared to source photo.

### Pitfall 4: 12M Points Performance Wall

**What goes wrong:** Full pixel density from a 12MP photo creates 12 million points. Multiple photos compound this. Rendering becomes sluggish.

**Why it happens:** 12M points at 28 bytes each (position float32x3 + color float32x4) = ~336 MB per photo. GPU can handle the memory, but draw call and fragment shader costs add up.

**How to avoid:**
- Implement LOD from the start: full resolution only when zoomed in
- For LOD, use spatial decimation: divide image into grid cells, render one point per cell at distance
- Set a rendering point budget (e.g., 5M points max visible at any time)
- Use frustum culling: don't render off-screen points

**Warning signs:** FPS drops below 30 when adding the second or third photo.

### Pitfall 5: QRenderWidget Resize Flicker

**What goes wrong:** Resizing the main window causes the viewport to flicker or show black frames briefly as the wgpu surface is recreated.

**Why it happens:** wgpu surface configuration must update when the widget size changes. If not handled correctly, there's a frame gap.

**How to avoid:** rendercanvas handles this internally, but ensure `update_mode="continuous"` is set on QRenderWidget so it redraws every frame. Do not manually manage surface recreation.

### Pitfall 6: GIL Blocking During ONNX Inference

**What goes wrong:** Even though ONNX Runtime runs inference on GPU, the Python call to `session.run()` holds the GIL during the call setup and output copy. This can cause brief UI freezes.

**Why it happens:** ONNX Runtime's Python bindings acquire the GIL for input/output marshaling.

**How to avoid:** Run ONNX inference in a QThreadPool worker (separate thread). Qt's event loop runs in the main thread and stays responsive. The GIL is released during the actual GPU computation inside ONNX Runtime's C++ core.

## Code Examples

### Depth Anything V2 ONNX Inference

```python
# Source: fabio-sim/Depth-Anything-ONNX + onnxruntime DirectML docs
import onnxruntime as ort
import numpy as np
import cv2

class DepthExtractor:
    def __init__(self, model_path: str = "models/depth_anything_v2_vits.onnx"):
        self.session = ort.InferenceSession(
            model_path,
            providers=['DmlExecutionProvider', 'CPUExecutionProvider']
        )
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # (1, 3, 518, 518)

    def extract(self, image: np.ndarray) -> np.ndarray:
        """Extract depth map from image. Returns float32 array matching input dimensions."""
        h, w = image.shape[:2]

        # Preprocess: resize to model input, normalize
        input_size = (self.input_shape[3], self.input_shape[2])  # (518, 518)
        resized = cv2.resize(image, input_size, interpolation=cv2.INTER_LINEAR)
        normalized = resized.astype(np.float32) / 255.0
        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std
        # HWC -> NCHW
        input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...]

        # Inference
        depth = self.session.run(None, {self.input_name: input_tensor})[0]
        depth = depth.squeeze()

        # Resize back to original resolution
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)

        # Normalize to [0, 1]
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)

        return depth
```

### Point Cloud Generation (Depth-Projected Mode)

```python
import numpy as np

def generate_depth_projected_cloud(
    image: np.ndarray,          # (H, W, 3) float32 RGB [0, 1]
    depth_map: np.ndarray,      # (H, W) float32 [0, 1]
    depth_exaggeration: float = 4.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate point cloud from image + depth map.

    Returns (positions, colors, sizes) as numpy arrays.
    """
    h, w = image.shape[:2]

    # Create grid of (x, y) coordinates normalized to [-1, 1]
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    x_norm = (x_coords.astype(np.float32) / w) * 2.0 - 1.0  # [-1, 1]
    y_norm = -((y_coords.astype(np.float32) / h) * 2.0 - 1.0)  # [-1, 1], flipped for Y-up

    # Z from depth, exaggerated
    z_coords = depth_map * depth_exaggeration

    # Flatten to (N, 3)
    positions = np.stack([x_norm, y_norm, z_coords], axis=-1).reshape(-1, 3).astype(np.float32)

    # Colors: add alpha channel
    colors_rgb = image.reshape(-1, 3)
    alpha = np.ones((colors_rgb.shape[0], 1), dtype=np.float32)
    colors = np.concatenate([colors_rgb, alpha], axis=-1)  # (N, 4)

    # Uniform sizes (can be varied later)
    sizes = np.full(positions.shape[0], 2.0, dtype=np.float32)

    return positions, colors, sizes
```

### PySide6 Main Window Layout

```python
# Source: PySide6 docs + rendercanvas Qt integration
from PySide6 import QtWidgets, QtCore

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apollo 7")
        self.resize(1920, 1080)
        self.setMinimumSize(1280, 720)

        # Apply dark theme
        self.setStyleSheet(load_theme_qss())

        # Central widget with main splitter
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Horizontal splitter: viewport (left 70%) | right panel (30%)
        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Vertical splitter for bottom strip
        v_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.viewport = ViewportWidget()
        self.feature_strip = FeatureStripPanel()
        v_splitter.addWidget(self.viewport)
        v_splitter.addWidget(self.feature_strip)
        v_splitter.setSizes([800, 150])  # Feature strip is collapsible

        # Right panel: controls on top, library below
        right_panel = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.controls_panel = ControlsPanel()
        self.library_panel = LibraryPanel()
        right_panel.addWidget(self.controls_panel)
        right_panel.addWidget(self.library_panel)
        right_panel.setSizes([300, 500])

        h_splitter.addWidget(v_splitter)
        h_splitter.addWidget(right_panel)
        h_splitter.setSizes([1400, 500])  # ~73% viewport

        main_layout.addWidget(h_splitter)
```

### Dark Theme QSS (Electric Blue Accent)

```python
def load_theme_qss() -> str:
    """Apollo 7 dark theme with electric blue accent."""
    accent = "#0078FF"       # Electric blue
    accent_hover = "#339BFF"
    bg_dark = "#1a1a1a"
    bg_panel = "#242424"
    bg_widget = "#2d2d2d"
    text_primary = "#e0e0e0"
    text_secondary = "#808080"
    border = "#3a3a3a"

    return f"""
    QMainWindow, QWidget {{
        background-color: {bg_dark};
        color: {text_primary};
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}
    QSplitter::handle {{
        background-color: {border};
        width: 2px;
        height: 2px;
    }}
    QPushButton {{
        background-color: {bg_widget};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 16px;
    }}
    QPushButton:hover {{
        background-color: {accent};
        border-color: {accent};
    }}
    QPushButton:pressed {{
        background-color: {accent_hover};
    }}
    QProgressBar {{
        background-color: {bg_widget};
        border: 1px solid {border};
        border-radius: 4px;
        text-align: center;
        color: {text_primary};
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 3px;
    }}
    QScrollBar:vertical {{
        background-color: {bg_panel};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {border};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {accent};
    }}
    QLabel {{
        color: {text_secondary};
    }}
    """
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OpenGL point sprites | wgpu/WebGPU compute-based rendering | 2023-2024 | GPU-vendor-agnostic; Vulkan/DX12 backend; no legacy OpenGL |
| MiDaS depth estimation | Depth Anything V2/V3 | 2024 (NeurIPS) | Significantly better depth quality; smaller models available (ViT-S) |
| PyTorch CUDA inference | ONNX Runtime + DirectML | 2024-2025 | Works on AMD GPUs natively; no CUDA dependency |
| Qt5/PyQt5 | PySide6 (Qt 6) | 2022+ | Modern rendering, better HiDPI, LGPL license |
| vispy (OpenGL) | pygfx (wgpu) | 2022+ | pygfx is vispy's spiritual successor; actively maintained |

**Deprecated/outdated:**
- DirectML is in maintenance mode (Microsoft shifting to Windows ML), but still ships with Windows and is the proven path for ONNX on AMD
- vispy: OpenGL-based, unmaintained relative to pygfx
- PyQt6: functionally identical to PySide6 but GPL-licensed

## Open Questions

1. **PointsGaussianBlobMaterial opacity/blending behavior**
   - What we know: The material exists in pygfx and renders Gaussian blobs. It accepts `size` parameter.
   - What's unclear: Whether it supports additive blending out of the box, and how opacity interacts with per-vertex alpha.
   - Recommendation: Test early in Phase 1 Wave 1. If additive blending is needed and not built in, a custom material shader may be required (pygfx supports custom WGSL shaders via `register_wgpu_render_function`).

2. **Full pixel density performance at 12M points**
   - What we know: pygfx handles point clouds well; GPU memory budget supports ~340M points theoretically.
   - What's unclear: Whether PointsGaussianBlobMaterial at 12M points with per-vertex color achieves 30+ FPS on RX 9060 XT.
   - Recommendation: Benchmark in Wave 1. If <30 FPS, implement LOD before proceeding to multi-photo support.

3. **Depth Anything V2 ONNX on DirectML operator support**
   - What we know: ONNX exports exist at opset 17 with dynamic shapes. DirectML supports most standard operators.
   - What's unclear: Whether all operators in Depth Anything V2's ViT-S ONNX graph are supported by DirectML.
   - Recommendation: Test ONNX inference on AMD hardware in the extraction wave. CPU fallback is the safety net.

4. **rendercanvas QRenderWidget + PySide6 event loop compatibility**
   - What we know: rendercanvas provides QRenderWidget; examples show Qt + asyncio integration.
   - What's unclear: Whether continuous rendering (30+ FPS) coexists smoothly with heavy Qt event processing (panel resizing, list scrolling).
   - Recommendation: Prove this integration in Wave 1 skeleton app before building any extraction code.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | None -- Wave 0 creates `pyproject.toml` with `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --timeout=30` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | Load single JPEG/PNG/TIFF photo | unit | `pytest tests/test_loader.py::test_load_single -x` | No -- Wave 0 |
| INGEST-02 | Batch-ingest folder with progress | unit | `pytest tests/test_loader.py::test_batch_ingest -x` | No -- Wave 0 |
| INGEST-03 | Generate thumbnails, extract metadata | unit | `pytest tests/test_thumbnailer.py -x` | No -- Wave 0 |
| EXTRACT-01 | Extract dominant colors and distributions | unit | `pytest tests/test_color_extractor.py -x` | No -- Wave 0 |
| EXTRACT-02 | Extract edges and contours | unit | `pytest tests/test_edge_extractor.py -x` | No -- Wave 0 |
| EXTRACT-03 | Depth map via ONNX/DirectML | integration | `pytest tests/test_depth_extractor.py -x` | No -- Wave 0 |
| RENDER-01 | Generate point cloud from features | unit | `pytest tests/test_pointcloud_generator.py -x` | No -- Wave 0 |
| RENDER-02 | Viewport renders with orbit controls | manual-only | Manual: launch app, verify orbit/zoom/pan | N/A |
| RENDER-03 | Configurable point size, color, opacity | manual-only | Manual: verify visual output | N/A |
| APP-01 | Professional GUI layout | manual-only | Manual: verify layout proportions, styling | N/A |
| APP-02 | Runs on Windows 11 AMD (no CUDA) | smoke | `pytest tests/test_gpu_providers.py -x` | No -- Wave 0 |
| APP-03 | Full GPU/CPU utilization | manual-only | Manual: verify task manager during extraction | N/A |
| APP-04 | UI responsive during extraction | integration | `pytest tests/test_responsive_ui.py -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x --timeout=30`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` -- project config with pytest settings, dependencies
- [ ] `tests/conftest.py` -- shared fixtures (test images, temp directories)
- [ ] `tests/test_loader.py` -- covers INGEST-01, INGEST-02
- [ ] `tests/test_thumbnailer.py` -- covers INGEST-03
- [ ] `tests/test_color_extractor.py` -- covers EXTRACT-01
- [ ] `tests/test_edge_extractor.py` -- covers EXTRACT-02
- [ ] `tests/test_depth_extractor.py` -- covers EXTRACT-03 (requires ONNX model)
- [ ] `tests/test_pointcloud_generator.py` -- covers RENDER-01
- [ ] `tests/test_gpu_providers.py` -- covers APP-02 (smoke test for DirectML)
- [ ] `tests/assets/` -- small test images (JPEG, PNG, TIFF)
- [ ] Framework install: `pip install pytest pytest-timeout`

## Sources

### Primary (HIGH confidence)
- [pygfx documentation - Materials](https://docs.pygfx.org/stable/_autosummary/pygfx.materials.html) -- PointsGaussianBlobMaterial, PointsMaterial API
- [pygfx documentation - Points rendering example](https://docs.pygfx.org/v0.13.0/_gallery/introductory/points_basic.html) -- Geometry setup with per-vertex colors/sizes
- [pygfx documentation - EDL point cloud](https://docs.pygfx.org/latest/_gallery/other/edl_pointcloud.html) -- Point cloud rendering pattern
- [pygfx documentation - Custom shaders](https://docs.pygfx.org/stable/advanced_shaders.html) -- BaseShader, register_wgpu_render_function
- [pygfx documentation - OrbitController](https://docs.pygfx.org/v0.1.17/_autosummary/controllers/pygfx.controllers.OrbitController.html) -- Camera controls API
- [rendercanvas docs - Backends](https://rendercanvas.readthedocs.io/latest/backends.html) -- QRenderWidget for PySide6
- [rendercanvas docs - Qt app with asyncio](https://rendercanvas.readthedocs.io/latest/gallery/qt_app_asyncio.html) -- Complete Qt integration example
- [Depth-Anything-ONNX](https://github.com/fabio-sim/Depth-Anything-ONNX) -- ONNX export, opset 17, dynamic shapes
- [ONNX Runtime DirectML EP](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html) -- AMD GPU inference
- [AMD GPUOpen ONNX+DirectML guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/) -- AMD-specific optimization

### Secondary (MEDIUM confidence)
- [pygfx 2025 roadmap](https://pygfx.org/report002.html) -- v1.0 targeting July 2026; current API may change
- [PySide6 threading patterns](https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/) -- QThreadPool + QRunnable patterns
- [qt-material theme library](https://pypi.org/project/qt-material/) -- Reference for QSS theming approach
- [extcolors PyPI](https://pypi.org/project/extcolors/0.1.0/) -- Color extraction API

### Tertiary (LOW confidence)
- PointsGaussianBlobMaterial additive blending behavior -- not verified in docs; needs empirical testing
- 12M point rendering performance on RX 9060 XT -- no benchmarks found for pygfx at this scale on RDNA 4

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified against official docs and PyPI
- Architecture: MEDIUM-HIGH -- patterns are standard (Qt signals, worker threads, pluggable extractors) but pygfx+Qt integration is niche
- Pitfalls: HIGH -- GPU fallback, color space, and scaling issues are well-documented
- Rendering specifics: MEDIUM -- PointsGaussianBlobMaterial exists but detailed behavior needs empirical validation

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (30 days; pygfx is pre-1.0 so API could shift)
