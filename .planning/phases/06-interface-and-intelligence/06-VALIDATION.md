---
phase: 6
slug: interface-and-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -q --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | UI-01 | visual/manual | manual inspection | N/A | ⬜ pending |
| 06-01-02 | 01 | 1 | UI-03 | import | `python -c "from qt_material import apply_stylesheet"` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | UI-02 | unit | `python -m pytest tests/ -k "slider"` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | UI-04 | unit | `python -m pytest tests/ -k "preset"` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | CLAU-01 | unit | `python -m pytest tests/ -k "claude"` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | CLAU-02 | unit | `python -m pytest tests/ -k "pydantic"` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 2 | CLAU-03 | integration | `python -m pytest tests/ -k "crossfade"` | ❌ W0 | ⬜ pending |
| 06-04-02 | 04 | 2 | CLAU-04 | unit | `python -m pytest tests/ -k "refinement"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ui_layout.py` — stubs for UI-01, UI-02 (tab structure, slider counts)
- [ ] `tests/test_presets.py` — stubs for UI-04 (preset grid, gradient icons, built-in presets)
- [ ] `tests/test_claude_integration.py` — stubs for CLAU-01, CLAU-02, CLAU-03, CLAU-04
- [ ] `pip install qt-material` — qt-material theming dependency

*Existing test infrastructure (pytest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual hierarchy and theming appearance | UI-01, UI-03 | Visual quality requires human judgment | Launch app, verify dark panels frame white viewport, accent blue on interactive elements |
| Preset gradient thumbnails look correct | UI-04 | Generated gradients need visual assessment | Save preset, verify gradient icon represents color palette |
| Claude suggestion card readability | CLAU-01 | Rationale text layout needs visual check | Analyze photo, verify card shows rationale + params + Apply button |
| Crossfade smoothness on Apply | CLAU-03 | Animation quality needs visual check | Apply Claude suggestion, verify smooth ~400ms transition |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
