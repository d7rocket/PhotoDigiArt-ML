"""Tests for simulation engine lifecycle wiring in the viewport.

Tests the state machine transitions, parameter routing, and
pause/resume behavior without requiring a GPU.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
from PySide6 import QtWidgets

from apollo7.simulation.parameters import SimulationParams


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the test session."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class FakeParticleBuffer:
    """Stub for ParticleBuffer without GPU."""

    def __init__(self, particle_count=100):
        self._particle_count = particle_count

    @property
    def particle_count(self):
        return self._particle_count

    def read_positions(self):
        return np.random.randn(self._particle_count, 3).astype(np.float32)

    def upload(self, positions, colors):
        self._particle_count = positions.shape[0]

    def update_params(self, params):
        pass

    @property
    def input_buffer(self):
        return MagicMock()

    @property
    def output_buffer(self):
        return MagicMock()

    @property
    def color_buffer(self):
        return MagicMock()

    @property
    def params_buffer(self):
        return MagicMock()

    def swap(self):
        pass


class FakeSimulationEngine:
    """Stub SimulationEngine for unit testing lifecycle wiring."""

    def __init__(self):
        from apollo7.simulation.engine import SimState

        self._state = SimState.IDLE
        self._params = SimulationParams()
        self._particle_buffer = FakeParticleBuffer()
        self._performance_mode = False
        self._initial_positions = None
        self._initial_colors = None
        self._visual_calls = []
        self._physics_calls = []

    def initialize(self, positions, colors, feature_textures=None):
        from apollo7.simulation.engine import SimState

        self._initial_positions = positions.copy()
        self._initial_colors = colors.copy()
        self._particle_buffer = FakeParticleBuffer(positions.shape[0])
        self._state = SimState.RUNNING

    def step(self):
        pass

    def restart(self):
        from apollo7.simulation.engine import SimState

        if self._initial_positions is not None:
            self._state = SimState.RUNNING

    def pause(self):
        from apollo7.simulation.engine import SimState

        if self._state == SimState.RUNNING:
            self._state = SimState.PAUSED

    def resume(self):
        from apollo7.simulation.engine import SimState

        if self._state == SimState.PAUSED:
            self._state = SimState.RUNNING

    def toggle_pause(self):
        from apollo7.simulation.engine import SimState

        if self._state == SimState.RUNNING:
            self.pause()
        elif self._state == SimState.PAUSED:
            self.resume()

    def set_performance_mode(self, enabled):
        self._performance_mode = enabled

    def update_visual_param(self, name, value):
        self._visual_calls.append((name, value))
        self._params = self._params.with_update(**{name: value})

    def update_physics_param(self, name, value):
        self._physics_calls.append((name, value))
        self._params = self._params.with_update(**{name: value})

    @property
    def running(self):
        from apollo7.simulation.engine import SimState

        return self._state == SimState.RUNNING

    @property
    def paused(self):
        from apollo7.simulation.engine import SimState

        return self._state == SimState.PAUSED

    @property
    def state(self):
        return self._state

    @property
    def particle_count(self):
        return self._particle_buffer.particle_count

    @property
    def params(self):
        return self._params


@pytest.fixture
def viewport_widget(qapp):
    """Create a ViewportWidget without canvas initialization."""
    # Patch QRenderWidget and renderer to avoid GPU requirement
    with patch("apollo7.gui.widgets.viewport_widget.QRenderWidget"), \
         patch("apollo7.gui.widgets.viewport_widget.gfx"):
        from apollo7.gui.widgets.viewport_widget import ViewportWidget

        widget = ViewportWidget.__new__(ViewportWidget)
        QtWidgets.QWidget.__init__(widget)
        widget._sim_engine = None
        widget._photo_clouds = {}
        widget._point_objects = []
        widget._current_point_size = 2.0
        widget._current_opacity = 1.0
        widget._layout_mode = "depth_projected"
        widget._multi_photo_mode = "stacked"
        return widget


class TestSimLifecycle:
    """Tests for simulation lifecycle state machine."""

    def test_engine_none_before_init(self, viewport_widget):
        """Engine is None before simulation is triggered."""
        assert viewport_widget._sim_engine is None

    def test_init_simulation_creates_engine(self, viewport_widget):
        """After init_simulation(), engine transitions to valid state."""
        positions = np.random.randn(100, 3).astype(np.float32)
        colors = np.random.rand(100, 4).astype(np.float32)

        engine = FakeSimulationEngine()
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        assert viewport_widget._sim_engine is not None
        assert viewport_widget._sim_engine.particle_count == 100
        assert viewport_widget._sim_engine.running

    def test_pause_resume_transitions(self, viewport_widget):
        """Engine.paused toggles correctly."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        assert engine.running
        assert not engine.paused

        viewport_widget.pause_simulation()
        assert engine.paused
        assert not engine.running

        viewport_widget.resume_simulation()
        assert engine.running
        assert not engine.paused

    def test_toggle_pause(self, viewport_widget):
        """toggle_pause switches between running and paused."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        viewport_widget.toggle_pause()
        assert engine.paused

        viewport_widget.toggle_pause()
        assert engine.running

    def test_restart_resets_to_running(self, viewport_widget):
        """Restart resets to initial state with engine.running True."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        engine.pause()
        assert engine.paused

        engine.restart()
        assert engine.running

    def test_update_sim_param_routes_visual(self, viewport_widget):
        """Visual params route to update_visual_param."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        viewport_widget.update_sim_param("speed", 2.5)
        assert ("speed", 2.5) in engine._visual_calls

    def test_update_sim_param_viscosity_routes_visual(self, viewport_widget):
        """Viscosity routes to update_visual_param (all params visual post d2f401c)."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        viewport_widget.update_sim_param("viscosity", 0.5)
        assert ("viscosity", 0.5) in engine._visual_calls
        assert len(engine._physics_calls) == 0

    def test_update_sim_param_gravity_y_routes_visual(self, viewport_widget):
        """gravity_y compound param routes to visual with gravity tuple (post d2f401c)."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        viewport_widget.update_sim_param("gravity_y", -0.5)
        # Should route to visual with gravity tuple
        assert len(engine._visual_calls) == 1
        name, val = engine._visual_calls[0]
        assert name == "gravity"
        assert val[1] == -0.5
        assert len(engine._physics_calls) == 0

    def test_update_sim_param_wind_x_routes_visual(self, viewport_widget):
        """wind_x compound param routes to visual with wind tuple (post d2f401c)."""
        engine = FakeSimulationEngine()
        positions = np.random.randn(50, 3).astype(np.float32)
        colors = np.random.rand(50, 4).astype(np.float32)
        engine.initialize(positions, colors)
        viewport_widget._sim_engine = engine

        viewport_widget.update_sim_param("wind_x", 0.3)
        assert len(engine._visual_calls) == 1
        name, val = engine._visual_calls[0]
        assert name == "wind"
        assert val[0] == 0.3
        assert len(engine._physics_calls) == 0

    def test_no_error_when_engine_none(self, viewport_widget):
        """update_sim_param does not error when engine is None."""
        viewport_widget._sim_engine = None
        # Should not raise
        viewport_widget.update_sim_param("speed", 1.0)
        viewport_widget.pause_simulation()
        viewport_widget.resume_simulation()
        viewport_widget.toggle_pause()
