# Architecture Research

**Domain:** Data-driven generative art pipeline
**Researched:** 2026-03-14
**Confidence:** MEDIUM (novel domain combining well-understood components in an uncommon way; individual components are well-documented but their integration is bespoke)

## Standard Architecture

### System Overview

```
+------------------------------------------------------------------+
|                        DESKTOP GUI (PySide6)                      |
|  +-------------+  +-------------------+  +--------------------+  |
|  | Import Panel |  | Parameter Controls|  | Mode Switcher      |  |
|  | (drag/drop)  |  | (sliders, maps)   |  | (High-Control /    |  |
|  +------+------+  +--------+----------+  |  Discovery)         |  |
|         |                  |              +--------------------+  |
|  +------v------------------v-------------------------------+     |
|  |              3D VIEWPORT (wgpu-py / pygfx)              |     |
|  |         QRenderWidget embedded in PySide6 layout        |     |
|  +-------------------------^-------------------------------+     |
+--------------------------------|----------------------------------+
                                 |
              +------------------+------------------+
              |          SCENE GRAPH / STATE         |
              |  (point clouds, particle systems,    |
              |   camera, lighting, animations)      |
              +------------------+------------------+
                                 |
         +-----------------------+-----------------------+
         |                                               |
+--------v---------+                          +----------v---------+
| MAPPING ENGINE   |                          | ANIMATION ENGINE   |
| Feature -> Visual|                          | Fluid motion,      |
| (color, position,|                          | morphing, flow     |
| size, density)   |                          | fields, turbulence |
+--------+---------+                          +----------+---------+
         |                                               |
         +-------------------+---------------------------+
                             |
              +--------------v--------------+
              |      FEATURE STORE          |
              |  (extracted data per image  |
              |   + aggregate statistics)   |
              +--------------+--------------+
                             |
         +-------------------+-------------------+
         |                   |                   |
+--------v------+  +---------v------+  +---------v--------+
| GEOMETRY      |  | COLOR/TEXTURE  |  | SEMANTIC         |
| EXTRACTOR     |  | EXTRACTOR      |  | EXTRACTOR        |
| - Edges (Canny|  | - Palette      |  | - Object detect  |
|   Sobel)      |  |   (k-means)    |  |   (YOLO/ONNX)   |
| - Contours    |  | - Gradients    |  | - Scene class.   |
| - Depth map   |  | - Texture freq |  | - Mood/narrative |
|   (Depth Any.)|  | - Visual rhythm|  |   (Claude API)   |
| - Keypoints   |  | - Histograms   |  | - Embeddings     |
+--------+------+  +---------+------+  +---------+--------+
         |                   |                   |
         +-------------------+-------------------+
                             |
              +--------------v--------------+
              |      IMAGE INGESTION        |
              |  - Single / batch import    |
              |  - Thumbnail generation     |
              |  - Metadata extraction      |
              |  - Queue management         |
              +--------------+--------------+
                             |
                    +--------v--------+
                    |  SOURCE PHOTOS  |
                    |  (filesystem)   |
                    +-----------------+
```

### Component Responsibilities

| Component | Responsibility | Inputs | Outputs |
|-----------|---------------|--------|---------|
| **Image Ingestion** | Load, validate, thumbnail, queue photos for processing | File paths (single or directory) | Normalized images + metadata |
| **Geometry Extractor** | Extract spatial structure from images | Normalized images | Edge maps, contours, depth maps, keypoints |
| **Color/Texture Extractor** | Extract color palettes, gradients, texture signals | Normalized images | Palettes, gradient maps, frequency data |
| **Semantic Extractor** | Extract meaning, objects, mood | Normalized images | Labels, embeddings, mood vectors |
| **Feature Store** | Persist and index all extracted features per image and in aggregate | Extractor outputs | Queryable feature database |
| **Mapping Engine** | Translate features into visual parameters (position, color, size, opacity, motion) | Feature data + user mappings | Scene primitives (point positions, colors, sizes) |
| **Animation Engine** | Drive fluid motion, morphing, flow fields | Scene primitives + time | Animated scene updates per frame |
| **Scene Graph** | Hold the current 3D state: point clouds, particles, camera, lights | Mapping + animation outputs | Renderable scene |
| **3D Viewport** | GPU-accelerated real-time rendering with orbit/zoom/pan | Scene graph | Pixels on screen |
| **Desktop GUI** | Controls, sliders, mode switching, import UI | User interaction | Commands to all other components |

