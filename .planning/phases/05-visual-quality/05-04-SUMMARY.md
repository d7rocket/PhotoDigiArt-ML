---
phase: 05-visual-quality
plan: 04
subsystem: rendering
tags: [crossfade, ease-out, animation, qtimer, interpolation, bloom, gpu-buffers]

# Dependency graph
requires:
  - phase: 05-visual-quality
    provides: GPU buffer sharing (Plan 05-01), white background + luminous blending (Plan 05-03)
provides:
  - Unified CrossfadeEngine with QTimer-driven ease-out interpolation
  - Smooth slider parameter transitions (~0.4s cubic ease-out)
  - A/B preset crossfade via CrossfadeEngine chase animation
  - Discrete param passthrough (solver_iterations snaps instantly)
  - Visual verification fixes for white background rendering
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [QTimer-driven ease-out crossfade for parameter smoothing, cubic ease-out 1-(1-t)^3]

key-files:
  created:
    - apollo7/rendering/crossfade.py
    - tests/test_crossfade_engine.py
  modified:
    - apollo7/gui/widgets/viewport_widget.py
    - apollo7/gui/main_window.py
    - apollo7/rendering/bloom_controller.py

key-decisions:
  - "Cubic ease-out curve 1-(1-t)^3 for iOS-like deceleration feel"
  - "400ms transition duration (middle of 300-500ms user spec)"
  - "CrossfadeEngine applies to all continuous params; discrete params bypass"
  - "A/B preset crossfade_changed signal routes through same engine for unified behavior"
  - "GPU buffer sharing disabled due to pygfx vec3/vec4 mismatch -- CPU readback fallback active"
  - "Bloom disabled on white background (washes out particles)"
  - "Saturation boost raised to 1.8 and alpha to 0.92 for vibrancy on white"

patterns-established:
  - "Crossfade routing: all param changes go through CrossfadeEngine.set_target, engine calls back apply_fn with interpolated values"
  - "Retarget from current interpolated position, not from start, for smooth redirection"

requirements-completed: [REND-06]

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 5 Plan 04: Crossfade Engine Summary

**Unified CrossfadeEngine with cubic ease-out interpolation, plus visual verification fixes for white-background particle rendering**

## Performance

- **Duration:** 8 min (including checkpoint verification and iterative fixes)
- **Started:** 2026-03-15T16:16:36Z
- **Completed:** 2026-03-15
- **Tasks:** 3 of 3
- **Files modified:** 5

## Accomplishments
- Created CrossfadeEngine with cubic ease-out (1-(1-t)^3) for iOS-like smooth parameter transitions
- All slider changes now route through crossfade for ~0.4s chase animation instead of instant pop
- A/B preset crossfade_changed signal connected to viewport.apply_crossfaded_preset in main_window.py
- Discrete params (solver_iterations) correctly bypass engine and snap instantly
- Full TDD coverage: 5 tests covering ease-out curve, idle stop, concurrent transitions, retarget, discrete passthrough
- Visual verification identified and fixed 4 rendering issues on white background

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CrossfadeEngine and tests (TDD)**
   - `848145b` (test: add failing tests for CrossfadeEngine -- TDD RED)
   - `2a43014` (feat: implement CrossfadeEngine with ease-out interpolation -- TDD GREEN)

2. **Task 2: Wire crossfade engine into viewport, simulation panel, and preset crossfade** - `838899e` (feat)

3. **Task 3: Visual verification checkpoint** - Approved after iterative fixes:
   - `3618651` (fix: increase particle visibility on white background)
   - `2ff2934` (fix: disable GPU buffer sharing due to pygfx vec3/vec4 mismatch)
   - `970b8fd` (fix: boost color vibrancy on white background)
   - `77e7624` (fix: disable bloom on white background)

_Note: Task 1 used TDD flow (RED/GREEN commits)_

