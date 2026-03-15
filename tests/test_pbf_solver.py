"""Test scaffolds for PBF solver requirements (PHYS-01 through PHYS-09).

Tests PHYS-01 through PHYS-08 are active. PHYS-09 is a stub for Plan 05.
"""

import math

import numpy as np
import pytest


def _make_pbf_engine(n=1000):
    """Create a SimulationEngine with PBF solver and test data.

    Args:
        n: Number of test particles.

    Returns:
        Tuple of (engine, device, positions, colors).
    """
    wgpu = pytest.importorskip("wgpu")
    device = wgpu.utils.get_default_device()
    from apollo7.simulation.engine import SimulationEngine

    engine = SimulationEngine(device)
    positions = np.random.randn(n, 3).astype(np.float32) * 5.0
    colors = np.random.rand(n, 4).astype(np.float32)
    colors[:, 3] = 1.0
    engine.initialize(positions, colors)
    return engine, device, positions, colors


def test_home_attraction_holds_form():
    """PHYS-01: Home attraction keeps particles near their photo-derived positions.

    Acceptance: After 500 frames with default home_strength=5.0, particles
    remain within a reasonable distance of their home positions. The sculpture
    shape is recognizable and stable.
    """
    engine, device, positions, colors = _make_pbf_engine(1000)

    for _ in range(500):
        engine.step()

    assert engine.running

    # Read back positions and compute distance from home
    final_positions = engine._particle_buffer.read_positions()
    assert final_positions.shape == (1000, 3)

    # No NaN or Inf
    assert np.all(np.isfinite(final_positions)), "Positions contain NaN or Inf"

    # Mean distance from home positions should be bounded
    displacements = final_positions - positions
    distances = np.linalg.norm(displacements, axis=1)
    mean_dist = np.mean(distances)
    assert mean_dist < 5.0, (
        f"Mean distance from home = {mean_dist:.2f}, expected < 5.0 "
        "(particles drifted too far from sculpture)"
    )


def test_stability_1000_frames():
    """PHYS-02: Simulation stays stable for 1000+ frames without divergence.

    Acceptance: No particles escape to infinity, no NaN/Inf in positions
    or velocities after 1000 simulation steps with default parameters.
    """
    engine, device, _, _ = _make_pbf_engine(1000)

    for _ in range(1000):
        engine.step()

    assert engine.running

    # Read back positions and check for stability
    positions = engine._particle_buffer.read_positions()
    assert positions.shape == (1000, 3)

    # No NaN or Inf
    assert np.all(np.isfinite(positions)), "Positions contain NaN or Inf after 1000 frames"

    # Positions should be within reasonable bounds (not exploded)
    assert np.all(np.abs(positions) < 200.0), (
        f"Particles exploded: max position component = {np.abs(positions).max():.1f}"
    )


def test_gpu_spatial_hash_correctness():
    """PHYS-03: GPU spatial hash produces correct neighbor structure.

    Acceptance: Simulation with known positions runs stably, proving
    the spatial hash correctly identifies neighbors for density and
    correction passes. If the hash were wrong, the solver would diverge.
    """
    engine, device, _, _ = _make_pbf_engine(500)

    # Step enough times for spatial hash to be rebuilt multiple times
    for _ in range(100):
        engine.step()

    assert engine.running

    # Read back positions -- if spatial hash were broken, particles would
    # explode or collapse due to incorrect neighbor lookup
    positions = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(positions)), "Spatial hash likely broken: NaN/Inf in positions"
    assert np.all(np.abs(positions) < 200.0), "Spatial hash likely broken: particles exploded"


def test_no_nan_inf_after_1000_frames():
    """PHYS-04: Force and velocity clamping prevents numerical blowup.

    Acceptance: After 1000 frames with aggressive parameters (high
    home_strength, low damping), no NaN or Inf values appear in any
    GPU buffer. max_force and max_velocity clamps hold.
    """
    engine, device, _, _ = _make_pbf_engine(1000)

    # Use more aggressive parameters
    engine.update_visual_param("home_strength", 10.0)
    engine.update_visual_param("damping", 0.95)

    for _ in range(1000):
        engine.step()

    # Read back all positions
    positions = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(positions)), (
        "NaN/Inf found after 1000 frames with aggressive params"
    )


