---
phase: 02-creative-sculpting
plan: 07
subsystem: simulation
tags: [wgpu, compute-shader, sph, forces, spatial-hash, gpu-pipeline]

requires:
  - phase: 02-creative-sculpting (plan 01)
    provides: "SimulationParams uniform struct, integrate.wgsl shader, ParticleBuffer double-buffering"
provides:
  - "Forces compute pipeline (attraction/repulsion via spatial hash grid)"
  - "SPH density + force compute pipelines (pressure, viscosity)"
  - "Multi-pass GPU dispatch: forces -> SPH density -> SPH force -> integration"
  - "Spatial hash grid buffers (cell_counts, cell_offsets, sorted_indices)"
  - "Force accumulation buffers read by integration shader"
affects: [03-discovery, rendering, simulation]

tech-stack:
  added: []
  patterns:
    - "Multi-pass compute pipeline with separate command encoder submissions for GPU sync"
    - "CPU-side spatial hash build on init/restart, GPU reads per frame"
    - "Noise function extraction and prepending for shader dependency resolution"

key-files:
  created: []
  modified:
    - "apollo7/simulation/buffers.py"
    - "apollo7/simulation/engine.py"
    - "apollo7/simulation/shaders/integrate.wgsl"

key-decisions:
  - "CPU spatial hash build on init/restart only (not per-frame) -- acceptable for initial impl"
  - "Noise functions extracted from integrate.wgsl and prepended to forces.wgsl at pipeline build time"
  - "Each pipeline dispatch uses separate command encoder submission for GPU synchronization"
  - "SPH passes skipped entirely in performance_mode (not just zeroed)"

patterns-established:
  - "Multi-pass pipeline: forces -> SPH density -> SPH force -> integration"
  - "Bind group rebuild per frame for buffer swap correctness"

requirements-completed: [RENDER-04, SIM-02, SIM-03]

duration: 4min
completed: 2026-03-14
---

# Phase 2 Plan 7: Forces and SPH Pipeline Wiring Summary

**Attraction/repulsion and SPH fluid dynamics compute pipelines wired into multi-pass GPU dispatch with spatial hash neighbor lookup**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T18:44:29Z
- **Completed:** 2026-03-14T18:48:09Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ParticleBuffer extended with 6 auxiliary GPU buffers (forces, SPH forces, densities, spatial hash grid)
- CPU-side spatial hash builder computes cell assignments, prefix sums, and sorted indices
- Forces compute pipeline dispatches attraction/repulsion with 3x3x3 neighbor search via spatial hash
- SPH density and force pipelines compute pressure (spiky kernel) and viscosity forces
- Integration shader reads external_forces and sph_force_input buffers alongside inline flow forces
- Multi-pass dispatch with proper GPU synchronization (separate command encoder per pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add spatial hash and force buffers to ParticleBuffer** - `26e641d` (feat)
2. **Task 2: Build and dispatch forces + SPH compute pipelines** - `f2f6eb2` (feat)

## Files Created/Modified
- `apollo7/simulation/buffers.py` - Added 6 auxiliary GPU buffers, build_spatial_hash(), clear_forces(), buffer properties
- `apollo7/simulation/engine.py` - Added _build_forces_pipeline(), _build_sph_pipelines(), multi-pass _step_once() dispatch
- `apollo7/simulation/shaders/integrate.wgsl` - Added external_forces and sph_force_input bindings, total_force summation

## Decisions Made
- CPU spatial hash build runs only on init/restart, not per-frame (GPU-side hash deferred for optimization)
- Noise functions extracted from integrate.wgsl header and prepended to forces.wgsl source string at pipeline build time (avoids duplicating noise code in forces.wgsl)
- Each pipeline pass uses separate command encoder + submit for GPU synchronization between dependent passes
- SPH passes entirely skipped in performance_mode (bind group not even rebuilt)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure in test_simulation_params.py (viscosity classification) -- confirmed not caused by this plan's changes, out of scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All simulation compute pipelines now wired and dispatching on GPU
- Attraction/repulsion, SPH viscosity/pressure sliders have real effect on particle motion
- Ready for Phase 3 discovery features or further simulation refinement

---
*Phase: 02-creative-sculpting*
*Completed: 2026-03-14*
