# Project Research Summary

**Project:** Apollo 7
**Domain:** Data-driven generative art pipeline (photo-to-data-sculpture, desktop, AMD GPU)
**Researched:** 2026-03-14
**Confidence:** MEDIUM

## Executive Summary

Apollo 7 is a desktop application that transforms collections of photographs into explorable 3D data sculptures -- point clouds and particle systems driven by extracted image features (color, edges, depth, semantics). The closest commercial analogues are Refik Anadol's studio installations, but Apollo 7 targets a single artist on a single machine with a GUI, not a team of engineers with GPU clusters. The competitive landscape (TouchDesigner, Processing, openFrameworks, Houdini) requires programming or node-wiring; Apollo 7's differentiator is a zero-code, end-to-end photo-to-sculpture workflow with AI-guided discovery.

The recommended approach is a staged pipeline architecture with a persistent Feature Store as the central decoupling point. Photos flow through extraction (OpenCV, Depth Anything V2, CLIP via ONNX+DirectML), features are stored to disk (SQLite + numpy arrays), a declarative Mapping Engine translates features to visual parameters, and pygfx (WebGPU/Vulkan) renders the result at 60fps in a PySide6 desktop shell. The AMD RX 9060 XT constraint drives a dual-path GPU strategy: PyTorch+ROCm for heavy ML inference, ONNX Runtime+DirectML as a portable fallback, and wgpu for all rendering and compute shaders. This redundancy is deliberate -- ROCm on Windows is functional but young.

The primary risks are: (1) ROCm/DirectML model compatibility gaps discovered late, (2) scaling failures when moving from 100 to 5,000+ photos, and (3) GUI-renderer integration issues between PySide6 and the wgpu viewport. All three must be validated in Phase 1 before building features on top. The mitigation strategy is to build and test the GPU compute paths, Feature Store, and PySide6+pygfx integration as the first deliverables, proving the architecture before adding extraction or creative features.

## Key Findings

### Recommended Stack

The AMD GPU constraint on Windows is the single biggest technology driver. Python 3.12 is mandatory (ROCm wheels are cp312-only). The stack splits into three independent GPU paths that provide fault isolation: PyTorch+ROCm 7.2 for heavy ML models, ONNX Runtime+DirectML for lighter models and as a fallback, and pygfx/wgpu for all 3D rendering via Vulkan/DX12.

**Core technologies:**
- **Python 3.12 + conda**: Runtime pinned by ROCm wheel requirements. conda recommended by AMD for environment isolation
- **PyTorch 2.9.1 + ROCm 7.2**: GPU-accelerated inference for Depth Anything, semantic models on RX 9060 XT
- **ONNX Runtime + DirectML**: Portable GPU inference for CLIP, edge detection CNNs. Works on any DX12 GPU, no vendor-specific driver needed
- **pygfx 0.16.0 + wgpu-py 0.31.0**: 3D rendering engine built on WebGPU. Vendor-agnostic, renders via Vulkan/DX12. Point clouds, particles, custom WGSL compute shaders
- **PySide6 6.8+**: Desktop GUI with dockable panels, sliders. Official Qt integration with pygfx via rendercanvas
- **OpenCV + scikit-image**: CPU-based image feature extraction (edges, contours, textures, histograms)
- **Depth Anything V2**: Monocular depth estimation. Start with V2 (proven), upgrade to V3 after ONNX export validation

**Critical version requirement:** AMD driver 26.1.1+ must be installed before ROCm wheels. Without it, PyTorch silently falls back to CPU.

### Expected Features

**Must have (table stakes -- P0):**
- Single-image ingestion with color + edge extraction
- Point cloud generation from extracted features
- Real-time 3D viewport with orbit/zoom/pan (30+ FPS at 100K+ points)
- Parameter controls (sliders for point size, color mapping, density)
- Save/load project state
- Export still images

**Should have (core experience -- P1):**
- Batch image ingestion with progress feedback
- Depth estimation via monocular model (richer 3D geometry)
- Basic particle system with noise-driven motion
- Preset save/load
- Undo/redo for parameter changes

**Differentiators (competitive advantage -- P2):**
- Discovery mode: AI-guided composition proposals based on extracted feature distributions
- Semantic feature extraction (CLIP/BLIP local models)
- Feature-to-visual mapping editor (explicit, rewirable connections)
- Claude API integration for creative direction
- Multi-photo pattern emergence (collection-level analysis)
- Preset interpolation + live parameter animation

**Defer indefinitely:** Node editor, video input, camera feed, cloud rendering, plugin system, mesh export, social features, multi-user collaboration.

### Architecture Approach

The system is a staged pipeline with a Feature Store as the decoupling boundary between offline extraction and real-time rendering. Extraction is batch/background work; rendering is 60fps interactive. The Mapping Engine translates features to visuals via declarative data structures (not code), enabling both High-Control mode (user edits mappings) and Discovery mode (system proposes mappings) through the same mechanism. Qt signals/slots provide observer-pattern live updates from sliders to viewport.

