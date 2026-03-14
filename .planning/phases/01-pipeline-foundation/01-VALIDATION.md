---
phase: 1
slug: pipeline-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `pytest tests/ -v --timeout=120` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `pytest tests/ -v --timeout=120`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | | | | | |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (temp dirs, sample images)
- [ ] `tests/test_ingestion.py` — stubs for INGEST-01, INGEST-02, INGEST-03
- [ ] `tests/test_extraction.py` — stubs for EXTRACT-01, EXTRACT-02, EXTRACT-03
- [ ] `tests/test_rendering.py` — stubs for RENDER-01, RENDER-02, RENDER-03
- [ ] `tests/test_app.py` — stubs for APP-01, APP-02, APP-03, APP-04
- [ ] `pytest` + `pytest-timeout` — install if not present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D viewport orbit/zoom/pan at 30+ FPS | RENDER-02 | Requires GPU + visual inspection | Load sample photo, orbit camera, check FPS counter |
| GUI layout matches viewport-dominant design | APP-01 | Visual/aesthetic judgment | Launch app, verify 70%+ viewport, dark theme, custom widgets |
| Progressive point cloud build during extraction | RENDER-01 | Visual + timing behavior | Load folder of photos, watch viewport update progressively |
| Self-illuminated soft particles aesthetic | RENDER-03 | Visual quality judgment | Load high-contrast photo, verify Gaussian glow on dark gradient bg |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
