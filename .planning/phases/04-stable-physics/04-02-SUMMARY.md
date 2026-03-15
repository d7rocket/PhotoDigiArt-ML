---
phase: 04-stable-physics
plan: 02
subsystem: simulation
tags: [pbf, wgsl, gpu-compute, spatial-hash, position-based-fluids, prefix-sum, constraint-solver]

requires:
  - phase: 04-stable-physics
    provides: "PBF simulation parameters with 8x vec4 uniform layout and extended ParticleBuffer"
provides:
  - "7 WGSL compute shaders implementing full PBF algorithm pipeline"
  - "PBFSolver Python class orchestrating predict/hash/density/correct/finalize passes"
  - "GPU spatial hash via counting sort (atomicAdd + prefix sum + scatter)"
  - "Multi-level Blelloch prefix sum for 2M-cell grid"
  - "Chunked compute dispatch (256K) for AMD TDR prevention"
affects: [04-03, 04-04, 04-05]

tech-stack:
  added: []
  patterns:
    - "PBF compute pipeline: predict -> hash(count/scan/scatter) -> density/correct loop -> finalize"
    - "Multi-level prefix sum with block sums extraction and fixup dispatch"
    - "Bind group caching per buffer orientation for zero-rebuild frames"
    - "Inline fixup shader for prefix sum block sums addition"

key-files:
  created:
    - apollo7/simulation/pbf_solver.py
    - apollo7/simulation/shaders/pbf_predict.wgsl
    - apollo7/simulation/shaders/pbf_hash_count.wgsl
    - apollo7/simulation/shaders/pbf_hash_scan.wgsl
    - apollo7/simulation/shaders/pbf_hash_scatter.wgsl
    - apollo7/simulation/shaders/pbf_density.wgsl
    - apollo7/simulation/shaders/pbf_correct.wgsl
    - apollo7/simulation/shaders/pbf_finalize.wgsl
  modified: []

key-decisions:
  - "Block sums computed on CPU from cell_counts for prefix sum correctness (avoids race with in-place Blelloch scan)"
  - "Inline WGSL for add_block_sums fixup shader (too small for separate file)"
  - "Damping applied in finalize pass (velocity *= damping) rather than predict pass"

patterns-established:
  - "PBF solver as separate module (pbf_solver.py) -- engine.py delegates to it"
  - "Each WGSL shader declares its own SimParams struct (no shared include)"
  - "Particle struct: 2x vec4 = [pos.xyz, life, vel.xyz, mass] = 32 bytes"

requirements-completed: [PHYS-02, PHYS-03, PHYS-04]

duration: 4min
completed: 2026-03-15
---

# Phase 4 Plan 2: PBF Solver Core Summary

**7 WGSL compute shaders and PBFSolver orchestration class implementing full Position Based Fluids pipeline with GPU spatial hash and iterative constraint solving**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T11:24:46Z
- **Completed:** 2026-03-15T11:28:57Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created 7 WGSL compute shaders implementing the complete PBF algorithm (Macklin & Muller 2013)
- Built PBFSolver Python class that orchestrates the full pipeline per frame with proper GPU synchronization
- Implemented GPU spatial hash rebuild via counting sort (atomicAdd + Blelloch prefix sum + scatter)
- Added multi-level prefix sum handling for 2M-cell grid (4096 L1 workgroups + 8 L2 workgroups + fixup)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PBF WGSL shaders** - `b099a67` (feat)
2. **Task 2: Create PBFSolver Python class** - `6198202` (feat)

## Files Created/Modified
- `apollo7/simulation/pbf_solver.py` - PBF solver orchestration with pipeline building, bind group caching, chunked dispatch
- `apollo7/simulation/shaders/pbf_predict.wgsl` - Predict pass: home attraction + gravity + force/velocity clamping
- `apollo7/simulation/shaders/pbf_hash_count.wgsl` - Hash count: atomicAdd particle counts per cell
- `apollo7/simulation/shaders/pbf_hash_scan.wgsl` - Prefix sum: Blelloch tree-reduction parallel scan
- `apollo7/simulation/shaders/pbf_hash_scatter.wgsl` - Hash scatter: place particles in sorted order
- `apollo7/simulation/shaders/pbf_density.wgsl` - Density constraint: poly6/spiky kernels, lambda computation
- `apollo7/simulation/shaders/pbf_correct.wgsl` - Position correction: delta_p with artificial pressure
- `apollo7/simulation/shaders/pbf_finalize.wgsl` - Finalize: velocity from displacement + damping + clamping

## Decisions Made
- Block sums for prefix sum computed on CPU from cell_counts buffer (avoids race condition with in-place Blelloch scan that zeroes last element)
- Inline WGSL source for the add_block_sums fixup shader (too small for a separate .wgsl file)
- Damping applied in finalize pass (v *= damping) to act on the derived velocity, not the predicted velocity
- Each shader declares its own SimParams struct (no WGSL include mechanism, consistent with existing pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PBF solver ready to be wired into SimulationEngine (Plan 03)
- All 7 shaders load and validate without error
- Bind group layouts match buffer properties from ParticleBuffer (Plan 01)
- Curl noise (Plan 04) and vorticity/XSPH (Plan 04) are noted as future additions in predict and finalize shaders

---
*Phase: 04-stable-physics*
*Completed: 2026-03-15*
