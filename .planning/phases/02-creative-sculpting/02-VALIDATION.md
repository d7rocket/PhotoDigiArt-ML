---
phase: 2
slug: creative-sculpting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-timeout |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
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
| 02-01-01 | 01 | 1 | RENDER-04 | unit | `pytest tests/test_simulation_params.py -x` | W0 | pending |
| 02-01-02 | 01 | 1 | SIM-01 | unit | `pytest tests/test_simulation_engine.py -x` | W0 | pending |
| 02-01-03 | 01 | 1 | SIM-02 | unit | `pytest tests/test_sph.py -x` | W0 | pending |
| 02-01-04 | 01 | 1 | SIM-03 | unit | `pytest tests/test_flow_field.py -x` | W0 | pending |
| 02-01-05 | 01 | 1 | RENDER-06 | integration | `pytest tests/test_sim_lifecycle.py -x` | W0 | pending |
| 02-02-01 | 02 | 1 | RENDER-05 | unit | `pytest tests/test_postfx.py -x` | W0 | pending |
| 02-02-02 | 02 | 1 | EXTRACT-05 | manual-only | Manual: load photo, extract, inspect viewer | N/A | pending |
| 02-02-03 | 02 | 1 | SIM-04 | manual-only | Manual: visual inspection of output | N/A | pending |
| 02-03-01 | 03 | 2 | CTRL-01 | unit | `pytest tests/test_sim_panel.py -x` | W0 | pending |
| 02-03-02 | 03 | 2 | CTRL-03 | unit | `pytest tests/test_undo_redo.py -x` | W0 | pending |
| 02-03-03 | 03 | 2 | CTRL-04 | unit | `pytest tests/test_project_save_load.py -x` | W0 | pending |
| 02-03-04 | 03 | 2 | CTRL-05 | unit | `pytest tests/test_export.py -x` | W0 | pending |
| 02-03-05 | 03 | 2 | CTRL-06 | unit | `pytest tests/test_presets.py -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_simulation_params.py` — stubs for RENDER-04 (parameter dataclass, buffer sizing)
- [ ] `tests/test_simulation_engine.py` — stubs for SIM-01 (engine lifecycle, state machine)
- [ ] `tests/test_sph.py` — stubs for SIM-02 (SPH kernel math validation with known inputs, spatial hash cell computation)
- [ ] `tests/test_flow_field.py` — stubs for SIM-03 (shader loading, feature texture references, combined shader build)
- [ ] `tests/test_sim_lifecycle.py` — stubs for RENDER-06 (start/stop/restart sim state machine, param routing)
- [ ] `tests/test_sim_panel.py` — stubs for CTRL-01 (param_changed signal emits valid SimulationParams names, FPSCounter.tick behavior)
- [ ] `tests/test_postfx.py` — stubs for RENDER-05 (bloom pass config, effect pass pipeline)
- [ ] `tests/test_undo_redo.py` — stubs for CTRL-03 (QUndoStack push/undo/redo, merge behavior)
- [ ] `tests/test_project_save_load.py` — stubs for CTRL-04 (roundtrip serialize/deserialize)
- [ ] `tests/test_export.py` — stubs for CTRL-05 (offscreen render produces valid PNG with alpha)
- [ ] `tests/test_presets.py` — stubs for CTRL-06 (save/load/list/categorize presets)

*Note: GPU-dependent tests (simulation, postfx, export) require a wgpu device. Use `pytest.importorskip("wgpu")` and `wgpu.utils.get_default_device()`. Non-GPU tests (undo/redo, project save/load, presets) can run without GPU.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Feature viewer shows all extracted features | EXTRACT-05 | Visual UI inspection required | Load photo, run extraction, verify all features visible in viewer |
| Aesthetic quality of particle output | SIM-04 | Subjective visual quality assessment | Run simulation with various photos, verify gallery-worthy output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
