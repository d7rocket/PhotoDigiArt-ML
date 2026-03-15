---
phase: 04-stable-physics
plan: 03
subsystem: simulation
tags: [pbf, engine, cfl-timestep, feature-textures, gpu-compute]

requires:
  - phase: 04-stable-physics
    provides: "PBF simulation parameters with 8x vec4 uniform layout and extended ParticleBuffer"
  - phase: 04-stable-physics
    provides: "7 WGSL compute shaders implementing full PBF algorithm pipeline"
provides:
  - "SimulationEngine wired to PBFSolver (full PBF pipeline per frame)"
  - "CFL-adaptive timestep preventing velocity runaway"
  - "Feature texture modulation of home position strength (edge_map -> w channel)"
  - "1000-frame stability verified with no NaN/Inf/explosion"
  - "Old SPH code fully removed (3 shaders, all SPH pipeline code)"
affects: [04-04, 04-05]

tech-stack:
  added: []
  patterns:
    - "Engine delegates to PBFSolver.step() -- no direct shader dispatch in engine"
    - "Feature modulation: edge_map samples mapped to home_positions.w [0.5, 1.5]"
    - "CFL adaptive dt = min(dt_target, CFL_COEFF * h / v_max)"

key-files:
  created: []
  modified:
    - apollo7/simulation/engine.py
    - apollo7/simulation/buffers.py
    - apollo7/simulation/shaders/pbf_density.wgsl
    - apollo7/simulation/shaders/pbf_correct.wgsl
    - tests/test_simulation_engine.py
    - tests/test_pbf_solver.py

key-decisions:
  - "CFL uses conservative estimate from params rather than GPU readback (avoids sync stall)"
  - "Feature strength range [0.5, 1.5] -- edges hold tighter, flat areas drift more"
  - "PBF solver rebuilt on restart() for clean state"

patterns-established:
  - "Engine is thin orchestrator -- all GPU work delegated to PBFSolver"
  - "Feature textures modulate home position w channel on CPU during init"
  - "WGSL NaN/Inf guard via arithmetic (x != x) not isnan/isinf (not in WGSL)"

requirements-completed: [PHYS-02, PHYS-05]

duration: 6min
completed: 2026-03-15
---

# Phase 4 Plan 3: Engine PBF Integration Summary

**SimulationEngine rewired to PBF solver with CFL-adaptive timestep, feature texture modulation, and 1000-frame stability verified across all tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T11:31:26Z
- **Completed:** 2026-03-15T11:37:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Rewired SimulationEngine to delegate all simulation to PBFSolver, removing 1150+ lines of SPH pipeline code
- Deleted 3 obsolete SPH shaders (integrate.wgsl, forces.wgsl, sph.wgsl)
- Implemented CFL-adaptive timestep preventing velocity-driven instability
- Added feature texture modulation mapping edge_map values to home position strength
- Un-skipped and passed PHYS-02/03/04/05 stability tests (1000 frames, aggressive params, spatial hash)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire engine.py to PBFSolver and delete old SPH code** - `95b0112` (feat)
2. **Task 2: Update engine and PBF tests, un-skip stability tests** - `3c08fee` (feat)

## Files Created/Modified
- `apollo7/simulation/engine.py` - Complete rewrite: PBF delegation, CFL timestep, feature modulation
- `apollo7/simulation/buffers.py` - Added COPY_SRC usage to grid buffers for prefix sum copy
- `apollo7/simulation/shaders/pbf_density.wgsl` - Fixed invalid isnan/isinf calls to WGSL-compatible checks
- `apollo7/simulation/shaders/pbf_correct.wgsl` - Fixed invalid isnan/isinf calls to WGSL-compatible checks
- `tests/test_simulation_engine.py` - Removed PerformanceMode tests, added feature texture test, updated params
- `tests/test_pbf_solver.py` - Un-skipped PHYS-02/03/04/05, added _make_pbf_engine helper

## Decisions Made
- CFL timestep uses conservative estimate from params.max_velocity rather than GPU readback to avoid sync stall
- Feature strength mapped to [0.5, 1.5] range: high edge = tighter hold, flat areas = more drift
- PBF solver is rebuilt on restart() for clean GPU state (stateless approach)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed WGSL isnan/isinf calls in density and correct shaders**
- **Found during:** Task 2 (test execution)
- **Issue:** pbf_density.wgsl and pbf_correct.wgsl used isnan()/isinf() which don't exist in WGSL
- **Fix:** Replaced with arithmetic NaN/Inf checks (x != x for NaN, x - x != 0.0 for Inf)
- **Files modified:** apollo7/simulation/shaders/pbf_density.wgsl, apollo7/simulation/shaders/pbf_correct.wgsl
- **Verification:** All shaders compile and tests pass
- **Committed in:** 3c08fee (Task 2 commit)

**2. [Rule 1 - Bug] Fixed buffer COPY_SRC usage flags for prefix sum**
- **Found during:** Task 2 (test execution)
- **Issue:** cell_counts_buffer and cell_offsets_buffer lacked COPY_SRC flag, causing validation error when prefix sum copies cell_counts to cell_offsets
- **Fix:** Added COPY_SRC to grid buffer usage flags in ParticleBuffer
- **Files modified:** apollo7/simulation/buffers.py
- **Verification:** Prefix sum copy works, all tests pass
- **Committed in:** 3c08fee (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs from Plan 02 shaders/buffers)
**Impact on plan:** Both fixes essential for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PBF simulation running end-to-end through engine lifecycle
- 1000-frame stability proven with default and aggressive parameters
- Ready for Plan 04 (curl noise + vorticity) and Plan 05 (tuning)
- GUI references to set_performance_mode will need updating (deferred -- out of scope for this plan)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 04-stable-physics*
*Completed: 2026-03-15*
