# Phase 6: Interface and Intelligence - Research

**Researched:** 2026-03-16
**Domain:** PySide6 UI restructuring, qt-material theming, Claude API structured outputs, preset visualization
**Confidence:** HIGH

## Summary

Phase 6 restructures the existing right sidebar from a vertical panel stack into a tabbed layout (Create/Explore/Export), applies qt-material dark theming with custom QSS overrides, replaces the preset list with a visual thumbnail grid, and adds Claude creative direction features (photo analysis, parameter suggestion, iterative refinement).

The codebase is well-positioned for this work. The existing `_Section` collapsible widget, slider factory pattern, `CrossfadeEngine`, `EnrichmentService` with background worker, and `ParameterChangeCommand` undo system all provide reusable foundations. The Anthropic Python SDK (v0.84.0, already installed) supports `messages.parse()` with Pydantic models for structured outputs -- no beta headers needed. qt-material v2.17 is available but not yet installed; it provides `apply_stylesheet()` with an `extra` parameter for customization, and custom QSS can be appended via `app.setStyleSheet(stylesheet + custom_css)`.

**Primary recommendation:** Structure the work in 4 plans: (1) qt-material theming + tabbed layout restructure, (2) Create tab with reorganized sliders + toolbar strip, (3) Preset grid with gradient thumbnails, (4) Claude AI panel with structured outputs and refinement loop.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Tabbed groups: 3 tabs at top of right sidebar -- **Create**, **Explore**, **Export**
- **Create tab**: Rendering section (Point Size, Opacity) + Simulation section (Cohesion, Home Strength, Flow Intensity, Breathing Rate) + PostFX collapsed + Advanced collapsed
- **Explore tab**: Claude AI panel + Presets (grid with crossfade) + Discovery (dimensional mapper)
- **Export tab**: Library (loaded photos, thumbnails) + Export (PNG, resolution)
- 6 essential sliders visible by default: 4 simulation + 2 rendering. Depth Exaggeration moves to Advanced
- Simulate/Pause + Reset Camera as persistent toolbar strip above the tab bar
- Card-based Claude suggestion display with artistic rationale + parameter chips + Apply button
- Apply crossfades parameters via existing CrossfadeEngine
- Manual trigger only: "Analyze with Claude" button. No auto-analyze on photo load
- Refinement via direction buttons after applying: "More Fluid" / "More Structured" / "More Vibrant" / "More Subtle" + "Start Over" / "Keep This"
- All API calls async via background worker -- viewport never freezes
- API key via Settings dialog (Menu > Settings). Stored in local config file
- Generated gradient icons from preset's color palette (not viewport screenshots)
- Grid display: 2-3 column grid of thumbnail cards. Click to apply with crossfade
- Ship with 5-6 built-in presets: Ethereal, Liquid, Breathing, Turbulent, Dense, Calm
- qt-material dark theme as foundation + custom QSS overrides
- Keep electric blue accent (#0078FF)
- Keep Segoe UI font
- Dark panels frame white viewport

### Claude's Discretion
- Exact qt-material XML configuration and override specifics
- Gradient icon generation algorithm for preset thumbnails
- Direction button labels and exact phrasing (the 4 refinement directions)
- Claude prompt engineering for photo analysis and parameter suggestion
- Pydantic model structure for structured Claude outputs
- Loading spinner design during API calls
- Settings dialog layout and field organization
- Tab bar visual style (underline, pill, or standard qt-material tabs)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Clean, logical panel layout with clear visual hierarchy | Tabbed QTabWidget layout with _Section collapsible groups; qt-material provides consistent styling foundation |
| UI-02 | Tiered parameter controls -- 6 essential sliders visible, advanced collapsed | Existing SimulationPanel._add_slider pattern + _Section widget; reorganize into Create tab sections |
| UI-03 | qt-material theming for polished, modern appearance | qt-material v2.17 apply_stylesheet() + custom QSS override append pattern |
| UI-04 | Parameter presets with visual thumbnails for quick selection | Gradient icon generation from preset color palette; QGridLayout with custom PresetCard widget |
| CLAU-01 | Claude analyzes loaded photo(s) and suggests parameter sets | Extend EnrichmentService with suggest_parameters() using messages.parse() + Pydantic model |
| CLAU-02 | Structured outputs via Pydantic ensure Claude returns valid, bounded parameters | anthropic v0.84.0 messages.parse() with output_format=PydanticModel; Pydantic validators for bounds |
| CLAU-03 | Suggested parameters crossfade into viewport smoothly on apply | CrossfadeEngine from Phase 5 + ParameterChangeCommand for undo integration |
| CLAU-04 | Iterative "more/less like this" refinement loop with Claude | Direction buttons send current params + direction string to Claude; same background worker pattern |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | (existing) | GUI framework | Already established; all panels built on it |
| qt-material | 2.17 | Material dark theme | Decision locked; `apply_stylesheet()` with dark_blue.xml closest to #0078FF accent |
| anthropic | 0.84.0 | Claude API SDK | Already installed; has `messages.parse()` for structured outputs |
| pydantic | 2.12.5 | Structured output models | Already installed (anthropic dependency); validators for parameter bounds |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | (existing) | Image loading for Claude analysis | Already used throughout; base64 encoding in enrichment.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| qt-material | Keep existing custom QSS | qt-material is a locked decision; provides consistent Material baseline |
| messages.parse() | Manual JSON parsing | parse() gives type-safe Pydantic output with automatic validation |

**Installation:**
```bash
pip install qt-material==2.17
```

## Architecture Patterns

### Recommended Project Structure
```
apollo7/gui/
  main_window.py          # Restructure: toolbar strip + QTabWidget replacing panel stack
  theme.py                # Replace: qt-material setup + custom QSS override string
  panels/
    controls_panel.py     # Refactor: extract rendering sliders into Create tab sections
    simulation_panel.py   # Refactor: remove Simulate/Pause (moves to toolbar), keep slider sections
    postfx_panel.py       # Minor: becomes collapsed _Section in Create tab
    preset_panel.py       # Major rewrite: grid layout with gradient thumbnails
    discovery_panel.py    # Minor: moves into Explore tab as collapsed _Section
    library_panel.py      # Minor: moves into Export tab
    export_panel.py       # Minor: moves into Export tab
    claude_panel.py       # NEW: AI suggestion card, direction buttons, state machine
  widgets/
    preset_card.py        # NEW: gradient thumbnail + name widget for preset grid
    settings_dialog.py    # NEW: API key modal dialog
    toolbar_strip.py      # NEW: Simulate/Pause + Reset Camera persistent strip
apollo7/api/
  enrichment.py           # Extend: add suggest_parameters() and refine_parameters()
  models.py               # NEW: Pydantic models for Claude structured outputs
```

### Pattern 1: qt-material + Custom QSS Override
**What:** Apply qt-material base theme, then append project-specific QSS overrides
**When to use:** Theme initialization in main window startup
**Example:**
```python
# Source: qt-material docs + WebSearch verified pattern
from qt_material import apply_stylesheet

def setup_theme(app):
    # Apply qt-material dark blue base
    apply_stylesheet(app, theme='dark_blue.xml')

    # Append custom overrides for Apollo 7-specific widgets
    existing = app.styleSheet()
    custom_qss = """
    /* Apollo 7 overrides */
    QTabBar::tab:selected {
        border-bottom: 2px solid #0078FF;
    }
    QPushButton#btn-simulate {
        background-color: #0078FF;
        font-weight: 600;
    }
    /* ... more overrides ... */
    """
    app.setStyleSheet(existing + custom_qss)
```

### Pattern 2: Structured Claude Outputs with Pydantic
**What:** Use `messages.parse()` to get type-safe, bounded parameter suggestions
**When to use:** Claude photo analysis and refinement requests
**Example:**
```python
# Source: Anthropic docs (platform.claude.com/docs/en/build-with-claude/structured-outputs)
from pydantic import BaseModel, Field
from anthropic import Anthropic

class SculptureParams(BaseModel):
    """Claude-suggested sculpture parameters."""
    rationale: str = Field(description="2-3 sentence artistic rationale")
    solver_iterations: int = Field(ge=1, le=6, description="Cohesion 1-6")
    home_strength: float = Field(ge=0.1, le=20.0)
    noise_amplitude: float = Field(ge=0.0, le=5.0, description="Flow intensity")
    breathing_rate: float = Field(ge=0.05, le=0.5)
    point_size: float = Field(ge=0.5, le=10.0)
    opacity: float = Field(ge=0.0, le=1.0)

client = Anthropic(api_key=key)
response = client.messages.parse(
    model="claude-sonnet-4-20250514",
    max_tokens=512,
    messages=[{"role": "user", "content": [...]}],
    output_format=SculptureParams,
)
params = response.parsed_output  # Type-safe SculptureParams
```

### Pattern 3: Claude Panel State Machine
**What:** Finite state machine for Claude interaction flow
**When to use:** Managing Claude panel UI states
**Example:**
```python
# States: idle -> loading -> suggestion -> applied -> loading (refinement)
#                        -> error
# Transitions defined in CONTEXT.md state diagram
from enum import Enum, auto

class ClaudeState(Enum):
    IDLE = auto()       # Show "Analyze with Claude" button
    LOADING = auto()    # Show spinner, disable button
    SUGGESTION = auto() # Show card with rationale + chips + Apply
    APPLIED = auto()    # Show direction buttons + Keep/Start Over
    ERROR = auto()      # Show error message + Retry
```

### Pattern 4: Gradient Icon Generation for Preset Thumbnails
**What:** Generate 80x60px gradient images from preset color palette and key params
**When to use:** Preset card thumbnails in grid
**Example:**
```python
from PySide6.QtGui import QLinearGradient, QPixmap, QPainter, QColor

def generate_preset_icon(preset_data: dict, width=80, height=60) -> QPixmap:
    """Generate gradient icon from preset's simulation parameters."""
    sim = preset_data.get("sim_params", {})
    # Map key params to visual properties
    intensity = sim.get("noise_amplitude", 1.0) / 5.0  # normalize
    cohesion = sim.get("solver_iterations", 2) / 6.0

    pixmap = QPixmap(width, height)
    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, width, height)
    # Use accent hue shifted by params
    gradient.setColorAt(0, QColor.fromHsvF(0.6 * cohesion, 0.7, 0.4 + 0.3 * intensity))
    gradient.setColorAt(1, QColor.fromHsvF(0.6, 0.5 + 0.3 * intensity, 0.2 + 0.2 * cohesion))
    painter.fillRect(0, 0, width, height, gradient)
    painter.end()
    return pixmap
```

### Anti-Patterns to Avoid
- **Blocking the main thread with Claude API calls:** Always use QRunnable + QThreadPool (existing EnrichmentWorker pattern). Never call `client.messages.parse()` synchronously in the GUI thread.
- **Hardcoding parameter ranges in Claude models:** Import bounds from `config/settings.py` constants. The Pydantic model should reference the same ranges.
- **Replacing theme.py entirely without fallback:** qt-material may not cover all existing widget IDs. Keep the custom QSS overrides for Apollo 7-specific objectNames like `#btn-simulate`, `#fps-counter`, `#panel-title`.
- **Breaking existing signal/slot wiring during restructure:** The main_window.py `_connect_signals()` method wires ~30 connections. Moving panels into tabs must preserve all connections.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Material dark theme | Custom QSS from scratch | qt-material `apply_stylesheet()` | Covers 40+ widget types consistently; existing theme.py is 440 lines of manual QSS |
| Claude output parsing | Manual JSON parsing + validation | `messages.parse()` + Pydantic model | Automatic schema enforcement, type safety, Pydantic validators for bounds |
| Parameter interpolation | New lerp function | Existing `lerp_presets()` from presets.py | Already handles numeric, list, and non-numeric types correctly |
| Smooth crossfade on apply | Custom animation timer | Existing `CrossfadeEngine` | Cubic ease-out, 400ms, already tested and integrated |
| Undo for param changes | Custom undo tracking | Existing `ParameterChangeCommand` | Merge support for rapid changes, already on QUndoStack |
| Background API calls | Raw threading | Existing `EnrichmentWorker` QRunnable pattern | Signal-based result delivery, auto-delete, thread pool managed |

**Key insight:** Phase 5 and prior phases built precisely the infrastructure this phase needs -- CrossfadeEngine for smooth parameter application, EnrichmentService/Worker for async Claude calls, ParameterChangeCommand for undo, _Section for collapsible groups. The risk is in restructuring main_window.py (700+ lines) without breaking existing wiring, not in building new capabilities.

## Common Pitfalls

### Pitfall 1: qt-material Overriding Custom Widget Styles
**What goes wrong:** qt-material applies blanket styles that override Apollo 7-specific objectName selectors (`#btn-simulate`, `#fps-counter`, etc.)
**Why it happens:** qt-material uses high-specificity QSS selectors that win over simple objectName selectors
**How to avoid:** Apply qt-material first, then append custom QSS via `app.setStyleSheet(existing + custom)`. Custom QSS appended last has higher cascade priority. Test that all existing objectName-based styles still render correctly.
**Warning signs:** Buttons losing accent color, FPS counter losing monospace font, panel titles losing semibold weight.

### Pitfall 2: Signal Disconnection During Tab Restructure
**What goes wrong:** Moving panels from vertical stack into QTabWidget tabs breaks signal/slot connections established in `_connect_signals()`
**Why it happens:** Panel references are set up in `__init__` before layout. If panels are recreated instead of reparented, connections to old objects become dead.
**How to avoid:** Create panels once (as now), then add them to tab widget layouts. Do NOT create new panel instances. Verify all ~30 signal connections in `_connect_signals()` still work after restructure.
**Warning signs:** Sliders move but viewport doesn't update, Simulate button doesn't start animation, preset apply does nothing.

### Pitfall 3: Claude API Key Storage Insecurity
**What goes wrong:** API key stored in plain text in an easily discoverable location
**Why it happens:** Using a simple JSON config file without considering file permissions
**How to avoid:** Store in `~/.apollo7/config.json` with restrictive file permissions (0o600 on Unix). On Windows, user home directory provides reasonable isolation. Never log the API key.
**Warning signs:** Key visible in logs, config file world-readable.

### Pitfall 4: Pydantic Validation Rejecting Valid Claude Responses
**What goes wrong:** Claude returns parameters slightly outside defined bounds, Pydantic raises ValidationError, user sees error
**Why it happens:** Claude may not perfectly respect numeric constraints even with structured outputs
**How to avoid:** Use `messages.parse()` which enforces the schema server-side. Additionally, add a clamping step after parsing as defense-in-depth: `value = max(min_val, min(max_val, value))`.
**Warning signs:** "Claude returned an unexpected response" errors despite successful API calls.

### Pitfall 5: Built-in Presets Using Legacy Parameter Names
**What goes wrong:** Existing `_BUILTIN_PRESETS` in presets.py use v1.0 parameter names (noise_frequency, noise_amplitude, turbulence_scale, etc.) that don't match the v2.0 PBF slider parameter names
**Why it happens:** presets.py was written in Phase 1/2 and never updated for Phase 4's PBF parameter rename
**How to avoid:** Create new built-in presets (Ethereal, Liquid, Breathing, Turbulent, Dense, Calm) using current PBF parameter names: `solver_iterations`, `home_strength`, `noise_amplitude`, `breathing_rate`, `noise_frequency`, `vorticity_epsilon`, `xsph_c`, `damping`, `breathing_amplitude`. Also update rendering params: `point_size`, `opacity`.
**Warning signs:** Applying a built-in preset changes nothing because parameter names don't match.

### Pitfall 6: Tab Scroll Position Not Preserved
**What goes wrong:** Switching tabs resets scroll position, user loses their place in long Create tab
**Why it happens:** QTabWidget hides/shows widgets; if using a single QScrollArea, it shares scroll state
**How to avoid:** Each tab should have its own QScrollArea wrapping its content. The tab widget holds three separate scroll areas, not three widgets inside one scroll area.
**Warning signs:** Scrolling down in Create tab, switching to Explore and back, finding Create tab scrolled to top.

## Code Examples

### Existing Assets to Reuse

#### _Section Collapsible Widget (from preset_panel.py)
```python
# Source: apollo7/gui/panels/preset_panel.py line 26-71
class _Section(QtWidgets.QWidget):
    """A collapsible section with styled header and content area."""
    # Extract this into apollo7/gui/widgets/section.py for shared use
    # Used in: Create tab sections, Explore tab sections, Export tab sections
```

#### Slider Factory (from simulation_panel.py)
```python
# Source: apollo7/gui/panels/simulation_panel.py line 184-218
# _add_slider(layout, spec) where spec = (param_name, label, min, max, default, fmt, is_integer)
# Reuse for all sliders in Create tab -- both rendering and simulation
```

#### EnrichmentWorker Background Pattern (from enrichment.py)
```python
# Source: apollo7/api/enrichment.py line 226-274
# QRunnable with signals: enrichment_ready, suggestions_ready, error
# Extend with new signal: params_suggested = Signal(object)  # SculptureParams
```

### New: Claude Parameter Suggestion Service
```python
# Extend enrichment.py
from apollo7.api.models import SculptureParams

def suggest_parameters(
    self, image_path: str, current_params: dict | None = None,
    direction: str | None = None,
) -> SculptureParams | None:
    """Analyze photo and suggest sculpture parameters.

    Args:
        image_path: Path to photo file.
        current_params: Current parameters (for refinement).
        direction: Refinement direction ("More Fluid", etc.) or None for initial.
    """
    client = self._get_client()
    if client is None:
        return None

    # Build message with image + context
    content = [
        {"type": "image", "source": {"type": "base64", ...}},
        {"type": "text", "text": prompt},
    ]

    response = client.messages.parse(
        model=self._model,
        max_tokens=512,
        messages=[{"role": "user", "content": content}],
        output_format=SculptureParams,
    )
    return response.parsed_output
```

### New: Toolbar Strip Widget
```python
# apollo7/gui/widgets/toolbar_strip.py
class ToolbarStrip(QtWidgets.QWidget):
    """Persistent toolbar with Simulate/Pause, Reset Camera, FPS counter."""
    simulate_clicked = Signal()
    pause_toggled = Signal(bool)
    reset_camera_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        # [Simulate/Pause] [Reset Camera]  ...stretch...  [FPS]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON parsing for Claude | `messages.parse()` with Pydantic | Nov 2025 GA | Eliminates parsing errors, retry logic |
| Beta header for structured outputs | No header needed (GA) | Late 2025 | Simpler integration, production-ready |
| Raw QSS theme (440 lines) | qt-material base + targeted overrides | This phase | Consistent Material styling with less custom code |
| Vertical panel stack | Tabbed layout (Create/Explore/Export) | This phase | Better organization, workflow-oriented grouping |
| Built-in presets with v1.0 params | New presets with PBF v2.0 params | This phase | Presets actually work with current simulation engine |

**Deprecated/outdated:**
- `_BUILTIN_PRESETS` in presets.py: Uses v1.0 parameter names that don't map to current PBF sliders. Must be replaced with new presets using v2.0 parameter names.
- Existing `theme.py` `load_theme_qss()`: Will be replaced by qt-material setup, but the color constants and objectName selectors should be preserved in the override QSS.

## Open Questions

1. **qt-material dark_blue.xml accent color match**
   - What we know: qt-material ships dark_blue.xml, accent is likely close to #0078FF but exact hex unknown until installed
   - What's unclear: Whether dark_blue.xml uses exactly #0078FF or a different blue
   - Recommendation: Install qt-material, inspect the XML. If accent differs, use the `extra` parameter or custom theme XML to set `primaryColor: #0078FF`

2. **qt-material environment variable color customization**
   - What we know: qt-material sets `QTMATERIAL_PRIMARYCOLOR` etc. internally; custom themes can override
   - What's unclear: Exact mechanism for setting custom primary color without creating a full XML theme file
   - Recommendation: Inspect `apply_stylesheet` source after install; worst case, append QSS overrides to replace accent color references

3. **Slider filled track with qt-material**
   - What we know: Current theme.py uses `QSlider::sub-page` for filled track. qt-material may style this differently
   - What's unclear: Whether qt-material's slider styling matches the design spec (accent fill, round handle)
   - Recommendation: Test after applying qt-material; add override QSS for slider if needed

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` or implicit pytest discovery |
| Quick run command | `pytest tests/ -x --timeout=30` |
| Full suite command | `pytest tests/ --timeout=60` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Tabbed panel layout creates without error | unit | `pytest tests/test_tabbed_layout.py -x` | No -- Wave 0 |
| UI-02 | 6 essential sliders visible, advanced collapsed | unit | `pytest tests/test_tabbed_layout.py::test_essential_sliders -x` | No -- Wave 0 |
| UI-03 | qt-material theme applies without crash | unit | `pytest tests/test_theme.py -x` | No -- Wave 0 |
| UI-04 | Preset grid displays thumbnails, click applies | unit | `pytest tests/test_preset_grid.py -x` | No -- Wave 0 |
| CLAU-01 | Claude suggests valid parameters from photo | unit | `pytest tests/test_claude_suggestions.py::test_suggest_params -x` | No -- Wave 0 |
| CLAU-02 | Pydantic model validates and clamps params | unit | `pytest tests/test_claude_suggestions.py::test_pydantic_validation -x` | No -- Wave 0 |
| CLAU-03 | Apply crossfades params via CrossfadeEngine | unit | `pytest tests/test_claude_suggestions.py::test_apply_crossfade -x` | No -- Wave 0 |
| CLAU-04 | Refinement sends direction + current params | unit | `pytest tests/test_claude_suggestions.py::test_refinement -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_claude_suggestions.py tests/test_preset_grid.py -x --timeout=30`
- **Per wave merge:** `pytest tests/ --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tabbed_layout.py` -- covers UI-01, UI-02 (widget creation, slider counts)
- [ ] `tests/test_theme.py` -- covers UI-03 (qt-material applies without crash)
- [ ] `tests/test_preset_grid.py` -- covers UI-04 (gradient icon generation, grid layout)
- [ ] `tests/test_claude_suggestions.py` -- covers CLAU-01 through CLAU-04 (mocked API, Pydantic model, refinement)
- [ ] Framework install: `pip install qt-material==2.17` -- required before any tests

## Sources

### Primary (HIGH confidence)
- Anthropic official docs (platform.claude.com/docs/en/build-with-claude/structured-outputs) -- messages.parse(), output_format, no beta header needed, supported models
- Existing codebase: apollo7/api/enrichment.py -- EnrichmentService/Worker pattern with QRunnable + signals
- Existing codebase: apollo7/gui/panels/preset_panel.py -- _Section widget, PresetPanel structure
- Existing codebase: apollo7/gui/panels/simulation_panel.py -- Slider factory, essential/advanced grouping
- Existing codebase: apollo7/config/settings.py -- All parameter ranges and defaults
- Existing codebase: apollo7/gui/theme.py -- Current QSS, color constants, objectName selectors

### Secondary (MEDIUM confidence)
- [qt-material PyPI](https://pypi.org/project/qt-material/) -- v2.17 available, pip installable
- [qt-material GitHub](https://github.com/dunderlab/qt-material) -- apply_stylesheet(), extra parameter, dark themes
- [qt-material docs](https://qt-material.readthedocs.io/) -- Basic setup, theme listing, QSS customization via append

### Tertiary (LOW confidence)
- qt-material custom color mechanism: exact process for overriding primaryColor to #0078FF needs verification after install. The `extra` dict format for color overrides was not fully documented in sources found.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed except qt-material (available, verified)
- Architecture: HIGH - restructuring existing code with well-understood PySide6 patterns
- Claude integration: HIGH - Anthropic SDK v0.84.0 has messages.parse() confirmed via code inspection
- qt-material customization: MEDIUM - basic apply works, but exact color override mechanism needs post-install verification
- Pitfalls: HIGH - identified from direct codebase analysis (parameter name mismatch, signal wiring, etc.)

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable ecosystem, no fast-moving dependencies)
