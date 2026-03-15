# Requirements: Apollo 7

**Defined:** 2026-03-14
**Core Value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, visually stunning 3D sculptures.

## v1.0 Requirements (Validated)

All v1.0 requirements shipped. See v1.0 milestone archive for details.

### Ingestion -- Complete
- [x] **INGEST-01**: User can load a single photo (JPEG, PNG, TIFF, RAW) -- Phase 1
- [x] **INGEST-02**: User can batch-ingest an entire folder of photos -- Phase 1
- [x] **INGEST-03**: User can view thumbnails and metadata in library panel -- Phase 1

### Feature Extraction -- Complete
- [x] **EXTRACT-01**: Pipeline extracts dominant colors, gradients, color distributions -- Phase 1
- [x] **EXTRACT-02**: Pipeline extracts edges, contours, geometric structure -- Phase 1
- [x] **EXTRACT-03**: Pipeline generates depth maps via Depth Anything V2 -- Phase 1
- [x] **EXTRACT-04**: Pipeline extracts semantic features via CLIP -- Phase 3
- [x] **EXTRACT-05**: User can view extracted features per photo -- Phase 2

### Collection Analysis -- Complete
- [x] **COLL-01**: Pipeline identifies patterns across collections -- Phase 3
- [x] **COLL-02**: User can visualize collection-level patterns -- Phase 3
- [x] **COLL-03**: Collection patterns feed into sculpture generation -- Phase 3

### 3D Rendering -- Complete
- [x] **RENDER-01** through **RENDER-07**: Point clouds, viewport, particles, post-processing, animation -- Phases 1-3

### Simulation -- Complete
- [x] **SIM-01** through **SIM-04**: Particle models, fluid sim, flow fields -- Phase 2

### Creative Controls -- Complete
- [x] **CTRL-01** through **CTRL-07**: Parameter panel, mapping editor, undo/redo, save/load, export, presets -- Phases 2-3

### Discovery & AI -- Complete
- [x] **DISC-01** through **DISC-04**: Discovery mode, Claude API, offline-first -- Phase 3

### Desktop Application -- Complete
- [x] **APP-01** through **APP-04**: PySide6 GUI, AMD GPU, responsive UI -- Phase 1

## v2.0 Requirements

Requirements for v2.0 "Make It Alive". Each maps to roadmap phases.

### Physics & Simulation

- [x] **PHYS-01**: Particles maintain coherent form via per-particle home position attraction instead of dispersing into chaos
- [x] **PHYS-02**: PBF (Position Based Fluids) solver replaces SPH with unconditionally stable constraint resolution
- [x] **PHYS-03**: Spatial hash rebuilds every frame on GPU so neighbor lookups remain correct during motion
- [x] **PHYS-04**: Force and velocity clamping prevents runaway acceleration
- [x] **PHYS-05**: CFL-adaptive timestep adjusts step size based on maximum particle velocity
- [x] **PHYS-06**: Curl noise flow fields produce smooth, organic particle motion
- [x] **PHYS-07**: Vortex confinement adds swirling, turbulent detail to particle motion
- [x] **PHYS-08**: Breathing modulation (sine wave on home_strength/noise_amplitude) makes sculptures feel alive
- [x] **PHYS-09**: Solver iterations parameter acts as creative control (1=gas/wispy, 4+=liquid/cohesive)

### Rendering Quality

- [x] **REND-01**: Particles render as round, soft points instead of hard squares
- [x] **REND-02**: Viewport uses white background by default
- [x] **REND-03**: Additive blending creates luminous, glowing particle clusters
- [x] **REND-04**: Bloom/glow post-processing enhances particle aesthetics
- [x] **REND-05**: GPU buffer sharing eliminates CPU readback bottleneck for 1M+ particles
- [ ] **REND-06**: Parameter changes crossfade smoothly instead of popping

### UI & UX

- [ ] **UI-01**: Clean, logical panel layout with clear visual hierarchy
- [ ] **UI-02**: Tiered parameter controls -- 6 essential sliders visible, advanced collapsed
- [ ] **UI-03**: qt-material theming for polished, modern appearance
- [ ] **UI-04**: Parameter presets with visual thumbnails for quick selection

### Claude Creative Direction

- [ ] **CLAU-01**: Claude analyzes loaded photo(s) and suggests parameter sets for organic sculptures
- [ ] **CLAU-02**: Structured outputs via Pydantic ensure Claude returns valid, bounded parameters
- [ ] **CLAU-03**: Suggested parameters crossfade into viewport smoothly on apply
- [ ] **CLAU-04**: Iterative "more/less like this" refinement loop with Claude

### Depth & Extraction

- [x] **DPTH-01**: Depth maps use CLAHE post-processing for proper saturation and contrast
- [x] **DPTH-02**: Depth-to-color mapping uses richer, more expressive color range

## Future Requirements

Deferred beyond v2.0. Tracked but not in current roadmap.

### Output Formats
- **OUT-01**: Export animated sequences as video (MP4/WebM)
- **OUT-02**: Export point cloud data for use in other 3D tools (PLY, LAS)

### Advanced Rendering
- **ADV-01**: Multiple simultaneous viewports
- **ADV-02**: VR viewport output for immersive exploration
- **ADV-03**: Audio-reactive parameter modulation

### Input Expansion
- **INP-01**: Video frame extraction as input source
- **INP-02**: Real-time camera feed processing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replace pygfx/wgpu rendering engine | Research confirmed current stack is correct; problems are physics, not rendering |
| Replace PySide6 GUI framework | pygfx integration works; theme with qt-material instead |
| Taichi Lang integration | Cannot share GPU buffers with wgpu/pygfx -- CPU roundtrip kills performance |
| NVIDIA Warp | CUDA-only, incompatible with AMD RDNA 4 |
| Text-to-image / prompt-based generation | Apollo 7 transforms DATA, not prompts |
| Node-based visual programming | TouchDesigner does this; Apollo 7's value is integrated GUI |
| Cloud rendering | Local-first philosophy; desktop GPU is capable |
| Mobile app | Desktop only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PHYS-01 | Phase 4 | Complete |
| PHYS-02 | Phase 4 | Complete |
| PHYS-03 | Phase 4 | Complete |
| PHYS-04 | Phase 4 | Complete |
| PHYS-05 | Phase 4 | Pending |
| PHYS-06 | Phase 4 | Complete |
| PHYS-07 | Phase 4 | Complete |
| PHYS-08 | Phase 4 | Complete |
| PHYS-09 | Phase 4 | Complete |
| REND-01 | Phase 5 | Complete |
| REND-02 | Phase 5 | Complete |
| REND-03 | Phase 5 | Complete |
| REND-04 | Phase 5 | Complete |
| REND-05 | Phase 5 | Complete |
| REND-06 | Phase 5 | Pending |
| DPTH-01 | Phase 5 | Complete |
| DPTH-02 | Phase 5 | Complete |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| UI-04 | Phase 6 | Pending |
| CLAU-01 | Phase 6 | Pending |
| CLAU-02 | Phase 6 | Pending |
| CLAU-03 | Phase 6 | Pending |
| CLAU-04 | Phase 6 | Pending |

**Coverage:**
- v2.0 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-14 (v1.0), updated 2026-03-15 (v2.0)*
*Last updated: 2026-03-15 after v2.0 roadmap creation*
