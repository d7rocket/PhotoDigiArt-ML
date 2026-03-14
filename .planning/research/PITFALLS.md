# Pitfalls Research

**Domain:** Data-driven generative art pipeline (photo-to-3D-sculpture)
**Researched:** 2026-03-14
**Confidence:** HIGH (GPU ecosystem verified against current sources; rendering patterns verified against published research)

---

## Critical Pitfalls

### CP-1: ROCm on Windows Is Not ROCm on Linux

**What goes wrong:** Developers assume ROCm on Windows has feature parity with Linux. It does not. The Windows offering is a subset called HIP SDK, which supports PyTorch and ONNX Runtime but lacks many ROCm libraries available on Linux (MIOpen, rocBLAS full suite, etc.). Many tutorials and Stack Overflow answers assume Linux ROCm and will silently fail on Windows.

**Why it happens:** AMD markets "ROCm" as a unified brand, but Windows support is a constrained subset. ROCm 6.4.4 added PyTorch on Windows for RDNA 4, and ROCm 7.x continues expanding, but the Windows surface area is smaller than Linux.

**How to avoid:**
- For ML inference (feature extraction, depth estimation): Use **ONNX Runtime with DirectML** or the newer **Windows ML** execution provider. DirectML works on all DirectX 12 GPUs including AMD RDNA 4, no ROCm required. DirectML is in maintenance mode but still ships with Windows; Windows ML is its successor.
- For compute shaders (particle simulation, point cloud transforms): Use **Vulkan compute** or **DirectX 12 compute**. These are first-class on AMD RDNA 4.
- For PyTorch training/fine-tuning (if ever needed): ROCm 6.4.4+ on Windows supports RDNA 4, but test early.
- Never depend on a single AMD compute path. Always have a CPU fallback.

**Warning signs:**
- Import errors mentioning `hiprtc` or `amdhip64` on Windows
- PyTorch `torch.cuda.is_available()` returning False (HIP masquerades as CUDA but needs correct builds)
- Tutorials that say "install ROCm" without specifying Windows vs Linux

**Phase to address:** Phase 1 (foundation). GPU compute strategy must be locked before any feature extraction or rendering work begins.

**Confidence:** HIGH -- verified against ROCm 7.2.0 release notes, AMD HIP SDK docs, and DirectML GitHub status.

---

### CP-2: The "It Works on 100 Photos" Scaling Wall

**What goes wrong:** The pipeline works beautifully with 10-100 photos but crashes or becomes unusable at 1,000+. Feature extraction creates per-image data (depth maps, edge maps, color histograms, embeddings) that accumulates linearly. A single photo might produce 50-200 MB of intermediate data. At 5,000 photos, that's 250 GB-1 TB of intermediate state that must be managed.

**Why it happens:** Developers build for the demo case (few images, immediate results) and defer batch processing architecture. Photo-to-feature pipelines are embarrassingly parallel but memory-hungry. Without streaming/chunking, the system tries to hold everything in RAM.

**How to avoid:**
- Design a **disk-backed feature store** from day one. Extract features per-image and write to a structured format (SQLite + binary blobs, or a purpose-built format like Apache Arrow/Parquet for metadata + raw binary for tensors).
- Process images in configurable batch sizes (e.g., 16-64 at a time), never all at once.
- Distinguish between **per-image features** (stored individually) and **aggregate features** (computed incrementally across the dataset). Only aggregate features should be in memory.
- Implement a progress/resume system: if extraction crashes at image 3,847 of 5,000, it should resume from 3,848.

**Warning signs:**
- RAM usage climbs linearly during batch processing with no plateau
- No concept of "already processed" images -- re-running means re-extracting everything
- Feature extraction function returns an in-memory list/array rather than writing to storage

**Phase to address:** Phase 1 (data pipeline core). The storage architecture must exist before scaling tests.

**Confidence:** HIGH -- standard data engineering pattern; verified against pipeline architecture best practices.

---

### CP-3: VRAM Exhaustion During Real-Time Point Cloud Rendering

**What goes wrong:** The renderer attempts to load all points into GPU VRAM simultaneously. With 16 GB VRAM (RX 9060 XT), a naive approach hits limits surprisingly fast. Each point with position (3x float32) + color (4x float32) + normal (3x float32) = 40 bytes. At 16 GB, that's ~400 million points max -- but VRAM is also needed for textures, framebuffers, shader state, and the OS compositor. Realistic budget is 100-200M points before problems.

**Why it happens:** Point clouds from thousands of photos can easily exceed hundreds of millions of points. Developers test with small datasets and never hit the wall until late in development.

