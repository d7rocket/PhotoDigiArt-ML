---
phase: 5
slug: visual-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-timeout) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x --timeout=30` |
| **Full suite command** | `python -m pytest tests/ --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | REND-05 | unit | `python -m pytest tests/test_visual_quality.py::test_buffer_sharing -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | REND-01 | manual-only | Visual inspection | N/A | ⬜ pending |
| 05-02-02 | 02 | 1 | REND-02 | unit | `python -m pytest tests/test_visual_quality.py::test_white_background -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | REND-03 | unit | `python -m pytest tests/test_visual_quality.py::test_blend_alpha_configured -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 1 | REND-04 | unit | `python -m pytest tests/test_visual_quality.py::test_bloom_tuned_for_white -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | REND-06 | unit | `python -m pytest tests/test_crossfade_engine.py -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 2 | DPTH-01 | unit | `python -m pytest tests/test_depth_extractor.py::test_clahe_enhancement -x` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 2 | DPTH-02 | unit | `python -m pytest tests/test_visual_quality.py::test_saturation_boost -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_visual_quality.py` — stubs for REND-02, REND-03, REND-04, REND-05, DPTH-02
- [ ] `tests/test_crossfade_engine.py` — stubs for REND-06
- [ ] `tests/test_depth_extractor.py::test_clahe_enhancement` — new test in existing file for DPTH-01

*Existing test_postfx.py covers bloom controller basics but needs new tests for retuned parameters.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Particles render as soft round Gaussian blobs | REND-01 | Visual rendering quality cannot be verified without a display | Run app, load photo, verify particles appear as soft round dots with Gaussian falloff |
| Bloom produces colored halos on white background | REND-04 | Visual bloom quality requires human judgment | Run app, enable bloom, verify colored halo spread around dense particle clusters |
| Crossfade feels smooth and polished | REND-06 | Animation feel requires human perception | Drag sliders, verify smooth chase with ease-out deceleration |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
