---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-03-15T04:58:05.549Z"
last_activity: 2026-03-15 -- Plan 03-01 complete (CLIP semantic extraction with tokenizer and feature viewer)
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 20
  completed_plans: 16
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, visually stunning 3D sculptures.
**Current focus:** Phase 2 complete -- ready for Phase 3: Discovery and Intelligence

## Current Position

Phase: 3 of 3 (Discovery and Intelligence)
Plan: 1 of 7 in current phase (03-01 complete)
Status: Executing Phase 3
Last activity: 2026-03-15 -- Plan 03-01 complete (CLIP semantic extraction with tokenizer and feature viewer)

Progress: [██████████████] 100% (phases 1-2) + Plan 1/7 in Phase 3

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
| Phase 02 P06 | 2min | 1 task (checkpoint) | 0 files |
| Phase 02 P07 | 4min | 2 tasks | 3 files |
| Phase 02 P08 | 1min | 1 tasks | 2 files |
| Phase 03 P03 | 4min | 2 tasks | 5 files |
| Phase 03 P02 | 5min | 3 tasks | 8 files |
| Phase 03 P01 | 5min | 2 tasks | 9 files |

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
- [Phase 02-06]: Partial approval -- flow field forces (speed, turbulence, gravity, wind) verified; attraction/repulsion/SPH not yet in shader
- [Phase 02-06]: User accepted current simulation state as sufficient quality gate for Phase 2
- [Phase 02]: CPU spatial hash build on init/restart only (not per-frame GPU hash)
- [Phase 02]: Multi-pass GPU dispatch with separate command encoder per pass for synchronization
- [Phase 02]: Renamed test methods to document all-visual design decision from d2f401c
- [Phase 03]: Dot-path key navigation for flexible feature addressing in mapping engine
- [Phase 03]: Fixed two-column node layout (features left, params right) for patch bay editor
- [Phase 03]: Additive blending for multiple connections to same target parameter
- [Phase 03]: Hash-based deterministic noise with smoothstep interpolation (no external Perlin library)
- [Phase 03]: AnimationBinding normalizes generator output to [0,1] then maps to [min_val, max_val]
- [Phase 03]: Crossfade re-uses preset_applied signal for lerped params (no new main window wiring needed)
- [Phase 03]: CLIP ViT-B/32 via ONNX for semantic extraction with pure Python BPE tokenizer (no torch)

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: ROCm on Windows is functional but young -- Phase 1 must validate GPU paths early
- [Resolved]: PySide6 + pygfx/wgpu integration proven working in 01-01 via QRenderWidget

## Session Continuity

Last session: 2026-03-15T04:57:52.527Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
