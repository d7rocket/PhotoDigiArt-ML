# Roadmap: Apollo 7

## Milestones

- [x] **v1.0 MVP** - Phases 1-3 (shipped 2026-03-14)
- [ ] **v2.0 Make It Alive** - Phases 4-6 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-3) - SHIPPED 2026-03-14</summary>

- [x] **Phase 1: Pipeline Foundation** - Photo to point cloud to interactive 3D viewport in a desktop GUI (completed 2026-03-14)
- [x] **Phase 2: Creative Sculpting** - Particles, fluid sim, parameter controls, depth, save/load, export (completed 2026-03-14)
- [x] **Phase 3: Discovery and Intelligence** - Semantic extraction, collection analysis, discovery mode, Claude API (completed 2026-03-15)

### Phase 1: Pipeline Foundation
**Goal**: User can load photos, see extracted features, and explore a 3D point cloud sculpture in a real-time desktop viewport
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, EXTRACT-01, EXTRACT-02, EXTRACT-03, RENDER-01, RENDER-02, RENDER-03, APP-01, APP-02, APP-03, APP-04
**Plans:** 5/5 plans complete

### Phase 2: Creative Sculpting
**Goal**: User can sculpt, animate, and export visually stunning data sculptures with full parameter control
**Depends on**: Phase 1
**Requirements**: EXTRACT-05, RENDER-04, RENDER-05, RENDER-06, SIM-01, SIM-02, SIM-03, SIM-04, CTRL-01, CTRL-03, CTRL-04, CTRL-05, CTRL-06
**Plans:** 8/8 plans complete

### Phase 3: Discovery and Intelligence
**Goal**: The system understands photo content semantically, reveals collection-level patterns, and proposes creative directions
**Depends on**: Phase 2
**Requirements**: EXTRACT-04, COLL-01, COLL-02, COLL-03, RENDER-07, CTRL-02, CTRL-07, DISC-01, DISC-02, DISC-03, DISC-04
**Plans:** 7/7 plans complete

</details>

## v2.0 Make It Alive

**Milestone Goal:** Transform the rough v1.0 prototype into a product that produces organic, living data sculptures -- fix physics so particles form coherent shapes, make rendering gallery-quality, polish the UI, and let Claude drive creative direction.

- [x] **Phase 4: Stable Physics** - PBF solver, home positions, force balance, and organic motion forces (completed 2026-03-15)
- [x] **Phase 5: Visual Quality** - Gallery-quality rendering, GPU performance, smooth transitions, and depth map fixes (completed 2026-03-15)
- [ ] **Phase 6: Interface and Intelligence** - Polished UI rework and Claude-driven creative direction

## Phase Details

### Phase 4: Stable Physics
**Goal**: Particles form coherent, organic, living shapes that sustain indefinitely instead of exploding into chaos
**Depends on**: Phase 3 (v1.0 complete)
**Requirements**: PHYS-01, PHYS-02, PHYS-03, PHYS-04, PHYS-05, PHYS-06, PHYS-07, PHYS-08, PHYS-09
**Success Criteria** (what must be TRUE):
  1. Particles maintain a recognizable sculptural form derived from source photo geometry for 1000+ frames without dispersing, collapsing, or exploding
  2. User can adjust solver iterations and see the simulation character change from wispy gas (1 iteration) to cohesive liquid (4+ iterations) in real-time
  3. Sculptures exhibit organic, living motion -- visible flowing, swirling, and breathing behavior without any user interaction
  4. Simulation runs at 60fps with 500K+ particles on the RX 9060 XT without GPU timeout (TDR) errors
  5. Force and velocity values remain bounded -- no NaN, Inf, or runaway acceleration under any parameter combination
**Plans:** 5/5 plans complete

Plans:
- [x] 04-01-PLAN.md -- PBF parameters, buffer extensions, and test scaffolds
- [x] 04-02-PLAN.md -- PBF solver core: 7 WGSL shaders and PBFSolver orchestrator
- [x] 04-03-PLAN.md -- Engine integration: wire PBF, delete SPH, CFL timestep
- [x] 04-04-PLAN.md -- Organic motion: curl noise, vortex confinement, breathing
- [x] 04-05-PLAN.md -- Creative controls: solver iterations GUI, visual verification

### Phase 5: Visual Quality
**Goal**: Sculptures look like gallery-worthy art with smooth, luminous rendering and the pipeline handles 1M+ particles without CPU bottleneck
**Depends on**: Phase 4
**Requirements**: REND-01, REND-02, REND-03, REND-04, REND-05, REND-06, DPTH-01, DPTH-02
**Success Criteria** (what must be TRUE):
  1. Particles render as soft, round, glowing points with additive blending that creates luminous clusters -- not hard squares
  2. Viewport defaults to white background and bloom/glow post-processing is visible on particle clusters
  3. Changing any simulation or visual parameter crossfades smoothly over ~0.5 seconds instead of popping instantly
  4. Rendering sustains 60fps at 1M+ particles by sharing GPU buffers directly between compute and render (no CPU readback)
  5. Depth maps extracted from photos show full contrast and color saturation via CLAHE post-processing
**Plans:** 4/4 plans complete

Plans:
- [x] 05-01-PLAN.md -- GPU buffer sharing: extract-positions shader and zero-copy render
- [x] 05-02-PLAN.md -- CLAHE depth enhancement and enriched color extraction
- [x] 05-03-PLAN.md -- White background, luminous alpha, and bloom retuning
- [x] 05-04-PLAN.md -- Crossfade engine and visual verification checkpoint

### Phase 6: Interface and Intelligence
**Goal**: The application looks and feels polished with logical controls, and Claude can analyze photos to suggest parameter sets that produce compelling sculptures
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02, UI-03, UI-04, CLAU-01, CLAU-02, CLAU-03, CLAU-04
**Success Criteria** (what must be TRUE):
  1. UI has clean visual hierarchy with qt-material theming -- 6 essential sliders visible by default, advanced parameters collapsed but accessible
  2. Parameter presets show visual thumbnails and can be selected to instantly configure the sculpture
  3. User can click a button to have Claude analyze the loaded photo(s) and receive a suggested parameter set with artistic rationale
  4. Claude-suggested parameters apply via smooth crossfade into the viewport, and user can iterate with "more/less like this" refinement
  5. All Claude features work asynchronously -- the viewport never freezes during API calls, and core functionality works fully offline
**Plans:** 4 plans

Plans:
- [ ] 06-01-PLAN.md -- qt-material theming, tabbed layout restructure, and toolbar strip
- [ ] 06-02-PLAN.md -- Pydantic models, Claude suggestion service, and settings dialog
- [ ] 06-03-PLAN.md -- Preset grid with gradient thumbnails and v2.0 built-in presets
- [ ] 06-04-PLAN.md -- Claude AI panel, refinement loop, and visual verification

## Progress

**Execution Order:**
Phases execute in numeric order: 4 -> 5 -> 6

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Pipeline Foundation | v1.0 | 5/5 | Complete | 2026-03-14 |
| 2. Creative Sculpting | v1.0 | 8/8 | Complete | 2026-03-14 |
| 3. Discovery and Intelligence | v1.0 | 7/7 | Complete | 2026-03-15 |
| 4. Stable Physics | v2.0 | Complete    | 2026-03-15 | 2026-03-15 |
| 5. Visual Quality | v2.0 | Complete    | 2026-03-15 | 2026-03-15 |
| 6. Interface and Intelligence | v2.0 | 0/4 | In progress | - |
