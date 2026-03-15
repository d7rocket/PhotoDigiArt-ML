---
phase: 4
slug: stable-physics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | None (default pytest discovery) |
| **Quick run command** | `python -m pytest tests/test_pbf_solver.py tests/test_simulation_params.py tests/test_simulation_engine.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_pbf_solver.py tests/test_simulation_params.py tests/test_simulation_engine.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | PHYS-01 | integration | `python -m pytest tests/test_pbf_solver.py::test_home_attraction_holds_form -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | PHYS-02 | integration | `python -m pytest tests/test_pbf_solver.py::test_stability_1000_frames -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | PHYS-03 | unit | `python -m pytest tests/test_pbf_solver.py::test_gpu_spatial_hash_correctness -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | PHYS-04 | unit | `python -m pytest tests/test_pbf_solver.py::test_no_nan_inf_after_1000_frames -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | PHYS-05 | unit | `python -m pytest tests/test_pbf_solver.py::test_cfl_timestep_adapts -x` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | PHYS-06 | unit | `python -m pytest tests/test_pbf_solver.py::test_curl_noise_produces_flow -x` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 2 | PHYS-07 | integration | `python -m pytest tests/test_pbf_solver.py::test_vorticity_confinement_effect -x` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 3 | PHYS-08 | unit | `python -m pytest tests/test_simulation_params.py::test_breathing_modulation -x` | ❌ W0 | ⬜ pending |
| 04-05-02 | 05 | 3 | PHYS-09 | integration | `python -m pytest tests/test_pbf_solver.py::test_iteration_count_affects_density -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pbf_solver.py` — stubs for PHYS-01 through PHYS-09 (new file, all PBF-specific tests)
- [ ] Update `tests/test_simulation_params.py` — add tests for new PBF params (home_strength, breathing_rate, solver_iterations, kernel_radius)
- [ ] Update `tests/test_simulation_engine.py` — update to reflect PBF pipeline (remove SPH-specific tests, add PBF lifecycle tests)

*Existing test infrastructure covers basic engine lifecycle, param packing, and buffer management. New tests needed for PBF-specific behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ocean-current visual aesthetic | PHYS-06, PHYS-07 | Subjective visual quality | Load a photo, observe particle motion for 30s. Should exhibit slow sweeping flows with subtle eddies. |
| Breathing feels organic | PHYS-08 | Perceptual timing judgment | Observe sculpture for 15s at rest. Should see ~4-6s inhale/exhale cycle that feels calm and meditative. |
| Solver iterations creative spectrum | PHYS-09 | Subjective visual difference | Slide "Cohesion" from min to max. Each position should produce a visually distinct character. |
| 60fps at 500K+ particles | PHYS-02 | Hardware-specific performance | Load 500K+ particle scene on RX 9060 XT, verify sustained 60fps via viewport FPS counter. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
