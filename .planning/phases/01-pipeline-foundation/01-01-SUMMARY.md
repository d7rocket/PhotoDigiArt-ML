---
phase: 01-pipeline-foundation
plan: 01
subsystem: ui, rendering
tags: [pyside6, pygfx, wgpu, qt, 3d-viewport, gaussian-blob, orbit-controls]

# Dependency graph
requires: []
provides:
  - "PySide6 desktop app skeleton with dark theme and custom QSS"
  - "pygfx 3D viewport embedded in Qt via rendercanvas QRenderWidget"
  - "Gaussian blob point rendering with orbit/zoom/pan controls"
  - "Project config, settings module, and test infrastructure"
  - "BLEND_MODE_AVAILABLE flag for downstream blending decisions"
affects: [01-02, 01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: [PySide6, pygfx, wgpu, rendercanvas, onnxruntime-directml, opencv-python-headless, numpy, scipy, Pillow, extcolors, pytest, ruff]
  patterns: [QRenderWidget embedding for pygfx-in-Qt, QSS dark theme with accent color, OrbitController camera, settings module with typed constants]

key-files:
  created:
    - pyproject.toml
    - apollo7/__init__.py
    - apollo7/__main__.py
    - apollo7/app.py
    - apollo7/config/settings.py
    - apollo7/gui/main_window.py
    - apollo7/gui/theme.py
    - apollo7/gui/widgets/viewport_widget.py
    - apollo7/rendering/camera.py
    - tests/conftest.py
    - tests/test_gpu_providers.py
  modified: []

key-decisions:
  - "Alpha falloff workaround for additive blending (BLEND_MODE_AVAILABLE=False) -- pygfx PointsGaussianBlobMaterial does not expose blend_mode; using alpha=0.7 with Gaussian falloff for soft overlap glow"
  - "Used rendercanvas.qt.QRenderWidget for pygfx embedding -- proven integration path from research"
  - "Segoe UI font in QSS theme for native Windows feel"

patterns-established:
  - "Settings as module-level constants in apollo7/config/settings.py"
  - "QSS theme loaded via load_theme_qss() and applied to QApplication"
  - "ViewportWidget as reusable pygfx container with add_points/clear_points/auto_frame API"
  - "CameraController wrapping pygfx OrbitController with default viewing angle"

requirements-completed: [APP-01, APP-02, RENDER-02, RENDER-03]

# Metrics
duration: ~5min
completed: 2026-03-14
---

# Phase 1 Plan 01: Project Setup and 3D Viewport Summary

**PySide6 desktop app with dark theme, embedded pygfx 3D viewport rendering 10K Gaussian blob points with orbit/zoom/pan, and alpha-falloff blending workaround**

## Performance

- **Duration:** ~5 min (across execution sessions)
- **Started:** 2026-03-14T14:57:00Z
- **Completed:** 2026-03-14T15:03:18Z
- **Tasks:** 3 (2 auto + 1 human-verify)
- **Files created:** 17

## Accomplishments
- Launchable desktop app via `python -m apollo7` with full dark theme and electric blue accent
- pygfx 3D viewport embedded in Qt rendering 10,000 Gaussian blob points in a sphere with vertex colors
- Orbit, zoom, and pan camera controls working smoothly via OrbitController
- Additive blending validated: pygfx does not expose blend_mode on PointsGaussianBlobMaterial; alpha=0.7 falloff workaround produces acceptable soft glow overlap (BLEND_MODE_AVAILABLE=False documented for Plan 05)
- Test infrastructure with pytest, GPU provider smoke tests, and import verification all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Project bootstrap, config, settings, and test infrastructure** - `3258fb8` (feat)
2. **Task 2: GUI skeleton, dark theme, viewport widget, camera, and blending validation** - `6bbdbec` (feat)
3. **Task 3: Human verification of GUI, viewport, and blending quality** - approved by user (no code commit)

## Files Created/Modified
- `pyproject.toml` - Project config with all dependencies (pygfx, PySide6, wgpu, onnxruntime-directml, etc.)
- `apollo7/__init__.py` - Package init
- `apollo7/__main__.py` - Entry point for `python -m apollo7`
- `apollo7/app.py` - QApplication bootstrap with theme application
- `apollo7/config/__init__.py` - Config package init
- `apollo7/config/settings.py` - Typed constants (point size, colors, window size, LOD thresholds)
- `apollo7/gui/__init__.py` - GUI package init
- `apollo7/gui/main_window.py` - MainWindow with splitter layout (viewport 73% / panels 27%)
- `apollo7/gui/theme.py` - Comprehensive dark QSS theme with electric blue accent
- `apollo7/gui/widgets/__init__.py` - Widgets package init
- `apollo7/gui/widgets/viewport_widget.py` - pygfx viewport with Gaussian blob points, blending validation
- `apollo7/rendering/__init__.py` - Rendering package init
- `apollo7/rendering/camera.py` - CameraController wrapping OrbitController
- `apollo7/rendering/viewport.py` - Viewport module placeholder
- `tests/__init__.py` - Tests package init
- `tests/conftest.py` - Pytest fixtures (tmp_dir, sample_image)
- `tests/test_gpu_providers.py` - GPU provider and import smoke tests

## Decisions Made
- **Blending workaround:** pygfx PointsGaussianBlobMaterial does not support a blend_mode parameter. Used alpha=0.7 on point colors combined with Gaussian falloff to achieve soft additive-like glow. Documented as BLEND_MODE_AVAILABLE=False for Plan 05 controls wiring.
- **rendercanvas.qt.QRenderWidget:** Used as the embedding strategy for pygfx in Qt, matching research recommendation.
- **Segoe UI font:** Chosen for QSS theme to match Windows 11 native feel.

## Deviations from Plan

None - plan executed as written. The alpha falloff blending workaround was an explicitly planned contingency path in the plan's Task 2 Step 3.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- App skeleton ready for photo ingestion (Plan 02: drag-drop, library panel)
- Viewport API (add_points/clear_points/auto_frame) ready for real point cloud data (Plan 04-05)
- Settings module ready for controls integration (Plan 05)
- BLEND_MODE_AVAILABLE=False flag ready for Plan 05 opacity control wiring

## Self-Check: PASSED

All 11 key files verified present. Both task commits (3258fb8, 6bbdbec) confirmed in git history.

---
*Phase: 01-pipeline-foundation*
*Completed: 2026-03-14*
