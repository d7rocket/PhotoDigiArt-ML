---
phase: 04-stable-physics
plan: 04
subsystem: simulation
tags: [pbf, curl-noise, vorticity-confinement, xsph, breathing, organic-motion]

requires:
  - phase: 04-stable-physics
    provides: "SimulationEngine wired to PBFSolver (full PBF pipeline per frame)"
  - phase: 04-stable-physics
    provides: "7 WGSL compute shaders implementing full PBF algorithm pipeline"
provides:
  - "Curl noise divergence-free flow field in predict pass"
  - "Vorticity confinement for rotational energy injection in finalize"
  - "XSPH viscosity for coherent velocity field smoothing"
  - "Breathing modulation of home_strength and noise_amplitude"
  - "Feature-texture-driven motion intensity (edges active, flat calm)"
affects: [04-05]

tech-stack:
  added: []
  patterns:
    - "build_combined_shader('noise', 'pbf_predict') for shared noise functions"
    - "Finalize uses 7 bindings (original 4 + spatial hash for neighbor search)"
    - "Curl noise via finite-difference curl of 3-channel FBM with decorrelation offsets"
    - "Breathing complement: home tighter on inhale, noise stronger on exhale"

key-files:
  created: []
  modified:
    - apollo7/simulation/shaders/noise.wgsl
    - apollo7/simulation/shaders/pbf_predict.wgsl
    - apollo7/simulation/shaders/pbf_finalize.wgsl
    - apollo7/simulation/pbf_solver.py
    - tests/test_pbf_solver.py

key-decisions:
  - "Curl noise uses 3 decorrelated FBM channels with large constant offsets for proper curl"
  - "Vorticity confinement uses simplified eta approximation (omega direction) to avoid second neighbor pass"
  - "XSPH and vorticity share the same neighbor loop in finalize for efficiency"

patterns-established:
  - "Combined shader modules via build_combined_shader for cross-file function sharing"
  - "Breathing modulation applied as complement pair: home * mod, noise * (2-mod)"

requirements-completed: [PHYS-01, PHYS-06, PHYS-07, PHYS-08]

duration: 5min
completed: 2026-03-15
---

# Phase 4 Plan 4: Organic Motion Forces Summary

**Curl noise flow field, vorticity confinement, XSPH viscosity, and breathing modulation -- particles now flow with ocean-current motion while maintaining sculptural form**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T11:39:54Z
- **Completed:** 2026-03-15T11:44:58Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added curl_noise_3d function to noise.wgsl using finite-difference curl of 3-channel FBM noise
- Integrated curl noise into pbf_predict.wgsl with breathing modulation and feature-texture-driven intensity
- Rewrote pbf_finalize.wgsl with neighbor-search-based vorticity confinement and XSPH viscosity
- Expanded finalize bindings from 4 to 7 (added spatial hash buffers for neighbor search)
- Used build_combined_shader("noise", "pbf_predict") for shared noise functions across shaders
- Un-skipped and implemented PHYS-01, PHYS-06, PHYS-07, PHYS-08 tests -- all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add curl noise to noise.wgsl and integrate into pbf_predict.wgsl** - `14e0865` (feat)
2. **Task 2: Add vorticity confinement and XSPH to pbf_finalize.wgsl, un-skip motion tests** - `8e5742d` (feat)

## Files Created/Modified
- `apollo7/simulation/shaders/noise.wgsl` - Added curl_noise_3d function (finite-difference curl of decorrelated FBM channels)
- `apollo7/simulation/shaders/pbf_predict.wgsl` - Integrated curl noise + breathing modulation + feature-texture motion intensity
- `apollo7/simulation/shaders/pbf_finalize.wgsl` - Complete rewrite: vorticity confinement, XSPH viscosity, 7-binding layout
- `apollo7/simulation/pbf_solver.py` - build_combined_shader for predict, expanded finalize bind group to 7 bindings
- `tests/test_pbf_solver.py` - Un-skipped PHYS-01/06/07/08, implemented with proper assertions

## Decisions Made
- Curl noise uses 3 decorrelated FBM noise channels (offset by large constants) for proper divergence-free curl computation
- Vorticity confinement uses simplified eta approximation (omega direction) to avoid expensive second neighbor pass
- XSPH and vorticity share the same neighbor iteration loop in finalize for GPU efficiency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All organic motion forces active: curl noise, vorticity, XSPH, breathing
- Ready for Plan 05 (solver tuning and parameter optimization)
- PHYS-09 (iteration count effects) remains as the only skipped test

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 04-stable-physics*
*Completed: 2026-03-15*
