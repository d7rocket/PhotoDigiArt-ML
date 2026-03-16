---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: completed
stopped_at: Phase 6 planned (4 plans, 2 waves)
last_updated: "2026-03-16T12:54:47.996Z"
last_activity: "2026-03-15 -- Phase 5 complete: crossfade engine verified and rendering fixes applied (05-04)"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 13
  completed_plans: 9
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 5 -- Visual Quality (v2.0 Make It Alive)

## Current Position

Phase: 5 of 6 (Visual Quality) -- COMPLETE
Plan: 4 of 4 in current phase (all done)
Status: Phase 5 complete, ready for Phase 6
Last activity: 2026-03-15 -- Phase 5 complete: crossfade engine verified and rendering fixes applied (05-04)

Progress: [██████████] 100% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 9 (v2.0)
- Average duration: 4.4min
- Total execution time: 42min

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 04    | 01   | 3min     | 2     | 4     |
| 04    | 02   | 4min     | 2     | 8     |
| 04    | 03   | 6min     | 2     | 6     |
| 04    | 04   | 5min     | 2     | 5     |
| 04    | 05   | 3min     | 2     | 5     |
| 05    | 01   | 5min     | 2     | 4     |
| 05    | 02   | 5min     | 2     | 6     |
| 05    | 03   | 3min     | 2     | 4     |
| 05    | 04   | 8min     | 3     | 5     |

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
- [05-03]: Warm off-white #F8F6F3 (gallery art paper, not pure white)
- [05-03]: Bloom strength 0.5 with filter_radius 0.015 and Karis averaging for colored halos
- [05-03]: Blend alpha 0.45 for luminous cluster overlap
- [05-04]: Cubic ease-out 1-(1-t)^3 for iOS-like parameter crossfade
- [05-04]: 400ms transition duration (middle of 300-500ms user range)
- [05-04]: A/B preset crossfade uses same CrossfadeEngine for unified behavior
- [05-04]: GPU buffer sharing disabled -- pygfx vec3/vec4 mismatch; CPU readback fallback active
- [05-04]: Bloom disabled on white background (washes out particles)
- [05-04]: Saturation boost 1.8, alpha 0.92 for vibrant colors on white background

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- RESOLVED: disabled due to vec3/vec4 mismatch, CPU readback fallback active
- PBF tuning for artistic vs. physically accurate results -- needs experimentation
- GUI references to set_performance_mode need updating (deferred from 04-03)

## Session Continuity

Last session: 2026-03-16T12:54:47.994Z
Stopped at: Phase 6 planned (4 plans, 2 waves)
Resume file: .planning/phases/06-interface-and-intelligence/06-01-PLAN.md