**Major components:**
1. **Image Ingestion** -- Load, validate, thumbnail, queue photos. Entry point for all data
2. **Feature Extractors** (Geometry, Color, Semantic) -- Independent extractors with a shared interface. Each writes to the Feature Store
3. **Feature Store** -- SQLite metadata + numpy .npz arrays on disk. Process once, explore many times. Versioned schema from day one
4. **Mapping Engine** -- Declarative feature-to-visual parameter translation. Curves, ranges, weights as data, not code
5. **Scene Graph + Animation Engine** -- Point clouds, particles, flow fields, camera. GPU-resident data updated via compute shaders
6. **3D Viewport** -- pygfx/wgpu rendering embedded in PySide6 via rendercanvas WgpuWidget
7. **Desktop GUI** -- PySide6 main window with dockable panels, parameter controls, import UI

### Critical Pitfalls

1. **ROCm on Windows is not ROCm on Linux (CP-1)** -- Windows ROCm is a subset. Use ONNX+DirectML as the primary portable inference path; treat ROCm as a performance bonus. Test every model on AMD hardware in Phase 1, not Phase 3.

2. **The "works on 100 photos" scaling wall (CP-2)** -- Per-image feature data accumulates to hundreds of GB at scale. Design a disk-backed Feature Store from day one with batch processing, resume-on-failure, and incremental aggregation. Never hold all features in RAM.

3. **VRAM exhaustion during real-time rendering (CP-3)** -- Naive point clouds from thousands of photos can exceed hundreds of millions of points. Implement a point budget system, LOD, frustum culling, and importance sampling. Budget is ~50-100M points at 60fps on 16GB VRAM.

4. **ML model ecosystem assumes CUDA (CP-4)** -- All models must be converted to ONNX and validated with DirectML before integration. Ship ONNX files, not PyTorch checkpoints. Keep CPU fallback tested.

5. **GUI framework vs renderer event loop conflict (CP-5)** -- PySide6 and wgpu both want to own the main loop. Use rendercanvas Qt backend (WgpuWidget) to embed the viewport in Qt. If integration fails, GLFW fallback window is the escape hatch. Validate this integration first.

## Implications for Roadmap

### Phase 1: Foundation and Pipeline Core
**Rationale:** The architecture has four must-validate risks (GPU compute paths, Feature Store scaling, model ONNX compatibility, PySide6+pygfx integration) that all need to be proven before any creative features are built. Getting this wrong causes full rewrites.
**Delivers:** Working GPU pipeline proof: load a photo, extract basic features (color + edges), store in Feature Store, render a simple point cloud in a PySide6 window with orbit camera.
**Addresses features:** Image ingestion (P0), basic extraction (P0), point cloud rendering (P0), 3D viewport (P0)
**Avoids pitfalls:** CP-1 (GPU strategy locked), CP-2 (Feature Store designed), CP-4 (ONNX validated on AMD), CP-5 (GUI+renderer proven), TD-2 (extractor plugin interface), TD-3 (schema versioning)

### Phase 2: Core Creative Experience
**Rationale:** With the pipeline proven, this phase adds the features that make the tool usable for actual creative work. Depth estimation adds 3D richness, parameter controls add interactivity, particles add life. This is where the product becomes compelling.
**Delivers:** Interactive data sculpture tool: depth-enhanced point clouds, real-time parameter tuning, basic particle motion, save/load, export.
**Addresses features:** Depth estimation (P1), parameter controls (P0), particle system (P1), save/load (P0), export (P1), batch ingestion (P1), undo/redo (P1), presets (P1)
**Avoids pitfalls:** CP-3 (VRAM management with point budgets/LOD), IG-2 (color space pipeline), IG-3 (coordinate conventions), PT-1 (minimize CPU-GPU transfers), PT-3 (importance sampling, not one-point-per-pixel)

### Phase 3: Differentiators and Discovery
**Rationale:** The differentiating features (Discovery mode, semantic extraction, mapping editor, Claude integration) depend on a complete and stable extraction + rendering pipeline. They are high-complexity, high-value features that should only be attempted on a solid foundation.
**Delivers:** AI-assisted creative workflow: semantic understanding of photos, discovery mode that proposes interesting sculptures, visual mapping editor, collection-level pattern emergence.
**Addresses features:** Semantic extraction (P2), discovery mode (P2), feature-to-visual mapping editor (P2), Claude API (P2), multi-photo patterns (P2), preset interpolation (P2), parameter animation (P2)
**Avoids pitfalls:** UX-1 (progressive preview during batch), UX-2 (parameter overload via progressive disclosure), UX-3 (undo/history)

### Phase Ordering Rationale

