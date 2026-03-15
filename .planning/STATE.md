---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: executing
stopped_at: Completed 04-05-PLAN.md
last_updated: "2026-03-15T12:25:00Z"
last_activity: "2026-03-15 -- Creative controls GUI and visual verification (04-05) -- Phase 4 complete"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 25
  completed_plans: 25
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 4 Complete -- Ready for Phase 5 (v2.0 Make It Alive)

## Current Position

Phase: 4 of 6 (Stable Physics) -- COMPLETE
Plan: 5 of 5 in current phase (done)
Status: Phase Complete
Last activity: 2026-03-15 -- Creative controls GUI and visual verification (04-05) -- Phase 4 complete

Progress: [██████████] 100% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 5 (v2.0)
- Average duration: 4.2min
- Total execution time: 21min

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 04    | 01   | 3min     | 2     | 4     |
| 04    | 02   | 4min     | 2     | 8     |
| 04    | 03   | 6min     | 2     | 6     |
| 04    | 04   | 5min     | 2     | 5     |
| 04    | 05   | 3min     | 2     | 5     |

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
- [04-04]: Curl noise uses 3 decorrelated FBM channels with large constant offsets
- [04-04]: Vorticity confinement uses simplified eta approximation (omega direction)
- [04-04]: XSPH and vorticity share same neighbor loop in finalize
- [04-05]: Cohesion slider maps solver_iterations 1-6 with Ethereal-to-Liquid spectrum
- [04-05]: Crossfade snaps iterations (discrete) but interpolates home_strength for smooth transition
- [04-05]: 4 essential sliders visible, 5 advanced in collapsible section

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- exact API needs prototyping (MEDIUM confidence)
- PBF tuning for artistic vs. physically accurate results -- needs experimentation
- GUI references to set_performance_mode need updating (deferred from 04-03)

## Session Continuity

Last session: 2026-03-15T12:25:00Z
Stopped at: Completed 04-05-PLAN.md -- Phase 4 (Stable Physics) fully complete
Resume file: .planning/phases/04-stable-physics/04-05-SUMMARY.md
