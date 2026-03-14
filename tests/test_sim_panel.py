"""Tests for SimulationPanel and FPSCounter widgets."""

from __future__ import annotations

import time

import pytest
from PySide6 import QtWidgets

from apollo7.gui.panels.simulation_panel import SimulationPanel
from apollo7.gui.widgets.fps_counter import FPSCounter
from apollo7.simulation.parameters import SimulationParams


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for the test session."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def panel(qapp):
    """Create a SimulationPanel instance."""
    return SimulationPanel()


@pytest.fixture
def fps_counter(qapp):
    """Create an FPSCounter instance."""
    return FPSCounter()


class TestSimulationPanel:
    """Tests for SimulationPanel widget."""

    def test_instantiation(self, panel):
        """SimulationPanel can be created without errors."""
        assert panel is not None
        assert isinstance(panel, QtWidgets.QWidget)

    def test_has_simulate_button(self, panel):
        """Panel has a Simulate button."""
        assert panel.btn_simulate is not None
        assert panel.btn_simulate.text() == "Simulate"

    def test_has_pause_button(self, panel):
        """Panel has a Pause button, initially disabled."""
        assert panel.btn_pause is not None
        assert not panel.btn_pause.isEnabled()

    def test_has_performance_checkbox(self, panel):
        """Panel has a Performance Mode checkbox."""
        assert panel.chk_performance is not None

    def test_param_changed_signal_emits_valid_names(self, panel):
        """Each slider emits param_changed with a name that exists in SimulationParams."""
        # Collect all valid param names from SimulationParams
        valid_visual = {
            "noise_frequency", "noise_amplitude", "noise_octaves",
            "turbulence_scale", "speed", "damping",
        }
        valid_physics = {
            "viscosity", "pressure_strength", "surface_tension",
            "attraction_strength", "repulsion_strength", "repulsion_radius",
            "smoothing_radius", "rest_density", "gas_constant",
            "gravity", "wind",
        }
        # Sim panel also uses sub-params for gravity/wind
        valid_sub_params = {"gravity_y", "wind_x", "wind_z"}
        all_valid = valid_visual | valid_physics | valid_sub_params

        emitted = []
        panel.param_changed.connect(lambda name, val: emitted.append(name))

        # Change each slider
        for param_name, (slider, _, _) in panel._sliders.items():
            current = slider.value()
            slider.setValue(current + 1 if current < 100 else current - 1)

        # All emitted param names must be valid
        assert len(emitted) > 0, "No param_changed signals emitted"
        for name in emitted:
            assert name in all_valid, f"Unknown param name: {name}"

    def test_section_reset_emits_signal(self, panel):
        """Section reset buttons emit section_reset signal with section name."""
        emitted = []
        panel.section_reset.connect(lambda name: emitted.append(name))

        panel.btn_reset_flow.click()
        assert "flow" in emitted

        panel.btn_reset_forces.click()
        assert "forces" in emitted

        panel.btn_reset_fluid.click()
        assert "fluid" in emitted

    def test_reset_all_emits_signal(self, panel):
        """Reset All button emits reset_all signal."""
        emitted = []
        panel.reset_all.connect(lambda: emitted.append(True))
        panel.btn_reset_all.click()
        assert len(emitted) == 1

    def test_simulate_clicked_emits(self, panel):
        """Simulate button emits simulate_clicked signal."""
        emitted = []
        panel.simulate_clicked.connect(lambda: emitted.append(True))
        panel.btn_simulate.click()
        assert len(emitted) == 1

    def test_pause_toggled_emits(self, panel):
        """Pause button toggles and emits pause_toggled signal."""
        emitted = []
        panel.pause_toggled.connect(lambda paused: emitted.append(paused))
        panel.btn_pause.setEnabled(True)
        panel.btn_pause.click()
        assert len(emitted) == 1
        assert emitted[0] is True  # First click pauses
        panel.btn_pause.click()
        assert emitted[1] is False  # Second click resumes

    def test_slider_count(self, panel):
        """Panel has the expected number of parameter sliders."""
        # speed, turbulence_scale, noise_frequency, noise_amplitude,
        # noise_octaves, attraction_strength, repulsion_strength,
        # repulsion_radius, gravity_y, wind_x, wind_z,
        # viscosity, pressure_strength, surface_tension
        assert len(panel._sliders) == 14

    def test_set_simulation_running(self, panel):
        """set_simulation_running updates button states."""
        panel.set_simulation_running(True)
        assert panel.btn_pause.isEnabled()
        assert panel.btn_simulate.text() == "Restart"

        panel.set_simulation_running(False)
        assert not panel.btn_pause.isEnabled()
        assert panel.btn_simulate.text() == "Simulate"


class TestFPSCounter:
    """Tests for FPSCounter widget."""

    def test_instantiation(self, fps_counter):
        """FPSCounter can be created."""
        assert fps_counter is not None
        assert "FPS" in fps_counter.text()

    def test_tick_updates_display(self, fps_counter):
        """tick() updates displayed text after sufficient calls."""
        # Force the update interval to be very short
        fps_counter._UPDATE_INTERVAL = 0.01

        for _ in range(20):
            fps_counter.tick()
            time.sleep(0.005)

        text = fps_counter.text()
        assert "FPS" in text
        # Should have a number now, not "--"
        assert "--" not in text

    def test_update_fps_directly(self, fps_counter):
        """update_fps sets the display text."""
        fps_counter.update_fps(60.0)
        assert fps_counter.text() == "60 FPS"

    def test_fps_format(self, fps_counter):
        """FPS display uses integer format."""
        fps_counter.update_fps(59.7)
        assert fps_counter.text() == "60 FPS"
