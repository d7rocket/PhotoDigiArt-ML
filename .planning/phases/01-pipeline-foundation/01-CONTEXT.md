# Phase 1: Pipeline Foundation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Load photos (single or batch), extract visual features (color, edges, depth), generate 3D point clouds from extracted features, and render them in an interactive real-time viewport inside a PySide6 desktop GUI. This phase delivers the end-to-end pipeline from photo input to explorable 3D sculpture. Creative controls (sliders, presets, undo) and simulation (particles, fluid) are Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Viewport Experience
- Orbit-centric camera: click-drag to rotate around sculpture center, scroll to zoom. No free-fly mode.
- Dark gradient background (subtle dark gray to black) — not pure black
- Self-illuminated points: points emit their own color, no external lighting. Pure data glow aesthetic.
- Auto-frame on sculpture load: camera automatically positions to show full sculpture, then user takes over
- Default three-quarter view angle to immediately reveal the 3D depth effect
- Target 30+ FPS minimum with orbit controls

### Photo-to-Points Mapping
- Two spatial layout modes:
  - **Depth-projected** (default): depth map drives Z-axis displacement, creating a relief sculpture
  - **Feature-clustered**: points grouped by feature similarity, floating in abstract 3D space
- Full pixel density: every pixel becomes a point (12MP photo = 12M points)
- Original pixel colors: points retain the photo's actual colors
- Depth exaggeration: 3-5x amplification by default for dramatic sculptural effect
- Round soft particles: Gaussian-blurred circles for organic, glowing Anadol-style look
- Multi-photo handling:
  - **Stacked layers** (default): each photo is a separate Z-layer, browse through like geological strata
  - **Merged cloud** toggle: all points merge into unified sculpture, photo boundaries dissolve
- LOD (level-of-detail) system for scaling to thousands of photos: full resolution close, simplified at distance

### GUI Layout & Design
- Viewport-dominant layout: 3D viewport takes 70%+ of screen
- Right side panel split: controls on top, photo library below
- Collapsible bottom strip: feature viewer showing extracted data as thumbnail cards (color palette swatch, edge map, depth map)
- Dark theme only — no light mode
- **Visual identity: Maya x Unreal Engine x modern SaaS**
  - Maya's panel density and professional tool organization
  - Unreal's dark cinematic polish
  - Modern SaaS clean typography and refined spacing
- Custom-styled Qt widgets, not stock PySide6 defaults
- Electric blue accent color for interactive elements (buttons, sliders, active selections)
- GUI must be polished and visually refined — the app itself should look premium

### Extraction Pipeline UX
- Overall pipeline progress bar: "Processing 47/200 photos..." — clean and simple
- Progressive viewport build: point cloud grows in real-time as each photo completes extraction
- Extraction order: color first (fastest, gives immediate visual feedback), then edges, then depth (most GPU-intensive)
- Re-extractable: user can re-run extraction with different settings on already-loaded photos (e.g., different edge sensitivity, depth model)
- Feature results cached after extraction — no re-processing unless user requests it

### Claude's Discretion
- Photo library panel design (grid thumbnails vs list — pick what suits the thin right panel best)
- Exact point size defaults and ranges
- LOD distance thresholds and simplification strategy
- Feature clustering algorithm for the alternative spatial mode
- Error handling for unsupported image formats
- Keyboard shortcuts for camera controls

</decisions>

<specifics>
## Specific Ideas

- Anadol-style aesthetic: flowing, organic, self-illuminated data forms against dark backgrounds
- The app should feel like a premium creative tool — not a developer prototype
- Progressive build creates a "watching the sculpture emerge" experience during extraction
- Three-quarter default view means the depth effect is immediately visible without the user needing to rotate
- Full pixel density means no data is lost in the transformation — every pixel matters
- User has aerospace background — fluid dynamics concepts are intuitive, not intimidating

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns

### Integration Points
- PySide6 + pygfx/wgpu: rendercanvas QRenderWidget for embedding 3D viewport in Qt
- ONNX Runtime + DirectML: depth model inference on AMD GPU
- OpenCV: image loading, color extraction, edge detection

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-pipeline-foundation*
*Context gathered: 2026-03-14*
