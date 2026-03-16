# Phase 6: Interface and Intelligence - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Polished UI rework with qt-material theming, logical tabbed panel layout, visual preset thumbnails, and Claude-driven creative direction that analyzes photos and suggests parameter sets with iterative refinement. The rendering engine, physics, and crossfade systems are complete from prior phases -- this phase only touches GUI structure, theming, preset presentation, and Claude API integration UX.

</domain>

<decisions>
## Implementation Decisions

### Panel Layout & Organization
- Tabbed groups: 3 tabs at top of right sidebar -- **Create**, **Explore**, **Export**
- **Create tab**: Rendering section (Point Size, Opacity) + Simulation section (Cohesion, Home Strength, Flow Intensity, Breathing Rate) + PostFX collapsed + Advanced collapsed
- **Explore tab**: Claude AI panel + Presets (grid with crossfade) + Discovery (dimensional mapper)
- **Export tab**: Library (loaded photos, thumbnails) + Export (PNG, resolution)
- 6 essential sliders visible by default: 4 simulation (Cohesion, Home Strength, Flow Intensity, Breathing Rate) + 2 rendering (Point Size, Opacity). Depth Exaggeration moves to Advanced
- Simulate/Pause + Reset Camera as persistent toolbar strip above the tab bar, always visible regardless of active tab

### Claude Creative Direction UX
- Card-based suggestion display: artistic rationale (2-3 sentences) + parameter values as labeled chips + Apply button
- Apply crossfades parameters into viewport via existing CrossfadeEngine
- Manual trigger only: "Analyze with Claude" button in AI panel. No auto-analyze on photo load
- Refinement via direction buttons after applying: "More fluid" / "More structured" / "More vibrant" / "More subtle" + "Start over" / "Keep this"
- Each refinement sends current params + direction to Claude for updated suggestion
- All API calls async via background worker -- viewport never freezes
- API key via Settings dialog (Menu > Settings). Stored in local config file. First-time prompt if key missing when user clicks Analyze

### Preset Thumbnails
- Generated gradient icons from preset's color palette and key params (not viewport screenshots)
- Grid display: 2-3 column grid of thumbnail cards (gradient icon + preset name). Click to apply with crossfade
- Ship with 5-6 built-in presets covering the spectrum: Ethereal, Liquid, Breathing, Turbulent, Dense, Calm

### qt-material Theming
- qt-material dark theme as foundation + custom QSS overrides for Apollo 7-specific widgets (viewport, preset grid, AI suggestion card)
- Keep electric blue accent (#0078FF) -- already established, good contrast on dark panels
- Keep Segoe UI font, refine size hierarchy (headers larger, labels smaller)
- Dark panels frame white viewport (carried from Phase 5)

### Claude's Discretion
- Exact qt-material XML configuration and override specifics
- Gradient icon generation algorithm for preset thumbnails
- Direction button labels and exact phrasing (the 4 refinement directions)
- Claude prompt engineering for photo analysis and parameter suggestion
- Pydantic model structure for structured Claude outputs
- Loading spinner design during API calls
- Settings dialog layout and field organization
- Tab bar visual style (underline, pill, or standard qt-material tabs)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing GUI architecture
- `apollo7/gui/main_window.py` -- Root layout, panel wiring, signal/slot connections. Must restructure for tabbed layout
- `apollo7/gui/theme.py` -- Current QSS stylesheet to be replaced by qt-material + overrides
- `apollo7/gui/panels/controls_panel.py` -- Rendering sliders, slider factory pattern to reuse
- `apollo7/gui/panels/simulation_panel.py` -- PBF sliders, essential/advanced grouping pattern
- `apollo7/gui/panels/preset_panel.py` -- Current preset list + `_Section` collapsible widget pattern
- `apollo7/gui/widgets/crossfade.py` -- A/B preset crossfade widget

### Claude API integration
- `apollo7/api/enrichment.py` -- Existing Claude API service with background worker pattern. Needs expansion for structured param suggestions
- `apollo7/api/__init__.py` -- API module entry point

### Configuration
- `apollo7/config/settings.py` -- All parameter defaults and ranges. Claude suggestions must respect these bounds
- `apollo7/animation/crossfade_engine.py` -- CrossfadeEngine for smooth parameter application (from Phase 5)

### Project context
- `.planning/PROJECT.md` -- Core value, constraints, AMD GPU requirement
- `.planning/REQUIREMENTS.md` -- UI-01 through UI-04, CLAU-01 through CLAU-04 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_Section` widget (preset_panel.py): Collapsible header + content pattern -- use for all section headers in tabbed panels
- `_create_slider` factory (controls_panel.py): Slider with min/max range binding and value labels -- extract into shared utility
- `CrossfadeEngine` (animation/crossfade_engine.py): Cubic ease-out interpolation, 400ms duration -- Claude suggestions apply through this
- `EnrichmentService` (api/enrichment.py): Background worker with signals, graceful offline fallback -- extend for structured param suggestions
- `lerp_presets()` function: A/B interpolation between preset dicts -- reuse for crossfade widget in new preset grid
- `PresetManager`: File-based preset persistence with categories -- extend for built-in presets and gradient icon generation

### Established Patterns
- Signal/slot wiring: Panels emit typed signals, main_window connects to viewport methods
- Background workers: QRunnable + signals for non-blocking operations (ingestion, extraction, enrichment)
- Undo/redo: ParameterChangeCommand wrapping -- Claude Apply should integrate with undo stack
- Parameter naming: Consistent `param_name` strings across all panels and preset dicts

### Integration Points
- `main_window.py` right panel: Replace QScrollArea + vertical stack with QTabWidget
- `main_window.py` toolbar area: Add Simulate/Pause strip above new tab widget
- `enrichment.py`: Add `suggest_parameters()` method returning Pydantic-validated param dict
- `preset_panel.py`: Replace list widget with grid widget, add gradient icon renderer
- `theme.py`: Replace entire file with qt-material setup + override stylesheet

</code_context>

<specifics>
## Specific Ideas

- Tab grouping follows workflow: Create (sculpt params) -> Explore (AI + presets + discovery) -> Export (output)
- Claude suggestion card should feel like a creative brief -- rationale explains WHY these parameters suit the photo
- Direction buttons for refinement (no typing needed) -- quick iterative loop
- Preset gradient icons give visual identity without requiring viewport state
- Built-in presets demonstrate the full range of the engine immediately on first launch

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 06-interface-and-intelligence*
*Context gathered: 2026-03-16*
