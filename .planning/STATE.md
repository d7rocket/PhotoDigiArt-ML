---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: in-progress
stopped_at: Completed 05-02 depth and color enrichment
last_updated: "2026-03-15T16:05:08Z"
last_activity: 2026-03-15 -- CLAHE depth enhancement and color enrichment (05-02)
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 29
  completed_plans: 27
  percent: 93
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 5 -- Visual Quality (v2.0 Make It Alive)

## Current Position

Phase: 5 of 6 (Visual Quality)
Plan: 2 of 4 in current phase
Status: In Progress
Last activity: 2026-03-15 -- CLAHE depth enhancement and color enrichment (05-02)

Progress: [█████████▌] 93% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 7 (v2.0)
- Average duration: 4.4min
- Total execution time: 31min

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 04    | 01   | 3min     | 2     | 4     |
| 04    | 02   | 4min     | 2     | 8     |
| 04    | 03   | 6min     | 2     | 6     |
| 04    | 04   | 5min     | 2     | 5     |
| 04    | 05   | 3min     | 2     | 5     |
| 05    | 01   | 5min     | 2     | 4     |
| 05    | 02   | 5min     | 2     | 6     |

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
- [05-02]: CLAHE clip_limit=3.0, tile_size=8 for optimal depth contrast
- [05-02]: Saturation boost default 1.3 (30%) -- middle of 20-40% user range
- [05-02]: Color enrichment baked at extraction time via generator.py call site
- [05-01]: Lazy pipeline creation for extract shader (built on first dispatch)
- [05-01]: CPU readback fallback preserved for safety if GPU sharing fails
- [05-01]: Color buffer gets VERTEX flag directly (no extract shader needed)

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- RESOLVED: _wgpu_object injection works (HIGH confidence)
- PBF tuning for artistic vs. physically accurate results -- needs experimentation
- GUI references to set_performance_mode need updating (deferred from 04-03)

## Session Continuity

Last session: 2026-03-15T16:05:08Z
Stopped at: Completed 05-02 depth and color enrichment
Resume file: .planning/phases/05-visual-quality/05-03-PLAN.md
