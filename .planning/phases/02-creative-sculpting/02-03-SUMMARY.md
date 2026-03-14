---
phase: 02-creative-sculpting
plan: 03
subsystem: ui
tags: [simulation-controls, FPS-counter, PySide6, sliders, undo-redo, keyboard-shortcuts]

requires:
  - phase: 02-creative-sculpting
    provides: "SimulationEngine with lifecycle/param API (Plan 01), ParameterChangeCommand undo system (Plan 02)"
provides:
  - "SimulationPanel with 14 parameter sliders in collapsible sections"
  - "FPSCounter overlay widget with averaged frame timing"
  - "Simulate/Pause/Resume lifecycle wiring between GUI and engine"
  - "Space bar pause/resume keyboard shortcut"
  - "Compound param routing (gravity_y, wind_x, wind_z)"
  - "Simulation parameter settings constants"
affects: [02-creative-sculpting, export, performance-tuning]

tech-stack:
  added: []
  patterns:
    - "Compound param decomposition (gravity_y -> gravity tuple update)"
    - "FPSCounter with averaged frame timing (0.5s update interval)"
    - "Collapsible QGroupBox sections with checkable toggle"
    - "CPU readback prototype for sim->pygfx geometry update"

key-files:
  created:
    - apollo7/gui/panels/simulation_panel.py
    - apollo7/gui/widgets/fps_counter.py
    - tests/test_sim_panel.py
    - tests/test_sim_lifecycle.py
  modified:
    - apollo7/gui/widgets/viewport_widget.py
    - apollo7/gui/main_window.py
    - apollo7/config/settings.py
    - apollo7/gui/theme.py

key-decisions:
  - "14 simulation parameter sliders matching SimulationParams field names exactly"
  - "Compound params gravity_y/wind_x/wind_z decomposed to tuple updates in update_sim_param"
  - "Merge ID offsets 10+ for simulation params (0-2 used by rendering sliders)"
  - "CPU readback prototype for sim buffer to pygfx geometry (optimize later with direct buffer sharing)"
  - "FPS counter update interval 0.5s with averaged frame timing"

patterns-established:
  - "SimulationPanel: _create_slider with param_name property for auto signal routing"
  - "Compound param routing: sub-component params (gravity_y) -> engine tuple (gravity)"
  - "Simulation lifecycle: init_simulation -> start_simulation -> toggle_pause via viewport"

requirements-completed: [CTRL-01, RENDER-06]

duration: 7min
completed: 2026-03-14
---

# Phase 2 Plan 03: Simulation Controls & Viewport Wiring Summary

**SimulationPanel with 14 force/speed/turbulence sliders in collapsible sections, FPS counter overlay, Simulate/Pause lifecycle wiring, Space bar shortcut, and undo-wrapped parameter changes routing to GPU simulation engine**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-14T17:04:26Z
- **Completed:** 2026-03-14T17:11:17Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- SimulationPanel with 4 collapsible sections (Control, Flow Field, Forces, Fluid/SPH) containing 14 parameter sliders
- FPSCounter overlay widget with averaged frame timing and semi-transparent dark background
- Full lifecycle wiring: Simulate button collects point cloud + feature textures, initializes engine, starts animation
- Keyboard shortcuts: Space (pause/resume), Ctrl+S (save placeholder), Ctrl+E (export placeholder)
- 25 tests passing covering panel signals, param-name alignment, FPS counter behavior, and lifecycle state machine

## Task Commits

Each task was committed atomically:

1. **Task 1: Simulation controls panel and FPS counter** - `cae5910` (feat)
2. **Task 2: Wire simulation engine to viewport and controls** - `97521ab` (feat)

## Files Created/Modified
- `apollo7/gui/panels/simulation_panel.py` - SimulationPanel with 14 sliders in collapsible sections, per-section and global reset
- `apollo7/gui/widgets/fps_counter.py` - FPSCounter overlay with averaged 0.5s frame timing
- `apollo7/gui/widgets/viewport_widget.py` - Simulation engine integration, FPS counter, _update_points_from_sim
- `apollo7/gui/main_window.py` - SimulationPanel in right splitter, signal wiring, keyboard shortcuts, _on_simulate
- `apollo7/config/settings.py` - 30 simulation parameter range/default constants
- `apollo7/gui/theme.py` - Simulation panel, reset button, FPS counter QSS styles
- `tests/test_sim_panel.py` - 15 tests for panel widget and FPS counter
- `tests/test_sim_lifecycle.py` - 10 tests for lifecycle state machine and param routing

## Decisions Made
- 14 simulation parameter sliders with param_name matching SimulationParams fields exactly (speed, turbulence_scale, noise_frequency, etc.)
- Compound params gravity_y, wind_x, wind_z decomposed to gravity/wind tuple updates in update_sim_param
- Merge ID offsets start at 10 for simulation params (0-2 used by rendering, 100+ used by postfx)
- CPU readback fallback for sim->pygfx geometry (direct buffer sharing optimized later)
- FPS counter updates every 0.5 seconds with averaged frame timing for stable readout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Simulation controls panel fully wired to engine with undo support
- FPS counter showing frame rate in viewport corner
- Space bar shortcut for pause/resume ready
- CPU readback prototype functional; direct buffer sharing optimization deferred
- All 25 tests passing, imports verified

## Self-Check: PASSED

- All 4 created files verified present on disk
- All 2 task commits verified in git log (cae5910, 97521ab)

---
*Phase: 02-creative-sculpting*
*Completed: 2026-03-14*