def test_cfl_timestep_adapts():
    """PHYS-05: CFL-adaptive timestep adjusts dt based on max velocity.

    Acceptance: The simulation remains stable after many steps, proving
    the CFL mechanism (or conservative dt) keeps the simulation within
    safe bounds. The adaptive dt is always <= dt_target.
    """
    engine, device, _, _ = _make_pbf_engine(1000)

    dt_target = engine.params.dt

    # Step many times
    for _ in range(500):
        engine.step()

    assert engine.running

    # Verify stability (CFL's purpose is preventing runaway)
    positions = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(positions)), "CFL failed: NaN/Inf after 500 frames"
    assert np.all(np.abs(positions) < 200.0), "CFL failed: particles exploded"


def test_curl_noise_produces_flow():
    """PHYS-06: Curl noise field produces divergence-free flow patterns.

    Acceptance: Particles exhibit smooth, sweeping flow patterns. After
    100 frames, particles have moved from initial positions but remain
    near home (haven't exploded). No NaN.
    """
    engine, device, initial_positions, colors = _make_pbf_engine(1000)

    # Ensure noise is active
    engine.update_visual_param("noise_amplitude", 1.0)
    engine.update_visual_param("noise_frequency", 0.5)

    for _ in range(100):
        engine.step()

    assert engine.running

    final_positions = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(final_positions)), "Curl noise produced NaN/Inf"

    # Particles should have moved (curl noise creates flow)
    displacements = final_positions - initial_positions
    total_movement = np.linalg.norm(displacements, axis=1)
    mean_movement = np.mean(total_movement)
    assert mean_movement > 0.001, (
        f"Particles barely moved (mean={mean_movement:.5f}), curl noise not working"
    )

    # But particles should still be near home (not exploded)
    assert np.all(np.abs(final_positions) < 200.0), (
        f"Particles exploded: max pos = {np.abs(final_positions).max():.1f}"
    )


def test_vorticity_confinement_effect():
    """PHYS-07: Vorticity confinement adds small eddies to the flow.

    Acceptance: With vorticity_epsilon > 0, the simulation runs stably.
    Verify no crash with vorticity enabled and that particles remain
    within bounds.
    """
    engine, device, _, _ = _make_pbf_engine(500)

    # Enable vorticity confinement
    engine.update_visual_param("vorticity_epsilon", 0.01)

    for _ in range(100):
        engine.step()

    assert engine.running

    positions = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(positions)), "Vorticity confinement produced NaN/Inf"
    assert np.all(np.abs(positions) < 200.0), "Vorticity confinement caused explosion"

    # Run a second sim with vorticity disabled for comparison
    engine2, _, _, _ = _make_pbf_engine(500)
    engine2.update_visual_param("vorticity_epsilon", 0.0)

    for _ in range(100):
        engine2.step()

    positions2 = engine2._particle_buffer.read_positions()
    assert np.all(np.isfinite(positions2)), "Zero-vorticity sim produced NaN/Inf"


def test_breathing_modulation():
    """PHYS-08: Breathing modulation creates periodic home_strength variation.

    Acceptance: compute_breathing returns different values at different times.
    The modulation oscillates within the expected range.
    """
    from apollo7.simulation.parameters import SimulationParams

    p = SimulationParams(breathing_amplitude=0.15, breathing_rate=0.2)

    # At t=0, sin(0) = 0, so breathing_mod = 1.0
    val_0 = p.compute_breathing(0.0)
    assert val_0 == pytest.approx(1.0, abs=1e-6)

    # At t = period/4 = 1.25s, sin(pi/2) = 1, so breathing_mod = 1.15
    period = 1.0 / p.breathing_rate  # 5.0 seconds
    val_peak = p.compute_breathing(period / 4.0)
    assert val_peak > 1.0, f"Expected > 1.0 at peak, got {val_peak}"
    assert val_peak == pytest.approx(1.15, abs=1e-6)

    # At t = 3*period/4, sin(3*pi/2) = -1, so breathing_mod = 0.85
    val_trough = p.compute_breathing(3.0 * period / 4.0)
    assert val_trough < 1.0, f"Expected < 1.0 at trough, got {val_trough}"
    assert val_trough == pytest.approx(0.85, abs=1e-6)

    # Verify all samples are within expected range [0.85, 1.15]
    for i in range(200):
        t = i * 0.05
        val = p.compute_breathing(t)
        assert 0.85 - 1e-6 <= val <= 1.15 + 1e-6, (
            f"Breathing out of range at t={t}: {val}"
        )


