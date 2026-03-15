---
phase: 04-stable-physics
plan: 01
subsystem: simulation
tags: [pbf, wgsl, gpu-buffers, uniform-packing, position-based-fluids]

requires:
  - phase: 03-ship-it
    provides: "Working SPH simulation with parameters.py and buffers.py"
provides:
  - "PBF simulation parameters with 8x vec4 (128-byte) uniform layout"
  - "Extended ParticleBuffer with home_positions, predicted, lambda, delta_p GPU buffers"
  - "Breathing modulation computation (compute_breathing method)"
  - "Test scaffolds for all PHYS requirements (PHYS-01 through PHYS-09)"
affects: [04-02, 04-03, 04-04, 04-05]

tech-stack:
  added: []
  patterns:
    - "128-byte vec4-aligned PBF uniform layout"
    - "Home positions buffer with w=feature_strength"
    - "compute_breathing() for per-frame breathing modulation"

key-files:
  created:
    - tests/test_pbf_solver.py
  modified:
    - apollo7/simulation/parameters.py
    - apollo7/simulation/buffers.py
    - tests/test_simulation_params.py

key-decisions:
  - "rest_density=6378.0 from research (PBF reference, not SPH 1000.0)"
  - "cell_size mirrors kernel_radius in uniform (avoids separate param)"
  - "All PBF params classified as visual (hot-reload, no restart needed)"

patterns-established:
  - "PBF uniform layout: 8 x vec4 with breathing_mod computed per-frame"
  - "Home positions uploaded alongside particle state with default w=1.0 feature strength"

requirements-completed: [PHYS-01, PHYS-04, PHYS-08, PHYS-09]

duration: 3min
completed: 2026-03-15
---

# Phase 4 Plan 1: PBF Parameters and Buffers Summary

**PBF parameter dataclass with 128-byte uniform layout, 4 new GPU buffers, and 9 test scaffolds replacing SPH solver foundation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T11:18:59Z
- **Completed:** 2026-03-15T11:22:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced all SPH parameters with PBF parameters (14 new fields, 11 removed)
- Extended uniform layout from 112 bytes (7x vec4) to 128 bytes (8x vec4) with WGSL alignment
- Added 4 PBF-specific GPU buffers to ParticleBuffer (home_positions, predicted, lambda, delta_p)
- Created 9 test scaffolds covering all PHYS requirements for future solver implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace SPH params with PBF params (TDD RED)** - `39ffb22` (test)
2. **Task 1: Replace SPH params with PBF params (TDD GREEN)** - `d149549` (feat)
3. **Task 2: Extend ParticleBuffer with PBF buffers** - `10ec833` (feat)

_Note: Task 1 followed TDD flow with separate test and implementation commits._

## Files Created/Modified
- `apollo7/simulation/parameters.py` - PBF params with 128-byte uniform layout and breathing computation
- `apollo7/simulation/buffers.py` - Extended with home_positions, predicted, lambda, delta_p GPU buffers
- `tests/test_simulation_params.py` - 45 tests covering PBF defaults, uniform offsets, breathing, classification
- `tests/test_pbf_solver.py` - 9 skipped test stubs for PHYS-01 through PHYS-09

## Decisions Made
- rest_density set to 6378.0 per PBF research (vs old SPH 1000.0)
- cell_size in uniform mirrors kernel_radius (no separate parameter needed)
- All PBF params classified as visual for hot-reload without simulation restart
- Home positions uploaded with w=1.0 default feature strength (feature modulation deferred to engine)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Parameters and buffer contracts established for all subsequent PBF plans
- Uniform layout matches planned WGSL struct (8x vec4 = 128 bytes)
- Test scaffolds ready to be fleshed out as solver is built
- Other files referencing old SPH params (engine.py, GUI panels, shaders, presets) will need updating in subsequent plans

## Self-Check: PASSED

All 5 files verified present. All 3 commits verified in git log.

---
*Phase: 04-stable-physics*
*Completed: 2026-03-15*
