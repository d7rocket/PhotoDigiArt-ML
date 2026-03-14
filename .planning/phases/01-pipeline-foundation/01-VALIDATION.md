---
phase: 1
slug: pipeline-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none -- Wave 0 installs |
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
| 01-01-T1 | 01-01 | 1 | APP-02 | smoke | `pip install -e ".[dev]" && pytest tests/test_gpu_providers.py -x -q --timeout=30` | tests/test_gpu_providers.py | pending |
| 01-01-T2 | 01-01 | 1 | APP-01, RENDER-02, RENDER-03 | integration | `python -c "from apollo7.gui.widgets.viewport_widget import BLEND_MODE_AVAILABLE; print(BLEND_MODE_AVAILABLE)" && pytest tests/ -x -q --timeout=30` | apollo7/gui/widgets/viewport_widget.py | pending |
| 01-01-T3 | 01-01 | 1 | APP-01, RENDER-02, RENDER-03 | manual | Manual: launch app, verify theme + viewport + blending | N/A | pending |
| 01-02-T1 | 01-02 | 2 | INGEST-01, INGEST-02 | unit | `pytest tests/test_loader.py tests/test_thumbnailer.py -x -v --timeout=30` | tests/test_loader.py, tests/test_thumbnailer.py | pending |
| 01-02-T2 | 01-02 | 2 | INGEST-03 | integration | `pytest tests/ -x -q --timeout=30` | apollo7/gui/panels/library_panel.py | pending |
| 01-03-T1 | 01-03 | 2 | EXTRACT-01, EXTRACT-02 | unit | `pytest tests/test_color_extractor.py tests/test_edge_extractor.py -x -v --timeout=30` | tests/test_color_extractor.py, tests/test_edge_extractor.py | pending |
| 01-03-T2 | 01-03 | 2 | EXTRACT-01, EXTRACT-02 | integration | `pytest tests/ -x -q --timeout=30` | apollo7/gui/panels/feature_strip.py | pending |
| 01-04-T1 | 01-04 | 3 | EXTRACT-03, RENDER-01 | unit | `pytest tests/test_depth_extractor.py tests/test_pointcloud_generator.py -x -v --timeout=30` | tests/test_depth_extractor.py, tests/test_pointcloud_generator.py | pending |
| 01-04-T2 | 01-04 | 3 | EXTRACT-03 | integration | `pytest tests/ -x -q --timeout=30` | apollo7/gui/panels/feature_strip.py | pending |
| 01-05-T1 | 01-05 | 4 | APP-03, APP-04, RENDER-03 | integration | `pytest tests/ -x -q --timeout=30` | apollo7/workers/extraction_worker.py | pending |
| 01-05-T2 | 01-05 | 4 | APP-03, RENDER-03 | manual | Manual: full end-to-end pipeline verification | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` -- shared fixtures (temp dirs, sample images)
- [ ] `tests/test_ingestion.py` -- stubs for INGEST-01, INGEST-02, INGEST-03
- [ ] `tests/test_extraction.py` -- stubs for EXTRACT-01, EXTRACT-02, EXTRACT-03
- [ ] `tests/test_rendering.py` -- stubs for RENDER-01, RENDER-02, RENDER-03
- [ ] `tests/test_app.py` -- stubs for APP-01, APP-02, APP-03, APP-04
- [ ] `pytest` + `pytest-timeout` -- install if not present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D viewport orbit/zoom/pan at 30+ FPS | RENDER-02 | Requires GPU + visual inspection | Load sample photo, orbit camera, check FPS counter |
| GUI layout matches viewport-dominant design | APP-01 | Visual/aesthetic judgment | Launch app, verify 70%+ viewport, dark theme, custom widgets |
| Progressive point cloud build during extraction | RENDER-01 | Visual + timing behavior | Load folder of photos, watch viewport update progressively |
| Self-illuminated soft particles aesthetic | RENDER-03 | Visual quality judgment | Load high-contrast photo, verify Gaussian glow on dark gradient bg |
| Additive/soft blending on overlapping points | RENDER-03 | Visual quality judgment | Zoom into dense area, verify soft overlap (not hard occlusion) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
