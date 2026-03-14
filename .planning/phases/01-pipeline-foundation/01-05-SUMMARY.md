---
phase: 01-pipeline-foundation
plan: 05
subsystem: integration, ui, rendering
tags: [qrunnable, qthreadpool, progressive-build, point-cloud, controls-panel, sliders, layout-modes, multi-photo]

# Dependency graph
requires:
  - phase: 01-02
    provides: "Photo ingestion pipeline, library panel, progress bar"
  - phase: 01-03
    provides: "Color/edge extractors, feature cache, feature strip panel"
  - phase: 01-04
    provides: "Depth extractor, extraction pipeline, point cloud generator, LOD"
provides:
  - "ExtractionWorker: background extraction + point cloud generation per photo"
  - "Progressive viewport build: point cloud grows as each photo completes"
  - "Per-photo cloud management: add, remove, regenerate individual photo clouds"
  - "Controls panel with point size, opacity, depth exaggeration sliders"
  - "Layout mode toggle (depth-projected / feature-clustered) with regeneration"
  - "Multi-photo mode toggle (stacked layers / merged cloud)"
  - "Full end-to-end wiring: load photos -> extract -> view 3D sculpture"
affects: [02-creative-sculpting]

# Tech tracking
tech-stack:
  added: []
  patterns: [ExtractionWorker with pipeline+generator in background thread, per-photo cloud management with tagged scene objects, slider-to-viewport real-time binding, layout regeneration on mode switch]

key-files:
  created:
    - apollo7/workers/extraction_worker.py
  modified:
    - apollo7/gui/main_window.py
    - apollo7/gui/widgets/viewport_widget.py
    - apollo7/gui/panels/controls_panel.py
    - apollo7/rendering/camera.py
    - apollo7/config/settings.py
    - apollo7/extraction/depth.py
    - apollo7/gui/theme.py

key-decisions:
  - "ExtractionWorker generates point cloud in background thread, arrays added to scene in main thread"
  - "Per-photo cloud tracking via dict keyed by photo path for selective removal and regeneration"
  - "Slider range 0-100 ticks mapped to float ranges for smooth control"
  - "Layout/multi-photo mode changes clear all clouds and regenerate from stored results"
  - "Depth exaggeration slider triggers full cloud regeneration (not just material update)"
  - "Removed test sphere from viewport -- real data comes from extraction pipeline"

patterns-established:
  - "ExtractionWorker pattern: pipeline + generator in QRunnable with photo_complete signal"
  - "Per-photo cloud management: add_photo_cloud/remove_photo_cloud with scene tagging"
  - "Slider-to-viewport binding: controls emit typed signals, main window connects to viewport methods"
  - "Layout regeneration: mode change -> clear clouds -> regenerate from stored results"

requirements-completed: [APP-03, APP-04, RENDER-03]

# Metrics
duration: ~12min
completed: 2026-03-14
---

# Phase 1 Plan 05: End-to-End Pipeline Integration Summary

**ExtractionWorker with progressive viewport build, per-photo cloud management, and real-time controls panel with point size/opacity/depth exaggeration sliders and layout mode switching**

## Performance

- **Duration:** ~12 min (including checkpoint verification)
- **Started:** 2026-03-14T15:20:34Z
- **Completed:** 2026-03-14T15:48:38Z
- **Tasks:** 2 of 2
- **Files created:** 1
- **Files modified:** 7

