---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: executing
stopped_at: Completed 04-03-PLAN.md
last_updated: "2026-03-15T11:37:04Z"
last_activity: 2026-03-15 -- Engine PBF integration with CFL timestep and stability tests (04-03)
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 25
  completed_plans: 23
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 4 - Stable Physics (v2.0 Make It Alive)

## Current Position

Phase: 4 of 6 (Stable Physics)
Plan: 3 of 5 in current phase
Status: Executing
Last activity: 2026-03-15 -- Engine PBF integration with CFL timestep and stability tests (04-03)

Progress: [█████████░] 92% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 3 (v2.0)
- Average duration: 4.3min
- Total execution time: 13min

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 04    | 01   | 3min     | 2     | 4     |
| 04    | 02   | 4min     | 2     | 8     |
| 04    | 03   | 6min     | 2     | 6     |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Research]: Keep entire v1.0 stack -- problems are physics bugs, not technology choices
- [v2.0 Research]: Replace SPH with PBF solver -- unconditionally stable for real-time GPU particle art
- [v2.0 Research]: No second GPU compute framework -- expand existing WGSL compute shaders, zero-copy buffer sharing
- [v2.0 Research]: "Alive formula" = home attraction + curl noise + vortex confinement + velocity-dependent damping
- [v2.0 Roadmap]: 3 phases (coarse) -- Physics first, then Rendering+Depth, then UI+Claude
- [04-01]: rest_density=6378.0 from PBF research (not SPH 1000.0)
- [04-01]: cell_size mirrors kernel_radius in uniform (no separate param)
- [04-01]: All PBF params classified as visual (hot-reload, no restart)
- [04-02]: Block sums for prefix sum computed on CPU from cell_counts (avoids Blelloch race)
- [04-02]: Damping applied in finalize pass (velocity *= damping) not predict pass
- [04-03]: CFL uses conservative estimate from params rather than GPU readback (avoids sync stall)
- [04-03]: Feature strength range [0.5, 1.5] -- edges hold tighter, flat areas drift more
- [04-03]: PBF solver rebuilt on restart() for clean state

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- exact API needs prototyping (MEDIUM confidence)
- PBF tuning for artistic vs. physically accurate results -- needs experimentation
- GUI references to set_performance_mode need updating (deferred from 04-03)

## Session Continuity

Last session: 2026-03-15T11:37:04Z
Stopped at: Completed 04-03-PLAN.md
Resume file: .planning/phases/04-stable-physics/04-03-SUMMARY.md
