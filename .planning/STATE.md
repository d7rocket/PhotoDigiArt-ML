---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: planning
stopped_at: Phase 4 context gathered
last_updated: "2026-03-15T10:27:22.565Z"
last_activity: 2026-03-15 -- v2.0 roadmap created
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 20
  completed_plans: 20
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 4 - Stable Physics (v2.0 Make It Alive)

## Current Position

Phase: 4 of 6 (Stable Physics)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-15 -- v2.0 roadmap created

Progress: [░░░░░░░░░░░░░░░░░░░░] 0% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v2.0)
- Average duration: --
- Total execution time: --

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Research]: Keep entire v1.0 stack -- problems are physics bugs, not technology choices
- [v2.0 Research]: Replace SPH with PBF solver -- unconditionally stable for real-time GPU particle art
- [v2.0 Research]: No second GPU compute framework -- expand existing WGSL compute shaders, zero-copy buffer sharing
- [v2.0 Research]: "Alive formula" = home attraction + curl noise + vortex confinement + velocity-dependent damping
- [v2.0 Roadmap]: 3 phases (coarse) -- Physics first, then Rendering+Depth, then UI+Claude

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- exact API needs prototyping (MEDIUM confidence)
- PBF tuning for artistic vs. physically accurate results -- needs experimentation

## Session Continuity

Last session: 2026-03-15T10:27:22.563Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-stable-physics/04-CONTEXT.md
