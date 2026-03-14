# Phase 3: Discovery and Intelligence - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

The system understands photo content semantically, reveals collection-level patterns, and proposes creative directions — turning Apollo 7 from a tool into a creative collaborator. Delivers semantic extraction (CLIP/BLIP), collection analysis, discovery mode with feedback loop, feature-to-visual mapping editor, preset interpolation, and optional Claude API enrichment. All core functionality works fully offline.

</domain>

<decisions>
## Implementation Decisions

### Semantic Understanding
- Rich multi-layer extraction: scene-level mood (serene, chaotic, melancholic), object detection (tree, car, person), and dense embedding vector for similarity
- Bundled ONNX models shipped in models/ directory (like Depth Anything V2) — works offline immediately
- Automatic in pipeline: runs after depth extraction as part of the standard extraction flow, not a separate manual step
- Tags displayed as colored pills/badges with confidence scores (e.g., "serene 0.87", "forest 0.72") in a new collapsible section in the feature viewer

### Collection Patterns
- 3D embedding cloud rendered IN the viewport — each photo is a point in embedding space alongside the sculpture
- Collection patterns feed into sculpture via both spatial seeding AND continuous force attractors:
  - Similar photos start near each other (spatial seeding from embedding positions)
  - Clusters act as ongoing force attractors — sculpture breathes around semantic centers
- Click-to-isolate: clicking a cluster isolates those photos' particles (others dim/hide) for focused sculpting of thematic subsets
- Outlier photos treated equally — no special visual treatment, no judgment about which photos are "normal"

### Discovery Mode
- Random walk with constraints: randomize parameters within sensible ranges derived from photo features (serene photo → calmer ranges, chaotic → wilder)
- Feedback via 3-4 abstract dimensional sliders: Energy (calm↔chaotic), Density (sparse↔dense), Flow (rigid↔fluid), and optionally Structure (organic↔geometric)
  - Each slider maps to clusters of simulation parameters under the hood
  - Adjusting a dimension steers future random proposals in that direction
- Visual history strip: horizontal strip of thumbnail snapshots showing recent proposals — click any to jump back. Non-linear, visual navigation.

### Feature-to-Visual Mapping Editor
- Node-wire patch bay: feature outputs on the left, parameter inputs on the right, drag wires to connect
- Dedicated full overlay panel: opens as a large overlay/modal (like a DAW's routing matrix), toggled via button or shortcut — not crammed into the sidebar
- Each connection has a strength/scale control

### Preset Interpolation
- Crossfade slider: select two presets, drag a slider from A to B — all parameters lerp smoothly in real-time
- Like a DJ crossfader between any two saved presets

### Claude API Integration
- Enrichment badge: subtle "Enhance with AI" toggle in settings
- When enabled: semantic tags get richer descriptions, node editor suggests creative mappings
- When disabled: everything still works, just less descriptive
- Offline-first guarantee: no core feature depends on API availability

### Claude's Discretion
- CLIP vs BLIP model selection and specific ONNX variants
- Clustering algorithm for collection analysis (DBSCAN, k-means, etc.)
- t-SNE vs UMAP for embedding projection to 3D
- Node editor visual design and interaction patterns
- Parameter animation implementation (LFOs, noise functions, envelopes for RENDER-07)
- Discovery mode constraint derivation logic (how features map to parameter ranges)
- How the enrichment badge communicates with Claude API (SDK, HTTP, etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseExtractor` (apollo7/extraction/base.py): inherit for ClipExtractor and BlipExtractor — implement `name` property + `extract()` method, return `ExtractionResult`
- `DepthExtractor` (apollo7/extraction/depth.py): reference pattern for ONNX model loading — lazy init, DirectML provider, fallback to CPU
- `ExtractionPipeline` (apollo7/extraction/pipeline.py): orchestrates extractors sequentially, caches results — just add new extractors to the list
- `FeatureViewerPanel` (apollo7/gui/panels/feature_viewer.py): 3 collapsible sections (color, edge, depth) — add `_build_semantic_section()` for tag cloud
- `PresetManager` (apollo7/project/presets.py): JSON presets with sim_params + postfx_params — extend schema for feature mappings
- `SimulationParams` (apollo7/simulation/parameters.py): 17 tunable params, `to_uniform_bytes()` for GPU upload — add semantic routing weights
- `FeatureCluster` (apollo7/pointcloud/feature_cluster.py): groups pixels by color — extend to group by semantic embedding similarity

### Established Patterns
- Signal/slot for UI ↔ viewport (controls_panel → main_window → viewport)
- QRunnable + QThreadPool for background compute
- Dark theme with electric blue accent (#0078FF)
- Collapsible sections in panels with consistent styling
- All params hot-reload via uniform buffer update (no restart needed)
- Lazy model loading on first use (not import time)

### Integration Points
- `ExtractionPipeline.__init__()`: register new semantic extractors in sequence
- `FeatureViewerPanel.update_features()`: already handles any ExtractionResult keys — new semantic data flows through
- `ViewportWidget`: embed 3D embedding cloud as additional scene objects
- `SimulationEngine`: add semantic force channels (cluster attractors) alongside existing forces
- `MainWindow`: wire discovery panel, mapping editor toggle, enrichment settings

</code_context>

<specifics>
## Specific Ideas

- The 3D embedding cloud makes the collection's semantic structure visible as a spatial form — photos cluster naturally in 3D space based on meaning
- Discovery mode dimensional sliders are the "creative collaborator" UX — abstract enough to feel like artistic direction, not parameter tuning
- Visual history strip lets artists browse through proposals like flipping through sketches — non-destructive exploration
- Node-wire editor should feel like a DAW routing matrix — professional creative tool aesthetic, not a programming interface
- Crossfade slider between presets creates a "morphing" experience — the sculpture transitions live between two saved states

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-discovery-and-intelligence*
*Context gathered: 2026-03-14*