## Recommended Project Structure

```
apollo7/
    __main__.py              # Entry point
    app.py                   # Application bootstrap, DI wiring

    ingestion/
        __init__.py
        loader.py            # Single + batch image loading
        thumbnailer.py       # Thumbnail generation
        queue.py             # Processing queue management

    extraction/
        __init__.py
        base.py              # Abstract extractor interface
        geometry.py          # Edge, contour, depth, keypoint extraction
        color.py             # Palette, gradient, texture extraction
        semantic.py          # Object detection, classification, mood
        pipeline.py          # Orchestrates extractors in sequence

    features/
        __init__.py
        store.py             # Feature persistence (SQLite + numpy arrays)
        schema.py            # Feature data models
        aggregator.py        # Cross-image statistics and patterns

    mapping/
        __init__.py
        engine.py            # Feature-to-visual parameter mapping
        presets.py           # Built-in mapping presets
        discovery.py         # Auto-suggested mappings (discovery mode)

    scene/
        __init__.py
        graph.py             # Scene graph (points, particles, camera)
        pointcloud.py        # Point cloud generation and management
        particles.py         # Particle system behaviors
        animation.py         # Flow fields, morphing, turbulence

    rendering/
        __init__.py
        viewport.py          # wgpu/pygfx renderer setup
        shaders/             # WGSL compute and render shaders
            particle.wgsl
            pointcloud.wgsl
            postprocess.wgsl
        camera.py            # Orbit camera controller

    gui/
        __init__.py
        main_window.py       # PySide6 main window
        panels/
            import_panel.py  # Photo import UI
            controls.py      # Parameter sliders and mapping UI
            feature_view.py  # Feature visualization panel
        widgets/
            viewport_widget.py  # QRenderWidget wrapper

    claude/                  # Optional Claude API integration
        __init__.py
        annotator.py         # Photo annotation via Claude
        advisor.py           # Artistic mapping suggestions

    config/
        __init__.py
        settings.py          # App settings, defaults
        presets/             # Saved mapping/rendering presets
```

## Architectural Patterns

### Pattern 1: Pipeline with Feature Store (Core Pattern)

**What:** The system is a staged pipeline where each stage produces intermediate artifacts persisted in a Feature Store. This decouples extraction from rendering -- you can re-extract features without re-rendering, and re-render without re-extracting.

**Why:** Photos can take seconds to minutes to process through ML models. The Feature Store means you process once, explore many times. It also enables aggregate analysis across thousands of photos (finding patterns, outliers, dominant colors).

**Implementation:**
```python
class FeatureStore:
    """SQLite metadata + numpy .npz files for array data."""

    def store_features(self, image_id: str, extractor: str, features: dict):
        # Scalar metadata -> SQLite
        # Arrays (depth maps, embeddings) -> .npz on disk
        ...

    def get_features(self, image_id: str) -> ImageFeatures:
        ...

    def get_aggregate(self, feature_name: str) -> AggregateStats:
        # Cross-image statistics for discovery mode
        ...
```

### Pattern 2: Mapping as Configuration, Not Code

**What:** Feature-to-visual mappings are declarative data structures, not hardcoded logic. A mapping says "depth value maps to Z position via ease-in curve, range 0-100" rather than implementing the transform in code.

**Why:** This enables the High-Control mode (user edits mappings via sliders) and Discovery mode (system proposes mappings) through the same mechanism. It also makes presets trivial to save/load.

```python
@dataclass
class FeatureMapping:
    source_feature: str       # e.g., "color.dominant_hue"
    target_param: str         # e.g., "point.color.h"
    curve: str                # "linear", "ease_in", "step", "noise"
    source_range: tuple       # (0.0, 360.0)
    target_range: tuple       # (0.0, 1.0)
    weight: float             # 0.0 - 1.0 blend factor
```

### Pattern 3: GPU Compute for Particles, CPU for Extraction

