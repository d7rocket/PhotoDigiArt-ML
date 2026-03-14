---
phase: 3
slug: discovery-and-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-timeout |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/ -x --timeout=30` |
| **Full suite command** | `pytest tests/ --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `pytest tests/ --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | EXTRACT-04 | unit | `pytest tests/test_clip_extractor.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | EXTRACT-04 | unit | `pytest tests/test_clip_extractor.py -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | COLL-01, COLL-02 | unit | `pytest tests/test_collection_analyzer.py -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | COLL-03 | unit | `pytest tests/test_collection_analyzer.py::test_force_attractors -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | RENDER-07 | unit | `pytest tests/test_animation.py -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | CTRL-02 | unit | `pytest tests/test_mapping.py -x` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 2 | CTRL-07 | unit | `pytest tests/test_preset_interpolation.py -x` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 2 | DISC-01 | unit | `pytest tests/test_discovery.py -x` | ❌ W0 | ⬜ pending |
| 03-06-01 | 06 | 3 | DISC-02, DISC-03 | unit | `pytest tests/test_enrichment.py -x` | ❌ W0 | ⬜ pending |
| 03-06-02 | 06 | 3 | DISC-04 | unit | `pytest tests/test_enrichment.py::test_offline_fallback -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_clip_extractor.py` — stubs for EXTRACT-04 (mock ONNX session, verify ExtractionResult structure)
- [ ] `tests/test_collection_analyzer.py` — stubs for COLL-01, COLL-02, COLL-03
- [ ] `tests/test_animation.py` — stubs for RENDER-07
- [ ] `tests/test_mapping.py` — stubs for CTRL-02
- [ ] `tests/test_preset_interpolation.py` — stubs for CTRL-07
- [ ] `tests/test_discovery.py` — stubs for DISC-01
- [ ] `tests/test_enrichment.py` — stubs for DISC-02, DISC-03, DISC-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D embedding cloud renders correctly in viewport | COLL-02 | GPU rendering + visual positioning | Load 10+ photos, run extraction, verify cloud shows clusters in viewport |
| Node-wire editor drag-and-connect UX | CTRL-02 | Interactive GUI behavior | Open mapping editor, drag wire from feature to param, verify connection |
| Discovery history strip navigation | DISC-01 | Visual snapshot comparison | Run 5+ proposals, click history thumbnails, verify state restoration |
| Claude API enrichment produces richer tags | DISC-02 | Requires API key + network | Enable enrichment, run extraction, compare tags with/without API |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