## Accomplishments
- ExtractionWorker runs full pipeline (color, edges, depth) + point cloud generation in background thread with progressive photo_complete signals
- ViewportWidget upgraded with per-photo cloud management (add/remove/regenerate), layout mode switching, multi-photo mode, and real-time material updates
- ControlsPanel fully wired with Extract Features button, Re-extract button, layout/multi-photo radio toggles, and three rendering sliders (point size, opacity, depth exaggeration)
- MainWindow orchestrates the complete pipeline: load photos -> extract -> progressive viewport build -> interactive controls
- Camera auto-frames with three-quarter view after each photo addition
- All existing tests pass
- Human-verified end-to-end pipeline approved (UI polish deferred to later iteration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extraction worker, progressive viewport build, and controls wiring** - `8a750f3` (feat)
2. **Task 2: Verify complete end-to-end pipeline** - human-verify checkpoint approved

**Bug fix commits (post-Task 1, pre-approval):**
- `a586ccd` - fix ONNX dynamic shapes (depth.py) and empty scene auto_frame (viewport_widget.py)
- `b901719` - add radio button and checkbox theme styles (theme.py)

## Files Created/Modified
- `apollo7/workers/extraction_worker.py` - Background extraction + point cloud generation worker with progressive signals
- `apollo7/gui/main_window.py` - Full end-to-end wiring: ingestion, extraction, progressive build, controls, layout regeneration
- `apollo7/gui/widgets/viewport_widget.py` - Per-photo cloud management, layout/multi-photo modes, material updates, removed test sphere
- `apollo7/gui/panels/controls_panel.py` - Extract/re-extract buttons, layout/multi-photo toggles, point size/opacity/depth exaggeration sliders
- `apollo7/rendering/camera.py` - Three-quarter view method (azimuth 45 deg, elevation 30 deg)
- `apollo7/config/settings.py` - Added OPACITY_DEFAULT/RANGE, DEPTH_EXAGGERATION_RANGE constants
- `apollo7/extraction/depth.py` - Fixed ONNX dynamic input shapes for depth model inference
- `apollo7/gui/theme.py` - Added QRadioButton and QCheckBox theme styles for dark theme consistency

## Decisions Made
- ExtractionWorker generates point cloud arrays in background thread; arrays are added to pygfx scene in main thread (Qt/pygfx thread safety)
- Per-photo cloud tracking uses dict keyed by photo path, enabling selective removal and regeneration on mode switch
- Sliders use 0-100 integer ticks mapped to float ranges for smooth, responsive control
- Layout mode and multi-photo mode changes clear all clouds and regenerate from stored extraction results (not re-extract)
- Depth exaggeration changes trigger full cloud regeneration since positions change
- Removed the 10K test sphere from viewport -- real data now comes from extraction pipeline
- UI polish deferred to later iteration per user feedback

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ONNX dynamic input shapes for depth extraction**
- **Found during:** Post-Task 1 testing
- **Issue:** Depth Anything V2 ONNX model expected specific input dimensions; dynamic shapes caused inference failures
- **Fix:** Updated depth.py to handle dynamic shapes correctly
- **Files modified:** apollo7/extraction/depth.py
- **Committed in:** a586ccd

**2. [Rule 1 - Bug] Fixed empty scene auto-frame crash**
- **Found during:** Post-Task 1 testing
- **Issue:** Camera auto_frame failed when viewport scene had no points yet
- **Fix:** Added guard for empty scene in viewport_widget.py
- **Files modified:** apollo7/gui/widgets/viewport_widget.py
- **Committed in:** a586ccd

**3. [Rule 2 - Missing Critical] Added radio button and checkbox theme styles**
- **Found during:** Post-Task 1 testing
- **Issue:** New radio buttons and checkboxes in controls panel had no theme styling, breaking dark theme consistency
- **Fix:** Added styled QSS rules for QRadioButton and QCheckBox to theme.py
- **Files modified:** apollo7/gui/theme.py
- **Committed in:** b901719

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical)
**Impact on plan:** All fixes necessary for correct operation. No scope creep.

## Issues Encountered
- UI needs polish pass in a future iteration (acknowledged by user, not blocking for Phase 1)

## User Setup Required

None - no external service configuration required. Note: the Depth Anything V2 ONNX model file must be downloaded and placed at `models/depth_anything_v2_vits.onnx` for depth extraction. Without it, depth extraction will fail but color/edge extraction still works.

## Next Phase Readiness
- Phase 1 Pipeline Foundation is COMPLETE -- all 5 plans executed and verified
- Full end-to-end pipeline operational: load photos -> extract features -> 3D point cloud sculpture
- Controls panel enables interactive exploration with real-time parameter updates
- Ready for Phase 2: Creative Sculpting (particles, fluid sim, parameter controls, export)
- Known future work: UI polish pass, advanced blending modes

## Self-Check: PASSED

- All 8 files verified present on disk
- All 3 commits (8a750f3, a586ccd, b901719) verified in git history

---
*Phase: 01-pipeline-foundation*
*Completed: 2026-03-14*