**What:** Extraction (OpenCV, ONNX models) runs on CPU or GPU via DirectML/ROCm. Particle simulation and rendering runs entirely on GPU via wgpu compute shaders. These are separate GPU workloads that do not share memory.

**Why:** Extraction is batch/offline work. Rendering is real-time (60fps target). Mixing them on the same GPU path creates contention. By separating them, extraction can saturate the GPU for inference while rendering uses the GPU graphics pipeline independently. The Feature Store is the clean boundary between the two worlds.

### Pattern 4: Observer Pattern for Live Parameter Updates

**What:** GUI sliders emit change events. The Mapping Engine subscribes and recomputes affected visual parameters. The Scene Graph updates. The Viewport re-renders. No polling.

**Why:** Real-time interactivity requires that moving a slider immediately changes the visualization. An observer/signal pattern (Qt's signals/slots) naturally fits this, and PySide6 provides it natively.

## Data Flow

### Phase 1: Ingestion (Offline, User-Initiated)

```
User drops photos
    -> Loader validates (format, size, EXIF)
    -> Thumbnailer generates previews
    -> Queue manager schedules extraction
    -> Photos stored with unique IDs
```

### Phase 2: Feature Extraction (Offline, Background)

```
For each image in queue:
    -> Geometry extractor runs:
        - OpenCV edge detection (Canny, Sobel)
        - OpenCV contour finding
        - Depth Anything V2 via ONNX Runtime + DirectML (monocular depth)
        - ORB/SIFT keypoints
    -> Color extractor runs:
        - k-means palette extraction
        - Gradient direction analysis
        - FFT texture frequency
        - Color histogram
    -> Semantic extractor runs:
        - YOLOv8 object detection via ONNX + DirectML
        - Scene classification via ONNX model
        - (Optional) Claude API for mood/narrative annotation
    -> All features stored in Feature Store
    -> Aggregate statistics updated
```

### Phase 3: Mapping (Interactive)

```
User selects mapping mode:
    HIGH-CONTROL:
        -> User assigns feature channels to visual parameters
        -> Adjusts curves, ranges, weights via sliders
    DISCOVERY:
        -> System analyzes feature distributions
        -> Proposes interesting mappings (high variance features get priority)
        -> User accepts/modifies/rejects

Mapping Engine produces:
    -> Point positions (x, y, z) from spatial features
    -> Point colors (r, g, b, a) from color features
    -> Point sizes from intensity/significance
    -> Motion vectors from semantic relationships
```

### Phase 4: Rendering (Real-time, 60fps)

```
Mapping output -> GPU buffer upload (positions, colors, sizes)
    -> Compute shader: particle physics (flow fields, attraction, turbulence)
    -> Compute shader: animation updates (morph targets, oscillation)
    -> Render pass: point sprites / billboards with depth
    -> Render pass: post-processing (bloom, ambient occlusion)
    -> Present to QRenderWidget
```

### Data Format Between Stages

| Boundary | Format | Rationale |
|----------|--------|-----------|
| Filesystem -> Ingestion | JPEG/PNG/TIFF files | Standard photo formats |
| Ingestion -> Extraction | numpy arrays (HWC uint8) | Universal image representation |
| Extraction -> Feature Store | SQLite + .npz files | Queryable metadata + efficient array storage |
| Feature Store -> Mapping | Python dataclasses | Type-safe, easy to serialize |
| Mapping -> Scene | numpy arrays (Nx3 float32 for positions, etc.) | GPU-ready data layout |
| Scene -> Viewport | wgpu Buffers | Direct GPU memory |

## Scaling Considerations

| Concern | 1-10 photos | 100-1K photos | 1K-10K photos |
|---------|-------------|---------------|---------------|
| **Extraction time** | Seconds, inline | Minutes, background thread | Hours, background process with progress bar |
| **Feature Store size** | < 100 MB, all in memory | 1-5 GB, memory-mapped | 5-50 GB, indexed queries only |
| **Point cloud density** | 100K-1M points, trivial | 1M-10M points, LOD needed | 10M-100M points, octree + frustum culling mandatory |
| **GPU memory (16GB VRAM)** | No concern | Point data fits (~160MB for 10M points) | Must stream/page, show LOD at distance |
| **Aggregate statistics** | Per-image only | Meaningful cross-image patterns emerge | Clustering, dimensionality reduction needed (UMAP/t-SNE) |

### GPU Memory Budget (RX 9060 XT, 16GB VRAM)

```
Rendering pipeline:
  Framebuffer (4K RGBA):       ~33 MB
  Depth buffer (4K):           ~16 MB
  Post-process buffers:        ~66 MB
  Total rendering overhead:   ~115 MB

Point cloud data (per million points):
  Positions (float32 x3):      12 MB
  Colors (float32 x4):         16 MB
  Sizes (float32):              4 MB
  Velocities (float32 x3):    12 MB
  Total per 1M points:        ~44 MB

Budget for points: ~15 GB available -> ~340M points theoretical max
Practical limit with animation buffers: ~50-100M points at 60fps
```

### Extraction Performance Strategy

| Extractor | Tool | AMD GPU Acceleration | Fallback |
|-----------|------|---------------------|----------|
| Edge/contour | OpenCV | CPU (fast enough) | N/A |
| Depth map | Depth Anything V2 | ONNX Runtime + DirectML | CPU (slow but works) |
| Object detection | YOLOv8 | ONNX Runtime + DirectML | CPU |
| Color palette | scikit-image / numpy | CPU (fast) | N/A |
| Embeddings | CLIP | ONNX Runtime + DirectML | CPU |
| Mood/narrative | Claude API | Cloud | Skip (optional) |

**Key insight:** DirectML is the primary GPU inference path for AMD on Windows. It works with any DirectX 12 GPU without vendor-specific drivers. PyTorch + ROCm is now available for RX 9000 series on Windows (ROCm 7.2+), but DirectML via ONNX Runtime is more battle-tested and model-portable.

## Anti-Patterns

### Anti-Pattern 1: Monolithic Extract-and-Render Loop

**What:** Processing images and rendering in the same thread/loop, blocking the viewport while extraction runs.

**Why bad:** Extraction of depth maps can take 1-5 seconds per image. The viewport would freeze during batch processing of hundreds of images. Users would think the app crashed.

**Instead:** Extraction runs in background threads (or a subprocess). The Feature Store is the async boundary. The viewport renders whatever data is available, progressively updating as new features arrive.

### Anti-Pattern 2: Storing Point Clouds as Python Objects

**What:** Representing millions of points as lists of Python objects or dataclass instances.

**Why bad:** A Python object has ~100 bytes overhead. 10M points = 1GB just for object headers, plus GC pressure that causes frame stutters.

**Instead:** Use contiguous numpy arrays (float32) for all point data. Upload to GPU buffers via wgpu. Never iterate points in Python -- operate on arrays or let compute shaders handle per-point logic.

### Anti-Pattern 3: Tight Coupling Between Extraction and Rendering

**What:** Rendering code directly calls extraction functions, or extraction code knows about rendering parameters.

**Why bad:** Makes it impossible to re-render with different mappings without re-extracting. Makes it impossible to swap rendering backends. Makes testing extraction without a GPU impossible.

**Instead:** The Feature Store is the clean boundary. Extraction writes to it. Rendering reads from it. They share data schemas but no code.

### Anti-Pattern 4: Hardcoded Feature-to-Visual Mappings

**What:** Writing code like `point.z = depth_map[y][x] * 50` scattered throughout the codebase.

**Why bad:** Destroys the High-Control / Discovery mode requirement. Every new mapping requires code changes.

**Instead:** Mappings are data. The Mapping Engine interprets them. Users configure them via the GUI.

### Anti-Pattern 5: Loading All Photos into GPU Memory

**What:** Uploading all source images as textures to the GPU.

**Why bad:** 1000 photos at 4K resolution = ~48 GB of uncompressed texture data. Exceeds any consumer GPU.

**Instead:** Photos are processed into features and then discarded from GPU memory. Only thumbnails are kept for the GUI. The point cloud IS the rendered representation -- the original photos are not rendered.

## Integration Points

### Internal Integration

| From | To | Mechanism | Notes |
|------|----|-----------|-------|
| GUI -> Ingestion | Function call + signal | User triggers import, progress bar updates via signals |
| GUI -> Mapping | Qt signals/slots | Slider changes emit signals, mapping engine subscribes |
| Ingestion -> Extraction | Queue (in-process) | `queue.Queue` or `asyncio.Queue` |
| Extraction -> Feature Store | Direct write | Extractor calls `store.store_features()` |
| Feature Store -> Mapping | Direct read | Mapping engine calls `store.get_features()` |
| Mapping -> Scene | Direct mutation | Mapping engine updates scene graph arrays |
| Scene -> Viewport | wgpu buffer upload | `device.queue.write_buffer()` per frame if dirty |
| Animation -> Scene | Per-frame update | Compute shader dispatch, no CPU round-trip |

### External Integration

| System | Protocol | Required? | Notes |
|--------|----------|-----------|-------|
| Claude API | HTTPS REST | Optional | Semantic annotation, artistic suggestions |
| Filesystem | OS APIs | Required | Photo loading, feature store persistence |
| ONNX Runtime | In-process C library | Required | ML model inference for depth, detection |
| DirectML | DirectX 12 driver | Required | GPU acceleration for ONNX models |

### Build Order (Dependency Chain)

The architecture implies this build sequence:

```
Phase 1: Foundation
    Image Ingestion (no dependencies)
    Feature Store schema + persistence (no dependencies)
    Basic PySide6 window with wgpu viewport (no dependencies)
    -> Milestone: Can load photos and see an empty 3D viewport

Phase 2: Extraction
    Geometry extractor (depends on: ingestion, feature store)
    Color extractor (depends on: ingestion, feature store)
    -> Milestone: Can extract features from photos and persist them

Phase 3: Point Cloud Generation
    Basic mapping engine (depends on: feature store)
    Point cloud from extracted features (depends on: mapping, viewport)
    Camera controls (depends on: viewport)
    -> Milestone: Photos become explorable 3D point clouds

Phase 4: Interactivity
    Parameter sliders wired to mapping engine (depends on: GUI, mapping)
    Real-time mapping updates (depends on: mapping, scene, viewport)
    High-Control mode (depends on: all above)
    -> Milestone: User can tune every parameter and see live results

Phase 5: Animation + Polish
    Flow fields and particle physics (depends on: scene, compute shaders)
    Discovery mode (depends on: feature store aggregate, mapping)
    Semantic extraction + Claude integration (depends on: feature store)
    -> Milestone: Flowing, organic data sculptures with discovery mode
```

## Sources

- [wgpu-py (WebGPU for Python)](https://github.com/pygfx/wgpu-py) -- GPU rendering layer, Vulkan/DX12 backend
- [pygfx render engine](https://github.com/pygfx/pygfx) -- 3D scene graph built on wgpu-py
- [rendercanvas Qt integration](https://rendercanvas.readthedocs.io/latest/backends.html) -- QRenderWidget for PySide6 embedding
- [ONNX Runtime DirectML](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html) -- GPU-accelerated ML inference on AMD
- [AMD ONNX + DirectML guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/) -- AMD-specific guidance
- [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) -- Monocular depth estimation
- [Depth Anything ONNX export](https://github.com/fabio-sim/Depth-Anything-ONNX) -- ONNX-compatible depth model
- [AMD ROCm on Radeon for Windows](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html) -- PyTorch + ROCm on RDNA 4
- [ROCm 7.2 release](https://github.com/ROCm/ROCm/releases) -- RDNA 4 support confirmation
- [Open3D v0.19 GPU support](https://www.open3d.org/2025/01/09/open3d-v0-19-is-out-with-new-features-and-more-gpu-support/) -- SYCL backend for AMD
- [Vulkan compute shaders tutorial](https://docs.vulkan.org/tutorial/latest/11_Compute_Shader.html) -- GPU compute fundamentals
- [Rendering Point Clouds with Compute Shaders (Schuetz 2021)](https://arxiv.org/pdf/2104.07526) -- Point cloud rendering techniques
- [Refik Anadol process](https://www.theartnewspaper.com/2024/04/05/on-process-refik-anadol-seeks-to-demystify-ai-art-by-showing-how-it-is-put-together) -- Artistic reference for data sculpture pipeline
- [Variable.io generative data art](https://variable.io/generative-and-data-art/) -- Industry reference for data-driven art systems
