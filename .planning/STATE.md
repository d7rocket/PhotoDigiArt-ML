---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: executing
stopped_at: Completed 06-03-PLAN.md
last_updated: "2026-03-16T13:09:00Z"
last_activity: 2026-03-16 -- Preset grid with gradient thumbnail cards (06-03)
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 13
  completed_plans: 12
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, living 3D sculptures.
**Current focus:** Phase 6 -- Interface and Intelligence (v2.0 Make It Alive)

## Current Position

Phase: 6 of 6 (Interface and Intelligence)
Plan: 4 of 4 in current phase (06-01, 06-02, 06-03 complete)
Status: Executing Phase 6
Last activity: 2026-03-16 -- Preset grid with gradient thumbnail cards (06-03)

Progress: [█████████░] 92% (v2.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 12 (v2.0)
- Average duration: 4.2min
- Total execution time: 50min

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
| 06    | 01   | 5min     | 2     | 6     |
| 06    | 02   | 3min     | 2     | 4     |
| 06    | 03   | 3min     | 2     | 3     |

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
- [06-01]: qt-material dark_blue.xml base theme with custom QSS overrides layered on top
- [06-01]: Panels reparented into Section widgets inside tabs rather than decomposed
- [06-01]: SimulationPanel buttons hidden (not removed) for backward compatibility
- [Phase 06]: SculptureParams uses Pydantic Field(ge/le) for bounds matching simulation ranges
- [Phase 06]: Config file at ~/.apollo7/config.json with env var taking priority over file
- [06-03]: PresetCard generates gradient icon via HSV mapping of solver_iterations, noise_amplitude, home_strength
- [06-03]: crossfade_changed signal kept as Signal(dict) matching existing main_window wiring
- [06-03]: Built-in category added to DEFAULT_CATEGORIES list ahead of legacy categories

### Pending Todos

None yet.

### Blockers/Concerns

- AMD RDNA 4 compute driver maturity -- test PBF solver on target hardware immediately after implementation
- GPU buffer sharing between wgpu compute and pygfx render -- RESOLVED: disabled due to vec3/vec4 mismatch, CPU readback fallback active
- PBF tuning for artistic vs. physically accurate results -- needs experimentation
- GUI references to set_performance_mode need updating (deferred from 04-03)

## Session Continuity

Last session: 2026-03-16T13:09:00Z
Stopped at: Completed 06-03-PLAN.md
Resume file: .planning/phases/06-interface-and-intelligence/06-04-PLAN.md