**How to avoid:**
- Implement a **point budget** system: set a maximum number of rendered points (e.g., 5-50M) based on target framerate, and use Level-of-Detail (LOD) to select which points to render.
- Use **compute-based rendering** instead of the hardware point primitive pipeline. Research by Schutz et al. shows compute shaders outperform `GL_POINTS`/`VK_PRIMITIVE_TOPOLOGY_POINT_LIST` by up to 10x.
- Stream points from system RAM to VRAM per-frame based on camera frustum and distance (out-of-core rendering).
- Use quantized positions (16-bit or even 8-bit relative to a bounding box) to halve memory per point.

**Warning signs:**
- Framerate drops below 30 FPS when adding more data
- GPU memory usage reported near 100% in task manager
- Application crash with no error (GPU driver timeout / TDR on Windows)

**Phase to address:** Phase 2 (rendering engine). Must be designed in from the start of the renderer, not bolted on.

**Confidence:** HIGH -- verified against Magnopus point cloud rendering blog, Schutz et al. compute shader paper, and vsgPoints documentation.

---

### CP-4: Feature Extraction Model Ecosystem Assumes CUDA

**What goes wrong:** The best pre-trained models for depth estimation (MiDaS/ZoeDepth), edge detection (HED/BDCN), semantic segmentation (SAM), and image embeddings (CLIP, DINOv2) are trained and distributed as PyTorch models. Their default inference paths assume CUDA. Running them on AMD requires explicit conversion to ONNX and using a compatible execution provider.

**Why it happens:** NVIDIA dominates ML research hardware. Model authors test on CUDA and publish CUDA-optimized code. AMD support is an afterthought.

**How to avoid:**
- **ONNX is your universal adapter.** Convert every model to ONNX format before integrating it. ONNX Runtime with DirectML/Windows ML will handle AMD GPU acceleration.
- Pre-convert models during development, not at runtime. Ship ONNX files, not PyTorch checkpoints.
- Test every model on AMD hardware early. Some ONNX operators may not be supported by DirectML -- discover this in Phase 1, not Phase 3.
- Keep CPU inference as a tested fallback. Some models run acceptably on CPU for single-image use.
- Use OpenCV DNN module as an alternative inference engine -- it supports ONNX models and has OpenCL acceleration which works on AMD.

**Warning signs:**
- Code with `model.cuda()` or `device='cuda'` anywhere
- PyTorch models loaded directly without ONNX conversion
- Inference times 10x slower than expected (falling back to CPU silently)

**Phase to address:** Phase 1 (feature extraction). Every model must be validated on AMD before the extraction pipeline is considered complete.

**Confidence:** HIGH -- verified against ONNX Runtime DirectML docs, AMD GPUOpen ONNX guide, and OpenCV DNN documentation.

---

### CP-5: GUI Framework vs Rendering Engine War

**What goes wrong:** The GUI framework (for sliders, controls, file browsers) and the 3D rendering engine (for the viewport) compete for the GPU, the event loop, or both. Common failure modes:
1. GUI runs on one graphics API (OpenGL via Qt), renderer on another (Vulkan). Two GPU contexts thrash.
2. GUI event loop blocks rendering, causing stuttery viewport.
3. Renderer event loop blocks GUI, causing unresponsive controls.

**Why it happens:** GUI frameworks and real-time renderers are both "main loop owners." They each want to control the application lifecycle. Combining them requires explicit architecture decisions that are painful to retrofit.

**How to avoid:**
- Choose a GUI framework that is renderer-aware. Best options for this project:
  - **egui** (Rust, immediate-mode, renders via wgpu/Vulkan) -- GUI and 3D share the same GPU context
  - **Dear ImGui** (C++, immediate-mode) with a Vulkan backend -- same principle
  - If Python: **Dear PyGui** uses GPU-accelerated rendering internally
- Run the 3D viewport and GUI in the **same render pass / same graphics context**. Do not embed a separate renderer inside a GUI widget.
- If the GUI and renderer must be separate processes, use shared memory (not sockets) for frame data.

**Warning signs:**
- Two different `wgpu::Device` / `VkDevice` instances in the same application
- The 3D viewport is a "widget" that has its own OpenGL context
- GUI freezes when the renderer is computing, or viewport freezes when sliders are being dragged

**Phase to address:** Phase 1 (architecture decision). This is a foundational choice that affects everything built on top.

**Confidence:** HIGH -- verified against wgpu, egui, and Dear PyGui documentation and architecture patterns.

---

## Technical Debt Patterns

### TD-1: Hardcoded Feature-to-Visual Mappings