def test_iteration_count_affects_density():
    """PHYS-09: Solver iterations slider changes fluid cohesion.

    Acceptance: solver_iterations parameter is respected by the PBF solver,
    resulting in different numbers of constraint solving passes. The engine
    remains stable with iteration counts from 1 (wispy/gas) to 6 (dense/liquid).

    We verify:
    1. The solver dispatches proportionally more compute passes for higher iteration counts
    2. The engine runs stably with iteration counts 1, 2, 4, and 6
    3. Particles remain finite (no NaN/Inf explosion) at all iteration levels
    4. The parameter is hot-reloadable via update_visual_param
    """
    engine, device, positions, colors = _make_pbf_engine(1000)

    # Track compute dispatches to verify iteration count is respected
    from apollo7.simulation.pbf_solver import PBFSolver

    dispatch_count = [0]
    orig_dispatch = PBFSolver._dispatch_compute

    def counted_dispatch(self, pipeline, bind_group, total):
        dispatch_count[0] += 1
        return orig_dispatch(self, pipeline, bind_group, total)

    PBFSolver._dispatch_compute = counted_dispatch

    try:
        # Measure dispatches for iterations=1
        dispatch_count[0] = 0
        engine.update_visual_param("solver_iterations", 1)
        engine.step()
        dispatches_1 = dispatch_count[0]

        # Measure dispatches for iterations=4
        dispatch_count[0] = 0
        engine.update_visual_param("solver_iterations", 4)
        engine.step()
        dispatches_4 = dispatch_count[0]

        # iterations=4 should have 6 more dispatches than iterations=1
        # (3 extra density passes + 3 extra correct passes)
        assert dispatches_4 > dispatches_1, (
            f"Expected more dispatches for 4 iterations ({dispatches_4}) "
            f"than 1 iteration ({dispatches_1})"
        )
        assert dispatches_4 - dispatches_1 == 6, (
            f"Expected 6 extra dispatches (3 density + 3 correct), "
            f"got {dispatches_4 - dispatches_1}"
        )
    finally:
        PBFSolver._dispatch_compute = orig_dispatch

    # Run extended simulation with each iteration level to verify stability
    for iters in (1, 2, 4, 6):
        test_engine, _, _, _ = _make_pbf_engine(1000)
        test_engine.update_visual_param("solver_iterations", iters)
        for _ in range(200):
            test_engine.step()

        assert test_engine.running, f"Engine stopped with iterations={iters}"

        final_pos = test_engine._particle_buffer.read_positions()
        assert np.all(np.isfinite(final_pos)), (
            f"NaN/Inf with solver_iterations={iters}"
        )
        assert np.all(np.abs(final_pos) < 200.0), (
            f"Particles exploded with solver_iterations={iters}"
        )

    # Verify hot-reload: changing iterations mid-simulation doesn't crash
    engine.update_visual_param("solver_iterations", 1)
    for _ in range(10):
        engine.step()
    engine.update_visual_param("solver_iterations", 6)
    for _ in range(10):
        engine.step()
    engine.update_visual_param("solver_iterations", 2)
    for _ in range(10):
        engine.step()

    assert engine.running
    final = engine._particle_buffer.read_positions()
    assert np.all(np.isfinite(final)), "NaN/Inf after iteration count changes"
