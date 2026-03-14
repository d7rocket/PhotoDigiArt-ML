"""Tests for SimulationEngine orchestrator.

Tests cover state machine transitions, parameter hot-reload vs restart,
particle count tracking, and GPU integration (skipped if wgpu unavailable).
"""

import numpy as np
import pytest


def _make_engine():
    """Create a SimulationEngine with a real wgpu device."""
    wgpu = pytest.importorskip("wgpu")
    device = wgpu.utils.get_default_device()
    from apollo7.simulation.engine import SimulationEngine

    return SimulationEngine(device), device


def _make_test_data(n=1000):
    """Generate random test positions and colors."""
    positions = np.random.randn(n, 3).astype(np.float32) * 5.0
    colors = np.random.rand(n, 4).astype(np.float32)
    colors[:, 3] = 1.0  # Full alpha
    return positions, colors


class TestSimulationEngineStateMachine:
    """Verify state machine transitions."""

    def test_initial_state_is_idle(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        assert engine.state == SimState.IDLE
        assert not engine.running
        assert not engine.paused

    def test_initialize_transitions_to_running(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        assert engine.state == SimState.RUNNING
        assert engine.running
        assert not engine.paused

    def test_pause_transitions_to_paused(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        engine.pause()
        assert engine.state == SimState.PAUSED
        assert engine.paused
        assert not engine.running

    def test_resume_transitions_to_running(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        engine.pause()
        engine.resume()
        assert engine.state == SimState.RUNNING
        assert engine.running

    def test_restart_transitions_to_running(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        engine.pause()
        engine.restart()
        assert engine.state == SimState.RUNNING

    def test_toggle_pause(self):
        engine, _ = _make_engine()
        from apollo7.simulation.engine import SimState

        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)

        engine.toggle_pause()
        assert engine.paused

        engine.toggle_pause()
        assert engine.running

    def test_step_does_nothing_when_paused(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        engine.pause()
        # Should not raise or change state
        engine.step()
        assert engine.paused

    def test_step_does_nothing_when_idle(self):
        engine, _ = _make_engine()
        # Should not raise
        engine.step()


class TestParameterHotReload:
    """Verify visual params hot-reload and physics params restart."""

    def test_update_visual_param_does_not_restart(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)

        # Step a few times to advance time
        engine.step()
        engine.step()
        time_before = engine._time

        # Visual param update should NOT reset time (no restart)
        engine.update_visual_param("speed", 2.0)
        assert engine.params.speed == 2.0
        assert engine._time == time_before  # Time unchanged
        assert engine.running

    def test_update_physics_param_triggers_restart(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)

        # Step to advance time
        engine.step()
        engine.step()

        # Physics param update should restart (reset time)
        engine.update_physics_param("viscosity", 0.5)
        assert engine.params.viscosity == 0.5
        assert engine._time == 0.0  # Time reset by restart
        assert engine.running


class TestParticleCount:
    """Verify particle count tracking."""

    def test_particle_count_matches_input(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(500)
        engine.initialize(positions, colors)
        assert engine.particle_count == 500

    def test_particle_count_zero_before_init(self):
        engine, _ = _make_engine()
        assert engine.particle_count == 0

    def test_particle_count_with_different_sizes(self):
        engine, _ = _make_engine()
        for n in [10, 100, 1000]:
            positions, colors = _make_test_data(n)
            engine.initialize(positions, colors)
            assert engine.particle_count == n


class TestGPUBufferAccess:
    """Verify GPU buffer access methods."""

    def test_get_positions_buffer_returns_buffer(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        buf = engine.get_positions_buffer()
        assert buf is not None

    def test_get_colors_buffer_returns_buffer(self):
        engine, _ = _make_engine()
        positions, colors = _make_test_data(100)
        engine.initialize(positions, colors)
        buf = engine.get_colors_buffer()
        assert buf is not None

    def test_buffers_none_before_init(self):
        engine, _ = _make_engine()
        assert engine.get_positions_buffer() is None
        assert engine.get_colors_buffer() is None


class TestPerformanceMode:
    """Verify performance mode toggle."""

    def test_performance_mode_default_off(self):
        engine, _ = _make_engine()
        assert engine._performance_mode is False

    def test_set_performance_mode(self):
        engine, _ = _make_engine()
        engine.set_performance_mode(True)
        assert engine._performance_mode is True
        engine.set_performance_mode(False)
        assert engine._performance_mode is False

    def test_sim_steps_per_frame(self):
        engine, _ = _make_engine()
        engine.set_sim_steps_per_frame(3)
        assert engine._sim_steps_per_frame == 3
        # Minimum is 1
        engine.set_sim_steps_per_frame(0)
        assert engine._sim_steps_per_frame == 1


class TestGPUIntegration:
    """GPU integration tests -- verify no crashes during actual dispatch."""

    def test_step_10_times_no_crash(self):
        """Initialize with 1000 particles, step 10 times, verify no crash."""
        engine, _ = _make_engine()
        positions, colors = _make_test_data(1000)
        engine.initialize(positions, colors)

        for i in range(10):
            engine.step()

        assert engine.running
        assert engine.particle_count == 1000

    def test_restart_after_stepping(self):
        """Step, restart, step again -- verify no crash."""
        engine, _ = _make_engine()
        positions, colors = _make_test_data(500)
        engine.initialize(positions, colors)

        engine.step()
        engine.step()
        engine.restart()
        engine.step()
        engine.step()

        assert engine.running

    def test_import_simulation_engine(self):
        """Verify the import path works."""
        from apollo7.simulation.engine import SimulationEngine

        assert SimulationEngine is not None

    def test_import_from_package(self):
        """Verify package-level import works."""
        from apollo7.simulation import SimulationEngine

        assert SimulationEngine is not None