**What goes wrong:** The mapping between extracted features (e.g., "average color hue") and visual parameters (e.g., "particle velocity") gets hardcoded as direct function calls instead of being data-driven. Adding new mappings requires code changes rather than configuration.

**How to avoid:** Design a **mapping graph** from day one. Each mapping is a node: input feature -> transform function -> output visual parameter. Users manipulate the graph through the GUI. Internally, mappings are stored as serializable data (JSON/TOML), not code.

**Warning signs:**
- Functions named `map_color_to_velocity()` with hardcoded logic
- Adding a new feature-to-visual mapping requires changing Python/Rust code
- No way to save/load mapping presets

**Phase to address:** Phase 2 (mapping engine).

### TD-2: Monolithic Feature Extraction Pipeline

**What goes wrong:** All feature extractors (depth, edges, color, semantics) are coupled into a single pipeline that must run in order. Want to skip depth estimation? Too bad, it's step 3 of 7. Want to add a new extractor? Modify the giant pipeline function.

**How to avoid:** Each feature extractor is a **plugin** with a standard interface: takes an image path, returns a typed feature result. A registry/manifest lists available extractors. The pipeline orchestrator runs whichever extractors the user has enabled, in parallel where possible.

**Warning signs:**
- A single `extract_features()` function longer than 200 lines
- Feature extractors share state or depend on each other's outputs
- Cannot run one extractor without running all of them

**Phase to address:** Phase 1 (extraction architecture).

### TD-3: No Intermediate Format Versioning

**What goes wrong:** The feature store format changes as new extractors are added, but old extracted data can't be read by new code. Users must re-extract thousands of images whenever the format changes.

**How to avoid:** Version the feature store schema from v1. Include a version field in metadata. Write migration code when the schema changes. Design for forward compatibility (new fields are optional; old readers ignore unknown fields).

**Warning signs:**
- Feature store has no version field
- Code crashes when reading features extracted by an older version
- "Just re-run extraction" is the answer to format mismatch

**Phase to address:** Phase 1 (storage design).

---

## Integration Gotchas

### IG-1: ONNX Operator Coverage Gaps on DirectML

**What goes wrong:** Not all ONNX operators are supported by every execution provider. DirectML supports most standard operators but may lack exotic ones used by cutting-edge models. The model converts to ONNX successfully but fails at runtime with "unsupported operator" errors.

**How to avoid:**
- Test inference with DirectML immediately after ONNX conversion, not days later.
- Use `onnxruntime`'s `get_providers()` to verify DirectML is active.
- For unsupported operators, either: (a) simplify the model's ONNX export with `opset_version` adjustments, (b) use graph optimization to replace unsupported ops, or (c) fall back to CPU for that specific model.
- Windows ML (DirectML successor) may support more operators -- check compatibility.

**Phase to address:** Phase 1.

### IG-2: Color Space Mismatches Across Pipeline Stages

**What goes wrong:** Images are loaded as sRGB, feature extractors expect linear RGB, the renderer uses linear color space, and the GUI displays in sRGB. Intermediate conversions are missed, causing washed-out or oversaturated visuals. Extracted colors don't match what the user sees in the viewport.

**How to avoid:**
- Establish a **canonical color space** for internal processing (linear RGB float32).
- Convert to linear on ingest, convert to sRGB only for display.
- Document the color space at every pipeline boundary.
- Test with images that have known colors (color checker charts).

**Phase to address:** Phase 1-2 boundary (extraction writes linear, renderer reads linear).

### IG-3: Coordinate System Mismatches

**What goes wrong:** 2D image features (pixel coordinates) must be mapped to 3D space. Different libraries use different conventions: Y-up vs Z-up, left-handed vs right-handed, pixel origin at top-left vs bottom-left. Point clouds end up mirrored, rotated, or scaled incorrectly.

