# Requirements: Apollo 7

**Defined:** 2026-03-14
**Core Value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, visually stunning 3D sculptures.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion

- [x] **INGEST-01**: User can load a single photo (JPEG, PNG, TIFF, RAW) into the pipeline
- [x] **INGEST-02**: User can batch-ingest an entire folder of photos with progress feedback
- [x] **INGEST-03**: User can view thumbnails and metadata of ingested photos in a library panel

### Feature Extraction

- [x] **EXTRACT-01**: Pipeline extracts dominant colors, gradients, and color distributions from each photo
- [x] **EXTRACT-02**: Pipeline extracts edges, contours, and geometric structure from each photo
- [x] **EXTRACT-03**: Pipeline generates monocular depth maps via Depth Anything V2 (ONNX/DirectML on AMD GPU)
- [x] **EXTRACT-04**: Pipeline extracts semantic features (objects, scenes, mood) via local CLIP/BLIP models
- [x] **EXTRACT-05**: User can view extracted features per photo (color palette, edge map, depth map, semantic tags)

### Collection Analysis

- [ ] **COLL-01**: Pipeline identifies patterns across photo collections (clustering, trends, outliers)
- [ ] **COLL-02**: User can visualize collection-level patterns (e.g., t-SNE/UMAP embedding space)
- [ ] **COLL-03**: Collection patterns feed into sculpture generation as compositional signals

### 3D Rendering & Visualization

- [x] **RENDER-01**: Pipeline generates 3D point clouds from extracted features (geometry, color, depth)
- [x] **RENDER-02**: Real-time 3D viewport with orbit, zoom, pan at 30+ FPS via Vulkan/wgpu
- [x] **RENDER-03**: Point cloud rendering with configurable size, color mapping, opacity, and additive blending
- [x] **RENDER-04**: GPU-computed particle system with physically-based dynamics (forces, flow fields, fluid sim)
- [x] **RENDER-05**: Post-processing effects for aesthetic quality (bloom/glow, depth-of-field, ambient occlusion)
- [x] **RENDER-06**: Render-then-interact pattern -- heavy GPU compute produces output, then viewport is lightweight for smooth exploration
- [x] **RENDER-07**: Parameter animation via LFOs, noise functions, and envelopes mapped to any visual parameter

### Generative Models & Simulation

- [x] **SIM-01**: Research and integrate best-in-class particle/generative models for visually compelling output
- [x] **SIM-02**: GPU-accelerated fluid dynamics simulation (SPH or Navier-Stokes solver via compute shaders)
- [x] **SIM-03**: Flow field generation from extracted features driving particle motion
- [x] **SIM-04**: Sculptures must be visually pleasing and artistic -- aesthetic quality is a hard requirement, not a nice-to-have

### Creative Controls

- [x] **CTRL-01**: Parameter panel with sliders, color pickers, and numeric inputs that update viewport in real-time
- [x] **CTRL-02**: Feature-to-visual mapping editor -- user can route extracted features to visual parameters
- [x] **CTRL-03**: Undo/redo on all parameter changes
- [x] **CTRL-04**: Save/load full project state (parameters, feature data, sculpture configuration)
- [x] **CTRL-05**: Export high-res still images (2x, 4x viewport resolution, transparent background option)
- [x] **CTRL-06**: Preset library -- save, load, and organize named parameter presets
- [x] **CTRL-07**: Preset interpolation -- smoothly blend between saved presets

### Discovery & AI

- [x] **DISC-01**: Local discovery mode -- randomized but constrained parameter exploration with "more/less like this" feedback loop (no API required)
- [ ] **DISC-02**: Optional Claude API integration for semantic photo annotation (describe what's in photos -- mood, objects, narrative)
- [ ] **DISC-03**: Optional Claude API creative direction (suggest how to map extracted features to visual forms)
- [ ] **DISC-04**: All core functionality works fully offline -- Claude API is additive enrichment only

### Desktop Application

- [x] **APP-01**: Desktop GUI built with PySide6 -- professional layout with docking panels
- [x] **APP-02**: Runs on Windows 11 with AMD RX 9060 XT (RDNA 4) -- no CUDA dependencies
- [x] **APP-03**: Full GPU/CPU/RAM utilization for generation (hours-long runs acceptable)
- [x] **APP-04**: UI remains responsive during long generation runs (background compute, foreground interaction)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Output Formats

- **OUT-01**: Export animated sequences as video (MP4/WebM)
- **OUT-02**: Export point cloud data for use in other 3D tools (PLY, LAS)

### Advanced Rendering

- **ADV-01**: Multiple simultaneous viewports (front/side/top/perspective)
- **ADV-02**: VR viewport output for immersive exploration
- **ADV-03**: Audio-reactive parameter modulation

### Input Expansion

- **INP-01**: Video frame extraction as input source
- **INP-02**: Real-time camera feed processing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Text-to-image / prompt-based generation | Apollo 7 transforms DATA, not prompts. This is Stable Diffusion territory |
| Node-based visual programming | TouchDesigner does this. Apollo 7's value is the integrated GUI workflow |
| Plugin/extension system | Premature abstraction -- hardcode features in v1, consider plugins v2+ |
| Cloud rendering | Contradicts local-first philosophy. Desktop GPU is more than capable |
| Mesh generation / 3D printing export | Point cloud to manifold mesh is a deep rabbit hole. Stay in particle/point territory |
| Multi-user collaboration | Desktop creative tool for solo artists |
| Social sharing / gallery | Export images; users choose their own sharing platform |
| Mobile app | Desktop only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Complete |
| INGEST-02 | Phase 1 | Complete |
| INGEST-03 | Phase 1 | Complete |
| EXTRACT-01 | Phase 1 | Complete |
| EXTRACT-02 | Phase 1 | Complete |
| EXTRACT-03 | Phase 1 | Complete |
| EXTRACT-04 | Phase 3 | Complete |
| EXTRACT-05 | Phase 2 | Complete |
| COLL-01 | Phase 3 | Pending |
| COLL-02 | Phase 3 | Pending |
| COLL-03 | Phase 3 | Pending |
| RENDER-01 | Phase 1 | Complete |
| RENDER-02 | Phase 1 | Complete |
| RENDER-03 | Phase 1 | Complete |
| RENDER-04 | Phase 2 | Complete |
| RENDER-05 | Phase 2 | Complete |
| RENDER-06 | Phase 2 | Complete |
| RENDER-07 | Phase 3 | Complete |
| SIM-01 | Phase 2 | Complete |
| SIM-02 | Phase 2 | Complete |
| SIM-03 | Phase 2 | Complete |
| SIM-04 | Phase 2 | Complete |
| CTRL-01 | Phase 2 | Complete |
| CTRL-02 | Phase 3 | Complete |
| CTRL-03 | Phase 2 | Complete |
| CTRL-04 | Phase 2 | Complete |
| CTRL-05 | Phase 2 | Complete |
| CTRL-06 | Phase 2 | Complete |
| CTRL-07 | Phase 3 | Complete |
| DISC-01 | Phase 3 | Complete |
| DISC-02 | Phase 3 | Pending |
| DISC-03 | Phase 3 | Pending |
| DISC-04 | Phase 3 | Pending |
| APP-01 | Phase 1 | Complete |
| APP-02 | Phase 1 | Complete |
| APP-03 | Phase 1 | Complete |
| APP-04 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation*
