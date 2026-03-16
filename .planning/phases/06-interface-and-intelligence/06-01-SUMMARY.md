---
phase: 06-interface-and-intelligence
plan: 01
subsystem: ui
tags: [pyside6, qt-material, tabbed-layout, toolbar, collapsible-sections]

# Dependency graph
requires:
  - phase: 05-visual-quality
    provides: rendering pipeline and postfx panels
provides:
  - qt-material dark theme with custom QSS overrides
  - shared collapsible Section widget
  - ToolbarStrip with Simulate/Pause, Reset Camera, FPS counter
  - 3-tab layout (Create/Explore/Export) in right sidebar
  - AI Direction placeholder section for Claude panel
affects: [06-02, 06-03, 06-04]

# Tech tracking
tech-stack:
  added: [qt-material]
  patterns: [tabbed-sidebar, collapsible-sections, toolbar-strip]

key-files:
  created:
    - apollo7/gui/widgets/section.py
    - apollo7/gui/widgets/toolbar_strip.py
  modified:
    - apollo7/gui/theme.py
    - apollo7/gui/main_window.py
    - apollo7/app.py
    - apollo7/gui/panels/preset_panel.py

key-decisions:
  - "qt-material dark_blue.xml base theme with custom QSS overrides layered on top"
  - "Panels reparented into Section widgets inside tabs rather than decomposed into individual widgets"
  - "SimulationPanel buttons hidden (not removed) to preserve backward compatibility"

patterns-established:
  - "Section widget: shared collapsible container for panel grouping in tabs"
  - "ToolbarStrip: persistent controls above tab widget, always visible"
  - "setup_theme(app): qt-material theme applied at app init before MainWindow creation"

requirements-completed: [UI-01, UI-02, UI-03]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 6 Plan 01: Tabbed Layout and Theme Summary

**qt-material dark theme with 3-tab sidebar (Create/Explore/Export), collapsible Section widgets, and persistent ToolbarStrip**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-16T12:58:29Z
- **Completed:** 2026-03-16T13:03:06Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced manual QSS stylesheet with qt-material dark_blue.xml base + custom overrides
- Extracted shared collapsible Section widget from preset_panel._Section
- Created ToolbarStrip with Simulate/Pause toggle, Reset Camera, and FPS counter
- Restructured right sidebar from vertical panel stack to 3-tab QTabWidget layout
- All existing signal/slot connections preserved after restructure

## Task Commits

Each task was committed atomically:

1. **Task 1: Install qt-material, extract Section widget, create ToolbarStrip, rewrite theme.py** - `c76850f` (feat)
2. **Task 2: Restructure main_window.py from vertical stack to tabbed layout** - `2eccce9` (feat)

## Files Created/Modified
- `apollo7/gui/theme.py` - qt-material setup_theme() with custom QSS overrides and exported color constants
- `apollo7/gui/widgets/section.py` - Shared collapsible section with toggle, collapsed property, content_layout
- `apollo7/gui/widgets/toolbar_strip.py` - Persistent toolbar with Simulate/Pause, Reset Camera, FPS counter
- `apollo7/gui/main_window.py` - Tabbed layout with Create/Explore/Export tabs, toolbar strip, Section wrappers
- `apollo7/app.py` - Updated to use setup_theme(app) instead of load_theme_qss()
- `apollo7/gui/panels/preset_panel.py` - Import shared Section widget instead of inline _Section class

## Decisions Made
- Used qt-material dark_blue.xml as base theme rather than pure custom QSS for consistent Material Design styling
- Reparented existing panel widgets directly into Section containers rather than decomposing into individual sliders (preserves all signal connections)
- Hidden SimulationPanel Simulate/Pause/Reset Camera buttons (setVisible(False)) rather than removing them, maintaining backward compatibility
- Added AI Direction placeholder in Explore tab for Claude panel (Plan 04 will populate)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_discovery.py::TestRandomWalkPropose::test_propose_within_constraints (unrelated to our changes, confirmed by running on stashed state)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tabbed layout shell ready for preset grid (Plan 03) and Claude panel (Plan 04)
- AI Direction section placeholder in Explore tab awaiting Claude integration
- ToolbarStrip FPS counter ready to be wired to viewport render loop

---
*Phase: 06-interface-and-intelligence*
*Completed: 2026-03-16*
