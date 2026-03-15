---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Make It Alive
status: active
stopped_at: null
last_updated: "2026-03-15"
last_activity: 2026-03-15 -- Milestone v2.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Photos become data, data becomes art -- the pipeline must faithfully extract meaningful signals and render them as explorable, visually stunning 3D sculptures.
**Current focus:** v2.0 — Make It Alive

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-15 — Milestone v2.0 started

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.0]: 3-phase coarse structure -- Foundation, Creative Sculpting, Discovery
- [v1.0]: pygfx/wgpu for rendering, PySide6 for GUI, WGSL compute shaders for sim
- [v1.0]: ONNX/DirectML for depth and CLIP models
- [v1.0]: CPU spatial hash build on init/restart only (not per-frame GPU hash)
- [v2.0]: User reports physics broken (particles just explode, no coherent forms)
- [v2.0]: User reports depth maps low quality (unsaturated, limited colors)
- [v2.0]: User reports UI needs complete rework
- [v2.0]: User wants organic, living sculptures (waves, morphism)
- [v2.0]: User open to tech stack changes if better alternatives exist
- [v2.0]: Research fluid physics engines before committing to approach

### Pending Todos

None yet.

### Blockers/Concerns

- [v1.0 carry-over]: ROCm on Windows is functional but young — must validate GPU paths
- [v2.0]: Current particle sim forces don't produce coherent forms — needs fundamental rework
- [v2.0]: Tech stack evaluation needed before committing to implementation approach

## Session Continuity

Last session: 2026-03-15
Stopped at: Milestone v2.0 initialization
Resume file: None
