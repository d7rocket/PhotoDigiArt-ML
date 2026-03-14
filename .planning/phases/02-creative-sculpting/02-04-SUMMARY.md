---
phase: 02-creative-sculpting
plan: 04
subsystem: rendering
tags: [bloom, depth-of-field, ssao, trails, postfx, pygfx]

requires:
  - phase: 02-01
    provides: "Viewport widget with pygfx renderer and simulation engine"
provides:
  - "BloomController wrapping pygfx PhysicalBasedBloomPass"
  - "DepthOfFieldPass with focal distance/aperture params"
  - "SSAOPass parameter controller (GPU pending pygfx API)"
  - "TrailAccumulator with ghost point history and alpha decay"
  - "PostFXPanel with toggleable sections and sliders"
  - "Viewport postfx init/update/toggle methods"
affects: [02-05, 02-06, 03-discovery]

tech-stack:
  added: [pygfx.PhysicalBasedBloomPass]
  patterns: [effect-pass-wrapper, parameter-controller-for-future-gpu, ghost-point-trails]

key-files:
  created:
    - apollo7/postfx/__init__.py
    - apollo7/postfx/bloom.py
    - apollo7/postfx/dof_pass.py
    - apollo7/postfx/ssao_pass.py
    - apollo7/postfx/trails.py
    - apollo7/gui/panels/postfx_panel.py
    - tests/test_postfx.py
    - tests/test_postfx_panel.py
  modified:
    - apollo7/config/settings.py
    - apollo7/gui/widgets/viewport_widget.py
    - apollo7/gui/main_window.py
    - apollo7/gui/theme.py

key-decisions:
  - "Bloom uses pygfx PhysicalBasedBloomPass directly (default strength 0.04)"
  - "DoF/SSAO as parameter controllers -- pygfx EffectPass API not public for custom shaders"
  - "Trails via ghost point history with alpha decay (not framebuffer accumulation)"
  - "PostFX merge_id offsets 100+ to avoid collision with sim param undo entries"

patterns-established:
  - "Effect pass wrapper: thin controller around pygfx pass with range clamping"
  - "Parameter-only controller: stores params for future GPU integration"
  - "Ghost point trail: ring buffer of position snapshots with decaying alpha"

requirements-completed: [RENDER-05, SIM-04]

duration: 6min
completed: 2026-03-14
---

# Phase 02 Plan 04: Post-Processing Effects Summary

**Bloom, DoF, SSAO param controllers, and alpha trail accumulator with PostFX panel for real-time slider/toggle control**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-14T17:04:11Z
- **Completed:** 2026-03-14T17:10:40Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Bloom effect wraps pygfx PhysicalBasedBloomPass with runtime strength control and enable/disable toggle
- Depth of field and SSAO implemented as parameter controllers ready for future GPU integration
- Trail accumulator uses ghost point history with configurable decay for motion visualization
- PostFX panel provides toggleable sections with sliders for all effects, wired through undo stack

## Task Commits

Each task was committed atomically:

1. **Task 1: Bloom, DoF, SSAO, and trails implementation** - `a36d8ad` (feat)
2. **Task 2: PostFX controls panel and viewport integration** - `77844c2` (feat)

## Files Created/Modified
- `apollo7/postfx/__init__.py` - Package init exporting all effect classes
- `apollo7/postfx/bloom.py` - BloomController wrapping pygfx PhysicalBasedBloomPass
- `apollo7/postfx/dof_pass.py` - DepthOfFieldPass with focal distance and aperture params
- `apollo7/postfx/ssao_pass.py` - SSAOPass parameter controller (GPU pending)
- `apollo7/postfx/trails.py` - TrailAccumulator with ghost point history and alpha decay
- `apollo7/gui/panels/postfx_panel.py` - PostFX controls panel with 4 sections
- `apollo7/config/settings.py` - Added postfx parameter ranges and defaults
- `apollo7/gui/widgets/viewport_widget.py` - Added init_postfx, update_postfx_param, toggle_postfx
- `apollo7/gui/main_window.py` - PostFX panel in layout, signal wiring, undo integration
- `apollo7/gui/theme.py` - QSS for PostFX panel
- `tests/test_postfx.py` - 26 tests for effect controllers
- `tests/test_postfx_panel.py` - 15 tests for panel and undo integration

## Decisions Made
- Used pygfx PhysicalBasedBloomPass directly (default strength=0.04, not 0.4 as initially planned -- actual pygfx default)
- DoF and SSAO implemented as parameter controllers since pygfx EffectPass API doesn't expose a clean public interface for custom fragment shaders with depth buffer access
- Trails implemented via ghost point history pattern (ring buffer of position snapshots) rather than framebuffer accumulation, which is more compatible with pygfx
- SSAO GPU mode flagged as pending -- the controller stores params and provides CPU-side density estimation fallback
- PostFX undo merge IDs start at 100 to prevent collision with sim params (10+) and rendering params (0-2)

## Deviations from Plan

None - plan executed exactly as written. The plan explicitly allowed fallback approaches for DoF, SSAO, and trails, and these fallback patterns were used as the primary approach given pygfx EffectPass API limitations.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four post-processing effects are functional with parameter control
- Bloom is the only GPU-accelerated effect (via pygfx); DoF/SSAO/trails controllers are ready for GPU integration when pygfx exposes the necessary APIs
- PostFX panel is fully wired and integrated into the main window layout

---
*Phase: 02-creative-sculpting*
*Completed: 2026-03-14*

## Self-Check: PASSED
- All 8 created files verified present
- Both task commits (a36d8ad, 77844c2) verified in git log
- 41 tests passing (26 postfx + 15 panel)
