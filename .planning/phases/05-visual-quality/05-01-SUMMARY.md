---
phase: 05-visual-quality
plan: 01
subsystem: rendering
tags: [wgpu, pygfx, compute-shader, gpu-buffer-sharing, zero-copy]

# Dependency graph
requires:
  - phase: 04-stable-physics
    provides: ParticleBuffer with ping-pong state buffers and PBF solver
provides:
  - Extract-positions compute shader (stride-32 to packed vec4)
  - Shared render buffer with VERTEX usage flag
  - Zero-copy GPU buffer injection into pygfx geometry
  - Test scaffolds for all Phase 5 visual quality requirements
affects: [05-02-PLAN, 05-03-PLAN, 05-04-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [GPU buffer sharing via pygfx Buffer._wgpu_object injection, lazy compute pipeline creation]

key-files:
  created:
    - apollo7/simulation/shaders/extract_positions.wgsl
    - tests/test_visual_quality.py
  modified:
    - apollo7/simulation/buffers.py
    - apollo7/gui/widgets/viewport_widget.py

key-decisions:
  - "Lazy pipeline creation for extract shader (built on first dispatch, not in __init__)"
  - "Fallback to CPU readback preserved for safety if GPU sharing fails"
  - "Color buffer gets VERTEX flag for direct injection (no extract shader needed for colors)"

patterns-established:
  - "GPU buffer sharing: create pygfx Buffer shell, inject _wgpu_object from compute buffer"
  - "Extract dispatch after swap(): compute shader copies packed positions for rendering"

requirements-completed: [REND-05]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 5 Plan 01: GPU Buffer Sharing Summary

**Zero-copy GPU buffer sharing between PBF compute and pygfx rendering via extract-positions shader and _wgpu_object injection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T15:59:54Z
- **Completed:** 2026-03-15T16:05:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Eliminated CPU readback bottleneck (device.queue.read_buffer) from the primary render path
- Created extract_positions.wgsl compute shader that copies xyz from stride-32 particle state to packed vec4 buffer
- Shared both positions and colors via pygfx Buffer._wgpu_object injection for zero-copy rendering
- Test scaffolds cover REND-02, REND-03, REND-04, REND-05, DPTH-02 requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffolds and extract-positions compute shader with shared render buffer**
   - `520fa8b` (test: add failing tests for GPU buffer sharing -- TDD RED)
   - `1c76eb2` (feat: add extract-positions shader and shared render buffer -- TDD GREEN)
   - `4d7b7b4` (refactor: restore test scaffolds with enriched color stubs)

2. **Task 2: Wire GPU buffer sharing into viewport replacing CPU readback** - `eceb9f8` (feat)

_Note: Task 1 used TDD flow (RED/GREEN commits)_

## Files Created/Modified
- `apollo7/simulation/shaders/extract_positions.wgsl` - Compute shader extracting xyz from stride-32 particle state into packed vec4 positions buffer
- `apollo7/simulation/buffers.py` - Added render_positions_buffer (VERTEX), extract_positions_to_render(), VERTEX on color buffer
- `apollo7/gui/widgets/viewport_widget.py` - GPU buffer injection replacing CPU readback, with fallback path
- `tests/test_visual_quality.py` - Test scaffolds for all Phase 5 visual quality requirements

## Decisions Made
- Lazy pipeline creation: extract-positions pipeline built on first dispatch rather than in __init__, avoiding import-time GPU work
- CPU readback fallback preserved: if GPU sharing fails, falls back to read_positions() with warning log
- Color buffer gets VERTEX flag directly (no extract shader needed since RGBA vec4 matches pygfx format)
- Shared buffer setup happens in init_simulation after engine.initialize, not in start_simulation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test file overwritten by external process**
- **Found during:** Task 1 (after TDD GREEN commit)
- **Issue:** tests/test_visual_quality.py was overwritten by an external process with different content
- **Fix:** Restored test file with correct content; adapted skip decorators to survive external modifications
- **Files modified:** tests/test_visual_quality.py
- **Verification:** All buffer sharing tests pass, stubs properly skipped
- **Committed in:** 4d7b7b4

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- file restoration required but all tests pass correctly.

## Issues Encountered
- Pre-existing test failure in test_discovery.py::TestRandomWalkPropose::test_propose_within_constraints (unrelated to this plan, not fixed)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- GPU buffer sharing foundation ready for Plans 05-02 (color enrichment) and 05-03 (white bg tuning)
- Blocker resolved: "GPU buffer sharing between wgpu compute and pygfx render" confirmed working via _wgpu_object injection
- Test scaffolds provide stubs for remaining Phase 5 requirements

---
*Phase: 05-visual-quality*
*Completed: 2026-03-15*