- **Dependencies flow strictly downward.** Point cloud rendering (Phase 2) requires the Feature Store and viewport (Phase 1). Discovery mode (Phase 3) requires semantic extraction and a working mapping engine (Phase 2). There are no shortcuts.
- **Risk front-loading.** The four critical pitfalls (CP-1 through CP-5) all map to Phase 1 decisions. By proving GPU paths, Feature Store scaling, and GUI+renderer integration first, the project avoids late-stage architectural rework.
- **The "critical path" from FEATURES.md is explicit:** Ingestion -> Extraction -> Point Cloud -> Viewport. Phase 1 builds the entire spine. Phase 2 enriches it. Phase 3 differentiates it.
- **Each phase delivers a usable artifact.** Phase 1: "I can see my photos as a point cloud." Phase 2: "I can sculpt and explore." Phase 3: "The system helps me discover."

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Needs research on PySide6 + rendercanvas WgpuWidget integration specifics (working examples exist but are sparse). Also needs hands-on validation of ONNX model conversion and DirectML operator support for Depth Anything V2 and CLIP.
- **Phase 3:** Discovery mode has no established pattern in desktop tools. The "feature distribution -> aesthetic mapping proposal" algorithm is novel and will require experimentation. Claude API prompt engineering for artistic direction is also uncharted.

Phases with standard patterns (skip deep research):
- **Phase 2:** Point cloud rendering with LOD, parameter controls via Qt signals/slots, particle systems with compute shaders -- all well-documented patterns with existing pygfx/wgpu examples and academic literature (Schutz et al.).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core rendering stack (pygfx, wgpu, PySide6) is well-documented and proven. ROCm on Windows is the uncertainty -- functional but young. DirectML fallback is solid. |
| Features | MEDIUM | Table stakes and P1 features are well-understood. P2 differentiators (Discovery mode, mapping editor) have sparse precedent in desktop tools. Competitor analysis is strong. |
| Architecture | MEDIUM | Individual components (pipeline, Feature Store, observer pattern) are standard. Their specific integration (pygfx in PySide6, ONNX+DirectML on AMD, wgpu compute shaders for particles) is bespoke and less documented. |
| Pitfalls | HIGH | Pitfalls are concrete, actionable, and verified against current sources. GPU ecosystem pitfalls (CP-1, CP-4) are especially well-documented given AMD's recent ROCm Windows push. |

**Overall confidence:** MEDIUM -- the individual pieces are proven, but this specific combination (AMD GPU + WebGPU rendering + ML feature extraction + desktop creative tool) has few direct precedents. Phase 1 exists specifically to validate the integration.

### Gaps to Address

- **PySide6 + pygfx real-world performance**: The rendercanvas WgpuWidget is documented but real-world performance with complex scenes and simultaneous GUI interaction needs hands-on validation.
- **Depth Anything V2 ONNX export on DirectML**: V2 is proven on CUDA. ONNX export exists but DirectML operator coverage for this specific model needs testing on RX 9060 XT hardware.
- **WGSL compute shader development experience**: Writing particle physics in WGSL is possible but tooling (debugging, profiling) is immature compared to CUDA/GLSL. Development velocity is uncertain.
- **Point cloud aesthetics**: The research covers technical rendering but not the artistic quality of point cloud sculptures. What makes a data sculpture "good" requires experimentation, not research.
- **Windows 11 TDR behavior**: Long-running GPU compute dispatches (>2s) can trigger Windows Timeout Detection and Recovery. May need registry adjustment for heavy extraction workloads.

## Sources

### Primary (HIGH confidence)
- [ROCm on Radeon/Ryzen -- PyTorch Windows Installation](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html)
- [ONNX Runtime DirectML Execution Provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [AMD GPUOpen -- ONNX DirectML Guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/)
- [pygfx GitHub + Documentation](https://github.com/pygfx/pygfx)
- [wgpu-py GitHub](https://github.com/pygfx/wgpu-py)
- [rendercanvas Qt Integration](https://rendercanvas.readthedocs.io/latest/backends.html)
- [Depth Anything V2 GitHub](https://github.com/DepthAnything/Depth-Anything-V2)
- [Rendering Point Clouds with Compute Shaders (Schutz et al.)](https://arxiv.org/pdf/2104.07526)
- [ROCm 7.2.0 Release Notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)

### Secondary (MEDIUM confidence)
- [AMD Blog -- Road to ROCm on Radeon](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html)
- [Magnopus: How We Render Extremely Large Point Clouds](https://www.magnopus.com/blog/how-we-render-extremely-large-point-clouds)
- [Codrops -- WebGPU Fluid Simulations](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/)
- [Refik Anadol -- NVIDIA AI Art Gallery](https://www.nvidia.com/en-us/research/ai-art-gallery/artists/refik-anadol/)
- [Dreamsheets -- Prompting for Discovery (ACM)](https://dl.acm.org/doi/10.1145/3613904.3642858)

### Tertiary (LOW confidence -- needs validation)
- Depth Anything V3 ONNX export stability (V3 released Nov 2025, limited ONNX conversion reports)
- Windows ML as DirectML successor (announced May 2025, compatibility extent unclear)
- WGSL compute shader performance for fluid simulation on RDNA 4 (theoretical, no benchmarks found)

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
