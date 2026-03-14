---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 02-05-PLAN.md
last_updated: "2026-03-14T17:19:04Z"
last_activity: 2026-03-14 -- Plan 02-05 complete (project save/load, export, presets)
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 11
  completed_plans: 10
  percent: 82
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, visually stunning 3D sculptures.
**Current focus:** Phase 2: Creative Sculpting

## Current Position

Phase: 2 of 3 (Creative Sculpting)
Plan: 5 of 6 in current phase (02-05 complete)
Status: In progress
Last activity: 2026-03-14 -- Plan 02-05 complete (project save/load, export, presets)

Progress: [████████░░] 82%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~5 min
- Total execution time: ~0.4 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 - Pipeline Foundation | 5/5 | ~27 min | ~5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~5 min), 01-02 (~4 min), 01-03 (~3 min), 01-04 (~3 min), 01-05 (~12 min)
- Trend: Stable (01-05 larger due to integration + checkpoint)

*Updated after each plan completion*
| Phase 02 P01 | 8min | 3 tasks | 14 files |
| Phase 02 P04 | 6min | 2 tasks | 12 files |
| Phase 02 P03 | 7min | 2 tasks | 8 files |
| Phase 02 P05 | 6min | 2 tasks | 12 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 3-phase coarse structure -- Foundation, Creative Sculpting, Discovery
- [Roadmap]: Semantic extraction (CLIP/BLIP) deferred to Phase 3 with discovery features
- [Roadmap]: Feature-to-visual mapping editor deferred to Phase 3 (differentiator, not core tool)
- [01-01]: Alpha falloff workaround for blending (BLEND_MODE_AVAILABLE=False) -- pygfx lacks blend_mode on PointsGaussianBlobMaterial
- [01-01]: rendercanvas.qt.QRenderWidget used for pygfx-in-Qt embedding
- [01-03]: extcolors tolerance=32, limit=12 for dominant color extraction
- [01-03]: Canny thresholds (50/150) configurable via EdgeExtractor constructor
- [01-03]: Cache keyed by (photo_path, extractor_name) tuple
- [01-02]: PIL-to-QPixmap via in-memory PNG buffer in main thread (Qt pixmap creation requirement)
- [01-02]: Header-based format detection via Pillow, not file extension
- [01-02]: WorkerSignals QObject pattern for QRunnable signal emission
- [01-04]: Lazy ONNX session loading (first extract() call, not import time)
- [01-04]: DirectML fallback with warning (don't crash if GPU unavailable)
- [01-04]: Blue-to-yellow depth colormap via pure numpy (no matplotlib)
- [01-04]: Grid-based LOD: divide space into cells, keep closest-to-center point
- [01-05]: ExtractionWorker generates arrays in background, scene modification in main thread (pygfx thread safety)
- [01-05]: Per-photo cloud tracking via dict keyed by photo path for selective removal/regeneration
- [01-05]: Layout/multi-photo mode changes regenerate from stored results (no re-extraction)
- [01-05]: UI polish deferred to later iteration per user feedback
- [02-02]: Merge ID offset per parameter (0=point_size, 1=opacity, 2=depth_exag) for selective merge
- [02-02]: FeatureViewerPanel replaces FeatureStripPanel in layout (strip kept for backward compat)
- [02-02]: QPainter-based histogram and swatch rendering (no matplotlib dependency)
- [Phase 02-01]: 112-byte uniform struct with 7x vec4 layout for WGSL alignment
- [Phase 02-01]: Chunked dispatch 256K particles/chunk for AMD TDR prevention
- [Phase 02-01]: Spatial hash grid 128^3 with 64-unit offset centering at origin
- [Phase 02-01]: SimulationParams.with_update() immutable update for hot-reload pattern
- [Phase 02]: Bloom uses pygfx PhysicalBasedBloomPass (strength 0.04 default)
- [Phase 02]: DoF/SSAO as param controllers (pygfx EffectPass API not public for custom shaders)
- [Phase 02]: Trails via ghost point history with alpha decay (not framebuffer accumulation)
- [Phase 02]: PostFX undo merge_id offsets 100+ to avoid sim param collision
- [Phase 02]: 14 sim parameter sliders with compound param decomposition (gravity_y -> gravity tuple)
- [Phase 02]: CPU readback prototype for sim-to-pygfx geometry update (optimize later)
- [Phase 02-05]: JSON project file format (.apollo7) for human readability
- [Phase 02-05]: Built-in presets in 4 categories (5 starter presets)
- [Phase 02-05]: Offscreen wgpu canvas for PNG export with transparent bg support
- [Phase 02-05]: Point cloud snapshot in project file for instant visual on load

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: ROCm on Windows is functional but young -- Phase 1 must validate GPU paths early
- [Resolved]: PySide6 + pygfx/wgpu integration proven working in 01-01 via QRenderWidget

## Session Continuity

Last session: 2026-03-14T17:19:04Z
Stopped at: Completed 02-05-PLAN.md
Resume file: None