**How to avoid:**
- Choose one 3D coordinate convention and document it (recommendation: right-handed, Y-up, matching Vulkan's clip space expectations).
- Write explicit coordinate transform functions at every boundary between 2D image space and 3D world space.
- Visual regression tests: render a known dataset and compare against a reference screenshot.

**Phase to address:** Phase 2 (when 2D features meet 3D renderer).

---

## Performance Traps

### PT-1: CPU-GPU Data Transfer Bottleneck

**What goes wrong:** Feature data is extracted on the GPU (via ONNX inference), copied to CPU for processing, then copied back to GPU for rendering. Each CPU-GPU transfer is expensive. With millions of points updated per frame, this round-trip kills performance.

**Why it happens:** It's natural to process data in Python/CPU land between extraction and rendering. But the data should ideally never leave the GPU.

**How to avoid:**
- Design for **GPU-resident data** where possible. Feature extraction outputs should feed directly into GPU buffers used by the renderer.
- If CPU processing is needed (e.g., Python-based mapping logic), batch it -- don't transfer per-frame.
- Use mapped/pinned memory for transfers that must happen.
- Compute shaders can handle feature-to-visual mapping on the GPU, keeping data GPU-side.

**Warning signs:**
- Frame time spikes correlating with data upload calls
- `memcpy` or buffer upload operations in the per-frame render loop
- GPU utilization low despite visual complexity

**Phase to address:** Phase 2-3 (rendering + mapping integration).

### PT-2: Python GIL Blocking the Render Loop

**What goes wrong:** If the application uses Python for orchestration, the Global Interpreter Lock (GIL) serializes CPU-bound work. Feature extraction (even if GPU-accelerated) still has Python-side overhead that blocks the render thread, causing viewport stutter.

**How to avoid:**
- Run the renderer in a separate **process**, not thread. Use shared memory or memory-mapped files for communication.
- Alternatively, write the renderer in Rust/C++ and embed Python for scripting/orchestration only.
- Use `multiprocessing` or `asyncio` with process pools for extraction tasks.
- If using Rust: no GIL problem. The renderer and extraction can run in parallel threads naturally.

**Warning signs:**
- Viewport FPS drops during feature extraction even though GPU has capacity
- `threading` used instead of `multiprocessing` for CPU-bound work
- Slider adjustments lag when background processing is active

**Phase to address:** Phase 1 (language/architecture choice).

### PT-3: Naive Point Cloud Generation (One Point Per Pixel)

**What goes wrong:** The simplest approach generates one 3D point per pixel in the source image. A single 4K photo = 8.3 million points. 1,000 photos = 8.3 billion points. This is unmanageable.

**How to avoid:**
- **Downsample intelligently**: extract features at lower resolution, generate points at salient locations only.
- Use edge/saliency detection to concentrate points where visual information is dense.
- Implement **importance sampling**: more points in interesting regions, fewer in uniform areas.
- Set a per-image point budget (e.g., 10,000-100,000 points per image) and use feature importance to allocate.

**Warning signs:**
- Point count equals `width * height * num_images`
- All regions of an image contribute equally to the point cloud
- System runs out of memory on the 10th image

**Phase to address:** Phase 2 (point cloud generation strategy).

---

## UX Pitfalls

### UX-1: No Preview During Long Processing

**What goes wrong:** Extracting features from 5,000 photos takes hours. The user sees a progress bar and nothing else. They have no idea if the result will be interesting until extraction completes.

**How to avoid:**
- Show **progressive previews**: after the first 50 images, render a preliminary sculpture. Update as more images are processed.
- Display extracted feature thumbnails as they complete (depth maps, edge maps, color palettes).
- Allow users to **start exploring** with partial data while extraction continues in the background.

**Phase to address:** Phase 3 (UX polish).

### UX-2: Parameter Overload in High-Control Mode

**What goes wrong:** The high-control mode exposes 50+ sliders and parameters. Users are overwhelmed and can't find meaningful combinations. The interface becomes a wall of knobs.

**How to avoid:**
- Group parameters into **layers**: Global (affects everything), Per-Feature (affects one data source), Per-Visual (affects one rendering aspect).
- Provide **presets** as starting points that users can modify.
- Use progressive disclosure: show 5-8 key parameters by default, expand to full control on demand.
- Discovery mode should produce parameter settings that users can then inspect/modify in high-control mode -- bridging the two modes.

**Phase to address:** Phase 3 (GUI design).

### UX-3: No Undo/History for Parameter Changes

**What goes wrong:** User adjusts 15 parameters to find a beautiful result, then accidentally moves one slider and can't get back. With real-time rendering, there's no "render this again" -- the moment is lost.

**How to avoid:**
- Implement **parameter snapshots**: save the full parameter state as a named preset at any time.
- Auto-snapshot on significant changes (slider released, preset loaded).
- Provide undo/redo for parameter changes (command pattern on the parameter state).

**Phase to address:** Phase 3 (interaction design).

---

## "Looks Done But Isn't" Checklist

| Feature | Looks Done When... | Actually Done When... |
|---------|--------------------|-----------------------|
| Feature extraction | Works on 10 JPEG photos | Works on 5,000 mixed-format images (JPEG, PNG, RAW, HEIC) with resume-on-failure |
| Point cloud rendering | 1M points at 60 FPS | 50M+ points at 60 FPS with LOD, frustum culling, and camera-distance-based detail |
| GUI controls | Sliders move, values change | Changes apply in real-time without frame drops, undo works, presets save/load |
| AMD GPU support | "It runs" | Tested on actual RX 9060 XT hardware, not just CPU fallback silently activating |
| Color pipeline | "Colors look right" | Verified with color checker: input sRGB -> processing linear -> display sRGB, gamma correct |
| Batch processing | Can process a folder | Handles missing files, corrupt images, mixed orientations, EXIF rotation, and resumes after crash |
| Discovery mode | "Makes something pretty" | Produces meaningfully different outputs based on different input data (not just random noise) |
| Save/export | Can save a screenshot | Can save the full project state (images, features, mappings, camera position) and reload it identically |

---

## Recovery Strategies

### When GPU Compute Path Fails
1. Verify DirectML/ONNX Runtime is detecting the GPU: `ort.get_available_providers()`
2. Fall back to CPU inference (slower but functional)
3. Check Windows GPU driver version -- RDNA 4 needs recent Adrenalin drivers
4. Check for TDR (Timeout Detection and Recovery) -- increase Windows registry `TdrDelay` if GPU compute takes >2 seconds per dispatch

### When Point Cloud Rendering Stutters
1. Reduce point budget (fewer points rendered per frame)
2. Enable frustum culling (don't render off-screen points)
3. Check for CPU-GPU memory transfer bottleneck (profile with RenderDoc or Radeon GPU Profiler)
4. Switch from point primitives to compute-based rendering

### When Feature Extraction Produces Garbage
1. Check input image color space (sRGB assumed by most models)
2. Verify ONNX model input dimensions match actual input (many models expect 224x224 or 384x384)
3. Check normalization: most models expect `[0, 1]` or `[-1, 1]` float input, not `[0, 255]` uint8
4. Test the same model on CPU to rule out DirectML execution differences

### When the Application Freezes
1. Check if GPU TDR is triggering (Event Viewer > System > "Display driver stopped responding")
2. Check if Python GIL is blocking the render thread
3. Check if feature extraction is running synchronously instead of async
4. Monitor VRAM usage -- near-100% VRAM can cause driver-level stalls

---

## Pitfall-to-Phase Mapping

| Phase | Pitfalls to Address | Priority |
|-------|---------------------|----------|
| **Phase 1: Foundation** | CP-1 (GPU compute strategy), CP-2 (scaling architecture), CP-4 (ONNX model validation), CP-5 (GUI+renderer architecture), TD-2 (plugin extraction), TD-3 (format versioning), IG-1 (DirectML operator gaps), PT-2 (GIL/process architecture) | CRITICAL -- wrong decisions here cause rewrites |
| **Phase 2: Rendering + Mapping** | CP-3 (VRAM management), TD-1 (data-driven mappings), IG-2 (color spaces), IG-3 (coordinate systems), PT-1 (CPU-GPU transfer), PT-3 (naive point generation) | HIGH -- rendering architecture must be right from start |
| **Phase 3: UX + Polish** | UX-1 (progressive preview), UX-2 (parameter overload), UX-3 (undo/history) | MEDIUM -- can iterate, but plan for these upfront |

---

## Sources

- [ROCm 7.2.0 Release Notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- [ROCm 6.4.4 PyTorch Windows Support](https://wccftech.com/amd-rocm-6-4-4-pytorch-support-windows-radeon-9000-radeon-7000-gpus-ryzen-ai-apus/)
- [AMD ROCm 7.0.2 with RX 9060 Support](https://videocardz.com/newz/amd-releases-rocm-7-0-2-with-radeon-rx-9060-support)
- [AMD HIP SDK for Windows](https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html)
- [DirectML GitHub (Maintenance Mode)](https://github.com/microsoft/DirectML)
- [Windows ML - Future of ML on Windows](https://blogs.windows.com/windowsdeveloper/2025/05/19/introducing-windows-ml-the-future-of-machine-learning-development-on-windows/)
- [ONNX Runtime DirectML Execution Provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [AMD GPUOpen ONNX + DirectML Guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/)
- [Rendering Point Clouds with Compute Shaders (Schutz et al.)](https://arxiv.org/pdf/2104.07526)
- [Magnopus: How We Render Extremely Large Point Clouds](https://www.magnopus.com/blog/how-we-render-extremely-large-point-clouds)
- [vsgPoints - Vulkan Point Cloud Rendering](https://github.com/vsg-dev/vsgPoints)
- [OpenCV DNN Module](https://opencv.org/opencv-dnn-module/)
- [wgpu - Portable Rust Graphics Library](https://wgpu.rs/)
- [AMD GPU Acceleration Technologies Explained (2025)](https://gist.github.com/danielrosehill/8793e2028ef4bd08c6ca955a38b40e5b)
