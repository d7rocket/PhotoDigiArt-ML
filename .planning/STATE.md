---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: executing
stopped_at: Completed 04-01-PLAN.md
last_updated: "2026-03-15T11:22:57.717Z"
last_activity: 2026-03-15 -- PBF parameters and buffers (04-01)
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 25
  completed_plans: 21
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 4 - Stable Physics (v2.0 Make It Alive)

## Current Position

Phase: 4 of 6 (Stable Physics)
Plan: 1 of 5 in current phase
Status: Executing
Last activity: 2026-03-15 -- PBF parameters and buffers (04-01)

Progress: [████████░░] 84% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 1 (v2.0)
- Average duration: 3min
- Total execution time: 3min

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

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- exact API needs prototyping (MEDIUM confidence)
- PBF tuning for artistic vs. physically accurate results -- needs experimentation

## Session Continuity

Last session: 2026-03-15T11:22:04Z
Stopped at: Completed 04-01-PLAN.md
Resume file: .planning/phases/04-stable-physics/04-01-SUMMARY.md
