---
phase: 05-visual-quality
plan: 03
subsystem: rendering
tags: [pygfx, bloom, background, blending, visual-tuning]

# Dependency graph
requires:
  - phase: 05-visual-quality
    provides: GPU buffer sharing with zero-copy rendering (Plan 05-01)
provides:
  - Warm off-white gallery background (#F8F6F3)
  - Retuned bloom (12x stronger, 3x wider filter, Karis averaging)
  - Luminous blend alpha (0.45) for particle cluster overlap
  - Un-skipped visual quality tests (background, alpha, bloom)
affects: [05-04-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [Karis average for firefly suppression in bloom, gallery-paper background aesthetic]

key-files:
  created: []
  modified:
    - apollo7/config/settings.py
    - apollo7/postfx/bloom.py
    - apollo7/gui/widgets/viewport_widget.py
    - tests/test_visual_quality.py

key-decisions:
  - "Warm off-white #F8F6F3/#F5F3F0 (not pure white) for gallery art paper aesthetic"
  - "Bloom strength 0.5 (12x from 0.04) with filter_radius 0.015 for colored halos on white"
  - "Blend alpha 0.45 for luminous cluster overlap while keeping individual particles distinct"
  - "Karis averaging enabled to suppress firefly artifacts from bright single pixels"

patterns-established:
  - "Gallery aesthetic: warm off-white background with colored bloom halos, not dark theme"
  - "Luminous overlap: low alpha + Gaussian blob + bloom creates dense-cluster brightening"

requirements-completed: [REND-01, REND-02, REND-03, REND-04]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 5 Plan 03: White Background Tuning Summary

**Gallery-quality warm off-white background with 12x bloom increase, 3x wider filter radius, Karis averaging, and 0.45 blend alpha for luminous particle cluster overlap**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T16:08:54Z
- **Completed:** 2026-03-15T16:12:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Transformed viewport from dark prototype (#1a1a1a) to gallery-quality warm off-white (#F8F6F3) background
- Retuned bloom for white background: strength 0.04->0.5, filter_radius 0.005->0.015, Karis averaging enabled
- Lowered blend alpha 0.7->0.45 for luminous overlap effect in dense particle clusters
- Un-skipped and enhanced 3 visual quality tests verifying background, alpha, and bloom tuning

## Task Commits

Each task was committed atomically:

1. **Task 1: White background and bloom defaults in settings** - `df207aa` (feat)
2. **Task 2: Luminous blend alpha and un-skip visual quality tests** - `07fe9b8` (feat)

## Files Created/Modified
- `apollo7/config/settings.py` - Warm off-white BG_COLOR defaults, BLOOM_STRENGTH_DEFAULT 0.5, new BLOOM_FILTER_RADIUS 0.015
- `apollo7/postfx/bloom.py` - Imports BLOOM_FILTER_RADIUS, uses wider filter radius, enables Karis averaging
- `apollo7/gui/widgets/viewport_widget.py` - _BLEND_ALPHA lowered to 0.45 for luminous cluster overlap
- `tests/test_visual_quality.py` - Un-skipped and enhanced test_white_background, test_blend_alpha_configured, test_bloom_tuned_for_white

## Decisions Made
- Warm off-white #F8F6F3 (not pure white) for gallery art paper aesthetic per user preference
- Bloom strength increased 12x (0.04 -> 0.5) with 3x wider filter radius (0.005 -> 0.015) for colored halos
- Karis averaging enabled to prevent firefly artifacts from bright single-pixel particles
- Blend alpha 0.45 chosen for luminous overlap -- saturated colors preserved in dense clusters, individual particles distinct at edges

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in test_discovery.py, test_flow_field.py, test_sph.py, test_sim_lifecycle.py (unrelated to this plan, documented in prior summaries)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Gallery aesthetic foundation complete for Plan 05-04 (final visual polish)
- Background, bloom, and alpha all tuned -- ready for visual verification
- Soft Gaussian blob material preserved (REND-01, no changes needed)

---
*Phase: 05-visual-quality*
*Completed: 2026-03-15*
