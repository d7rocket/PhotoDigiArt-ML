---
phase: 02-creative-sculpting
plan: 01
subsystem: simulation
tags: [wgpu, wgsl, compute-shaders, particle-sim, sph, perlin-noise, flow-field, gpu]

requires:
  - phase: 01-pipeline-foundation
    provides: "wgpu device access via pygfx renderer, point cloud data (positions/colors)"
provides:
  - "SimulationEngine class orchestrating GPU compute pipelines"
  - "SimulationParams dataclass with vec4-aligned WGSL uniform packing"
  - "ParticleBuffer with double-buffered GPU storage"
  - "WGSL shaders: noise, flow_field, forces, sph, integrate"
  - "Shader loader with concatenation utility"
affects: [02-creative-sculpting, simulation-panel, postfx, export]

tech-stack:
  added: []
  patterns:
    - "Double-buffered GPU particle state (ping-pong swap)"
    - "Vec4-aligned WGSL uniform structs (16-byte boundaries)"
    - "Chunked compute dispatch (256K particles/chunk for AMD TDR prevention)"
    - "Visual param hot-reload vs physics param restart pattern"
    - "Spatial hash grid for O(N*k) neighbor search"

key-files:
  created:
    - "apollo7/simulation/__init__.py"
    - "apollo7/simulation/engine.py"
    - "apollo7/simulation/parameters.py"
    - "apollo7/simulation/buffers.py"
    - "apollo7/simulation/shaders/__init__.py"
    - "apollo7/simulation/shaders/noise.wgsl"
    - "apollo7/simulation/shaders/flow_field.wgsl"
    - "apollo7/simulation/shaders/forces.wgsl"
    - "apollo7/simulation/shaders/sph.wgsl"
    - "apollo7/simulation/shaders/integrate.wgsl"
    - "tests/test_simulation_params.py"
    - "tests/test_flow_field.py"
    - "tests/test_sph.py"
    - "tests/test_simulation_engine.py"
  modified: []

key-decisions:
  - "112-byte uniform struct with 7x vec4 layout for WGSL alignment"
  - "Spatial hash grid size 128^3 with 64-unit offset centering at origin"
  - "Boundary clamping at +/-50 units with soft bounce damping"
  - "Separate force accumulation buffer zeroed each frame before passes"

patterns-established:
  - "Double-buffered particle state: read from A, write to B, swap"
  - "Chunked dispatch: 256K particles per dispatch call"
  - "Shader loader: load_shader(name) + build_combined_shader(*names)"
  - "SimulationParams.with_update() immutable update pattern"

requirements-completed: [RENDER-04, SIM-01, SIM-02, SIM-03]

duration: 8min
completed: 2026-03-14
---

# Phase 2 Plan 1: Simulation Engine Summary

**GPU particle simulation engine with WGSL compute shaders: Perlin flow fields, SPH fluid dynamics, attraction/repulsion forces, and double-buffered particle state for 1-5M particles**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T16:54:03Z
- **Completed:** 2026-03-14T17:01:42Z
- **Tasks:** 3
- **Files created:** 14

## Accomplishments
- Complete simulation module with 5 WGSL compute shaders (noise, flow field, forces, SPH, integration)
- SimulationEngine orchestrator with IDLE/RUNNING/PAUSED lifecycle, chunked dispatch for AMD TDR prevention
- SPH fluid dynamics with poly6/spiky/viscosity kernels and spatial hash neighbor search
- Feature-driven flow fields sampling edge_map and depth_map textures for organic motion
- 85 tests all passing covering params, buffers, shader loading, kernel math, spatial hashing, engine lifecycle, and GPU integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Simulation parameters, particle buffers, noise and integration shaders** - `d207c13` (feat)
2. **Task 2: Flow field, forces, SPH shaders, and shader loader** - `3ad21fe` (feat)
3. **Task 3: SimulationEngine orchestrator with compute pipeline** - `9a14fdf` (feat)

## Files Created/Modified
- `apollo7/simulation/__init__.py` - Package init exporting SimulationParams, ParticleBuffer, SimulationEngine
- `apollo7/simulation/parameters.py` - SimulationParams dataclass with vec4-aligned uniform packing (112 bytes)
- `apollo7/simulation/buffers.py` - ParticleBuffer with double-buffered GPU storage (32 bytes/particle)
- `apollo7/simulation/engine.py` - SimulationEngine orchestrating compute pipelines with chunked dispatch
- `apollo7/simulation/shaders/__init__.py` - Shader loader with load_shader() and build_combined_shader()
- `apollo7/simulation/shaders/noise.wgsl` - Perlin 3D, simplex 3D, and fBm noise functions
- `apollo7/simulation/shaders/flow_field.wgsl` - Feature-driven flow field with texture sampling
- `apollo7/simulation/shaders/forces.wgsl` - Attraction/repulsion, gravity, wind with spatial hash
- `apollo7/simulation/shaders/sph.wgsl` - 3-pass SPH: density (poly6), forces (spiky+viscosity)
- `apollo7/simulation/shaders/integrate.wgsl` - Symplectic Euler integration with soft boundary bounce
- `tests/test_simulation_params.py` - 21 tests for params, uniform bytes, classification
- `tests/test_flow_field.py` - 24 tests for shader loader, feature textures, kernel math, spatial hash
- `tests/test_sph.py` - 17 tests for SPH shader, kernel validation, pressure equation
- `tests/test_simulation_engine.py` - 23 tests for state machine, param reload, GPU integration

## Decisions Made
- 112-byte uniform struct (7x vec4) for strict WGSL alignment compatibility
- Spatial hash grid 128^3 with 64-unit offset to center at origin -- supports simulation domain of 128 units per axis
- Boundary at +/-50 units with soft bounce (0.5 damping) prevents particles escaping to infinity
- Force accumulation buffer zeroed each frame before shader passes write to it
- SimulationParams.with_update() returns new instance for immutable parameter updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Simulation engine ready for integration with viewport widget (next plan: simulation controls panel)
- GPU buffer access methods (get_positions_buffer, get_colors_buffer) ready for pygfx rendering connection
- Feature texture upload API ready for edge_map and depth_map from Phase 1 extractors
- All 85 tests passing, import paths verified

## Self-Check: PASSED

- All 14 created files verified present on disk
- All 3 task commits verified in git log (d207c13, 3ad21fe, 9a14fdf)

---
*Phase: 02-creative-sculpting*
*Completed: 2026-03-14*