## Files Created/Modified
- `apollo7/rendering/crossfade.py` - CrossfadeEngine with QTimer, cubic ease-out, concurrent transitions, retarget support
- `tests/test_crossfade_engine.py` - 5 tests covering all crossfade behavior
- `apollo7/gui/widgets/viewport_widget.py` - CrossfadeEngine instance, _apply_crossfaded_param routing, apply_crossfaded_preset for A/B transitions
- `apollo7/gui/main_window.py` - Connected preset_panel.crossfade_changed to viewport.apply_crossfaded_preset
- `apollo7/rendering/bloom_controller.py` - Bloom disabled on white background

## Decisions Made
- Cubic ease-out 1-(1-t)^3 chosen for fast initial response with smooth deceleration (iOS feel)
- 400ms duration chosen as middle of user-specified 300-500ms range
- All continuous params crossfade; only solver_iterations is discrete (snaps instantly)
- A/B preset transitions use same CrossfadeEngine (crossfade_changed signal -> apply_crossfaded_preset -> set_target per key)
- Timer test adapted to check _active dict emptiness instead of QTimer.isActive() (requires event loop)
- GPU buffer sharing disabled: pygfx expects vec4 but compute outputs vec3; CPU readback fallback is active and performant enough
- Bloom post-processing disabled on white background: bloom washes out particles and reduces contrast
- Saturation boost raised from 1.5 to 1.8, blend alpha from 0.85 to 0.92 for vibrant colors on white

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Particles invisible on white background**
- **Found during:** Task 3 (visual verification)
- **Issue:** Particles were not visible against white background -- blend alpha too low
- **Fix:** Raised blend alpha for visibility on white
- **Files modified:** apollo7/gui/widgets/viewport_widget.py
- **Committed in:** `3618651`

**2. [Rule 1 - Bug] GPU buffer sharing vec3/vec4 mismatch**
- **Found during:** Task 3 (visual verification)
- **Issue:** pygfx expects vec4 position buffers but compute shader outputs vec3, causing blank viewport
- **Fix:** Disabled GPU buffer sharing, reverted to CPU readback fallback path
- **Files modified:** apollo7/gui/widgets/viewport_widget.py
- **Committed in:** `2ff2934`

**3. [Rule 1 - Bug] Colors too pale on white background**
- **Found during:** Task 3 (visual verification)
- **Issue:** Saturation and alpha values tuned for dark background were washed out on white
- **Fix:** Saturation boost 1.5 -> 1.8, alpha 0.85 -> 0.92
- **Files modified:** apollo7/gui/widgets/viewport_widget.py
- **Committed in:** `970b8fd`

**4. [Rule 1 - Bug] Bloom washes out particles on white**
- **Found during:** Task 3 (visual verification)
- **Issue:** Bloom post-processing designed for dark background creates white haze on white background
- **Fix:** Disabled bloom on white background
- **Files modified:** apollo7/rendering/bloom_controller.py
- **Committed in:** `77e7624`

---

**Total deviations:** 4 auto-fixed (4 bugs found during visual verification)
**Impact on plan:** All fixes necessary for correct rendering on white background. No scope creep.

## Issues Encountered
- QTimer.isActive() returns False without running Qt event loop; adapted test to check _active dict instead (no behavior change)
- Pre-existing test_visual_quality.py failures due to wgpu device configuration conflict (unrelated to this plan)
- GPU buffer sharing (Plan 05-01) incompatible with pygfx vec4 expectations -- reverted to CPU readback. This is a known limitation that may be revisited in a future phase.

## Deferred Ideas
- **PSO (Particle Swarm Optimization) algorithm for particle behavior** -- user suggested during visual verification. Noted for potential future phase exploration.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 Visual Quality is now complete (all 4 plans executed and verified)
- All visual quality features active: white gallery background, luminous blending, smooth crossfade, CLAHE depth, enriched colors
- GPU buffer sharing disabled (CPU readback active) -- may be revisited when pygfx supports vec3 position buffers
- Ready for Phase 6: Interface and Intelligence

## Self-Check: PASSED

- All 4 key files verified present on disk
- All 7 commits verified in git history (848145b, 2a43014, 838899e, 3618651, 2ff2934, 970b8fd, 77e7624)

---
*Phase: 05-visual-quality*
*Completed: 2026-03-15*
