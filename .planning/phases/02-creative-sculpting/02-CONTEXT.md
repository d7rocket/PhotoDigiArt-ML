# Phase 2: Creative Sculpting - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add particle systems, fluid dynamics, flow fields, post-processing effects, full parameter controls with undo/redo, save/load projects, export high-res images, and preset library. This phase transforms the static point cloud pipeline into an interactive creative sculpting tool. Semantic extraction, discovery mode, and Claude API are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Particle & Fluid Simulation
- **Continuous loop animation**: simulation runs continuously — sculptures are always in motion, living data forms
- Speed/turbulence sliders control energy level (gentle drifting ↔ energetic swirls)
- Four force types, all available simultaneously:
  - **Perlin noise flow fields**: smooth organic currents (classic generative art)
  - **Attraction/repulsion**: feature-driven (e.g., similar colors attract)
  - **SPH fluid dynamics**: real fluid sim with viscosity, pressure, surface tension
  - **Gravity + wind**: directional forces for settling, drifting
- Features drive simulation both as **initial conditions** AND **continuous influence** on flow fields:
  - Edge maps define turbulence zones
  - Depth maps define current direction
  - Colors define temperature/force strength
- Target: millions of particles (1-5M) in real-time on GPU compute
- Fading alpha trails: ghost particles left behind that fade over time, showing flow history

### Post-Processing Effects
- **Bloom/glow**: adjustable intensity slider from subtle halo to dramatic radiance
- **Depth of field**: focal plane with blur for cinematic focus
- **Motion trails**: fading alpha trails on moving particles
- **Ambient occlusion**: dense regions darken subtly for perceived volume
- All effects adjustable via sliders — artist controls the mood

### Render-then-Interact Flow
- Manual "Simulate" button: user reviews static point cloud first, then clicks to bring it alive
- **Always interactive during simulation**: orbit, zoom, adjust sliders while particles flow (GPU sim, responsive UI)
- FPS counter visible in viewport
- "Performance mode" toggle: reduces sim quality for smooth interaction when FPS drops
- Parameter change behavior depends on type:
  - **Visual params** (size, color, bloom, opacity): hot-reload, take effect immediately
  - **Physics params** (forces, viscosity, flow field): restart sim from initial conditions

### Save/Load & Export
- Project file includes:
  - All parameters and sim state (every slider value, force config, camera position)
  - Photo references (paths, not copies — keeps files small)
  - Cached extraction data (pre-computed features, avoid re-extraction on load)
  - Point cloud snapshot (current positions/colors for instant visual on load)
- Export: PNG only (lossless with alpha transparency)
- Export resolutions: viewport/2x/4x quick buttons + custom width x height input + presets (4K, 8K, Instagram square)
- Transparent background option on export

### Preset Library
- Categorized library: presets organized by category (Organic, Geometric, Chaotic, etc.)
- Browse and preview before applying
- Named snapshots: save current state as e.g., "Crystalline" or "Data Storm"

### Undo & Parameter Control
- **Debounced slider undo**: slider drags collapse into one undo entry (final value only). Other changes are immediate.
- Ctrl+Z undo, Ctrl+Shift+Z redo
- Per-section reset buttons (reset just Forces, or just Post-FX) plus global "Reset All"
- Standard creative tool shortcuts:
  - Ctrl+Z / Ctrl+Shift+Z: undo/redo
  - Ctrl+S: save project
  - Ctrl+E: export image
  - Space: pause/resume simulation

### Claude's Discretion
- Controls panel organization (collapsible sections vs tabbed — pick what fits the thin right panel)
- Project file format (JSON, binary, or compressed archive)
- SPH solver parameters and defaults
- Perlin noise octaves and frequency defaults
- Performance mode quality reduction strategy
- Bloom implementation approach (screen-space blur passes)

</decisions>

<specifics>
## Specific Ideas

- Anadol-style continuous flowing data sculptures — not static renders
- User has aerospace background — SPH fluid dynamics is intuitive, not intimidating
- "Gallery-worthy" is a hard requirement: post-processing (bloom, DoF, AO, trails) must make output visually stunning
- The simulation should feel like the data is alive and breathing
- Alpha trails show flow history — where the data has been, not just where it is
- Features continuously shape the flow field — the photos aren't just initial conditions, they're the ongoing force that sculpts the motion

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ViewportWidget` (apollo7/gui/widgets/viewport_widget.py): pygfx scene with PointsGaussianBlobMaterial, add_points(), clear_points(), auto_frame()
- `ControlsPanel` (apollo7/gui/panels/controls_panel.py): signal-driven sliders and radio buttons — extend for simulation controls
- `ExtractionWorker` (apollo7/workers/extraction_worker.py): QRunnable pattern for background compute — reuse for simulation worker
- `FeatureCache` (apollo7/extraction/cache.py): in-memory cache keyed by photo+extractor — could extend for sim state
- `theme.py`: comprehensive QSS with accent color, radio buttons, sliders — add new widget styles here
- `settings.py`: centralized config with ranges and defaults — add sim/post-fx params here

### Established Patterns
- Signal/slot for UI ↔ viewport communication (controls_panel signals → main_window → viewport methods)
- QRunnable + QThreadPool for background compute (keeps UI responsive)
- Dark theme with electric blue accent (#0078FF)
- Viewport-dominant layout with thin right panel

### Integration Points
- `MainWindow._on_extraction_finished()`: wire simulation trigger after extraction completes
- `ViewportWidget`: needs compute shader integration for GPU particle sim
- `ControlsPanel`: extend with Simulation, Forces, Post-FX sections
- `settings.py`: add simulation defaults (force strengths, viscosity, etc.)

</code_context>

<deferred>
## Deferred Ideas

- UI polish pass (user noted "ui will need some polish later on") — could be a dedicated polish phase or part of Phase 3

</deferred>

---

*Phase: 02-creative-sculpting*
*Context gathered: 2026-03-14*
