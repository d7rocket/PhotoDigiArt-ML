# Roadmap: Apollo 7

## Overview

Apollo 7 transforms photographs into explorable 3D data sculptures. The roadmap delivers this in three phases: first proving the end-to-end pipeline (photo in, point cloud out, interactive viewport), then adding the creative sculpting tools that make it usable for art (particles, fluid sim, parameter controls, export), and finally building the differentiating intelligence layer (semantic understanding, collection analysis, discovery mode, Claude API).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Pipeline Foundation** - Photo to point cloud to interactive 3D viewport in a desktop GUI (completed 2026-03-14)
- [ ] **Phase 2: Creative Sculpting** - Particles, fluid sim, parameter controls, depth, save/load, export
- [ ] **Phase 3: Discovery and Intelligence** - Semantic extraction, collection analysis, discovery mode, Claude API

## Phase Details

### Phase 1: Pipeline Foundation
**Goal**: User can load photos, see extracted features, and explore a 3D point cloud sculpture in a real-time desktop viewport
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, EXTRACT-01, EXTRACT-02, EXTRACT-03, RENDER-01, RENDER-02, RENDER-03, APP-01, APP-02, APP-03, APP-04
**Success Criteria** (what must be TRUE):
  1. User can drag-drop or browse to load a single photo or a folder of photos, with progress feedback during batch ingestion
  2. User can view extracted color palettes, edge maps, and depth maps for any ingested photo
  3. User sees a 3D point cloud generated from extracted features, rendered in a real-time viewport with orbit, zoom, and pan at 30+ FPS
  4. Point cloud rendering supports configurable point size, color mapping, opacity, and additive blending
  5. The application runs on Windows 11 with AMD RX 9060 XT (no CUDA), UI stays responsive during long extraction runs
**Plans:** 5/5 plans complete

Plans:
- [x] 01-01-PLAN.md — Project setup, GUI skeleton, and embedded pygfx 3D viewport with test points
- [x] 01-02-PLAN.md — Photo ingestion (single + batch), library panel, and progress feedback
- [x] 01-03-PLAN.md — Color and edge extraction with pluggable interface and feature strip
- [x] 01-04-PLAN.md — Depth extraction via ONNX/DirectML and point cloud generation
- [x] 01-05-PLAN.md — End-to-end integration: progressive build, controls, multi-photo support

### Phase 2: Creative Sculpting
**Goal**: User can sculpt, animate, and export visually stunning data sculptures with full parameter control
**Depends on**: Phase 1
**Requirements**: EXTRACT-05, RENDER-04, RENDER-05, RENDER-06, SIM-01, SIM-02, SIM-03, SIM-04, CTRL-01, CTRL-03, CTRL-04, CTRL-05, CTRL-06
**Success Criteria** (what must be TRUE):
  1. User can inspect all extracted features per photo (color palette, edge map, depth map, semantic tags) in a unified feature viewer
  2. GPU-computed particle systems with physically-based dynamics and flow field motion produce visually compelling, gallery-worthy output
  3. User can tune every visual parameter via sliders and controls that update the viewport in real-time, with undo/redo on all changes
  4. User can save/load full project state and export high-resolution still images with transparent background option
  5. Presets can be saved, loaded, and organized -- heavy compute runs in background while viewport remains smooth for exploration
**Plans:** 1/6 plans executed

Plans:
- [ ] 02-01-PLAN.md — GPU particle simulation engine with WGSL compute shaders (all 4 force types, SPH, flow fields)
- [ ] 02-02-PLAN.md — Feature viewer panel and undo/redo system with slider debouncing
- [ ] 02-03-PLAN.md — Simulation UI controls, FPS counter, simulate button, viewport wiring
- [ ] 02-04-PLAN.md — Post-processing effects (bloom, DoF, SSAO, alpha trails)
- [ ] 02-05-PLAN.md — Save/load projects, high-res PNG export, preset library
- [ ] 02-06-PLAN.md — End-to-end creative sculpting verification checkpoint

### Phase 3: Discovery and Intelligence
**Goal**: The system understands photo content semantically, reveals collection-level patterns, and proposes creative directions -- turning Apollo 7 from a tool into a creative collaborator
**Depends on**: Phase 2
**Requirements**: EXTRACT-04, COLL-01, COLL-02, COLL-03, RENDER-07, CTRL-02, CTRL-07, DISC-01, DISC-02, DISC-03, DISC-04
**Success Criteria** (what must be TRUE):
  1. Pipeline extracts semantic features (objects, scenes, mood) from photos via local CLIP/BLIP models, and user can view semantic tags alongside other features
  2. User can visualize collection-level patterns (clustering, trends, outliers in embedding space) and those patterns feed into sculpture generation
  3. Discovery mode proposes compositions from extracted data with a "more/less like this" feedback loop, all running locally without API
  4. User can route extracted features to visual parameters through a mapping editor, and smoothly interpolate between saved presets
  5. Optional Claude API integration enriches photo annotation and suggests creative mappings, but all core functionality works fully offline

**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pipeline Foundation | 5/5 | Complete    | 2026-03-14 |
| 2. Creative Sculpting | 1/6 | In Progress|  |
| 3. Discovery and Intelligence | 0/2 | Not started | - |
