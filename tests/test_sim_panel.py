"""Tests for SimulationPanel (PBF controls) and FPSCounter widgets."""

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
    """Tests for SimulationPanel widget with PBF controls."""

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

    def test_has_pbf_essential_sliders(self, panel):
        """Panel has PBF essential control sliders."""
        assert "solver_iterations" in panel._sliders
        assert "home_strength" in panel._sliders
        assert "noise_amplitude" in panel._sliders
        assert "breathing_rate" in panel._sliders

    def test_has_pbf_advanced_sliders(self, panel):
        """Panel has PBF advanced control sliders."""
        assert "noise_frequency" in panel._sliders
        assert "vorticity_epsilon" in panel._sliders
        assert "xsph_c" in panel._sliders
        assert "damping" in panel._sliders
        assert "breathing_amplitude" in panel._sliders

    def test_no_old_sph_sliders(self, panel):
        """Panel does not have old SPH sliders."""
        assert "viscosity" not in panel._sliders
        assert "pressure_strength" not in panel._sliders
        assert "surface_tension" not in panel._sliders
        assert "attraction_strength" not in panel._sliders
        assert "repulsion_strength" not in panel._sliders
        assert "repulsion_radius" not in panel._sliders

    def test_param_changed_signal_emits_valid_names(self, panel):
        """Each slider emits param_changed with a name that exists in SimulationParams."""
        valid_visual = SimulationParams.is_visual_param
        emitted = []
        panel.param_changed.connect(lambda name, val: emitted.append(name))

        # Change each slider (skip solver_iterations as it triggers crossfade)
        for param_name, (slider, _, _) in panel._sliders.items():
            if param_name == "solver_iterations":
                continue
            current = slider.value()
            slider.setValue(current + 1 if current < 100 else current - 1)

        assert len(emitted) > 0, "No param_changed signals emitted"
        for name in emitted:
            assert valid_visual(name), f"Unknown visual param: {name}"

    def test_cohesion_slider_emits_solver_iterations(self, panel):
        """Cohesion slider emits solver_iterations param."""
        emitted = []
        panel.param_changed.connect(lambda name, val: emitted.append((name, val)))

        slider, _, _ = panel._sliders["solver_iterations"]
        current = slider.value()
        slider.setValue(current + 10 if current < 90 else current - 10)

        # Should emit solver_iterations (and possibly home_strength for crossfade)
        iter_emits = [e for e in emitted if e[0] == "solver_iterations"]
        assert len(iter_emits) >= 1, "Cohesion slider did not emit solver_iterations"

    def test_section_reset_emits_signal(self, panel):
        """Section reset buttons emit section_reset signal with section name."""
        emitted = []
        panel.section_reset.connect(lambda name: emitted.append(name))

        panel.btn_reset_essential.click()
        assert "essential" in emitted

        # Advanced section must be checked (expanded) for its children to be enabled
        panel.advanced_group.setChecked(True)
        panel.btn_reset_advanced.click()
        assert "advanced" in emitted

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
        """Panel has the expected number of PBF parameter sliders."""
        # Essential: solver_iterations, home_strength, noise_amplitude, breathing_rate (4)
        # Advanced: noise_frequency, vorticity_epsilon, xsph_c, damping, breathing_amplitude (5)
        assert len(panel._sliders) == 9

    def test_set_simulation_running(self, panel):
        """set_simulation_running updates button states."""
        panel.set_simulation_running(True)
        assert panel.btn_pause.isEnabled()
        assert panel.btn_simulate.text() == "Restart"

        panel.set_simulation_running(False)
        assert not panel.btn_pause.isEnabled()
        assert panel.btn_simulate.text() == "Simulate"

    def test_advanced_section_collapsed_by_default(self, panel):
        """Advanced section is collapsed by default."""
        assert not panel.advanced_group.isChecked()
        # Widget is hidden (not visible to user)
        assert panel._advanced_widget.isHidden()

    def test_advanced_section_expands(self, panel):
        """Advanced section can be expanded."""
        panel.advanced_group.setChecked(True)
        # Widget is no longer hidden (would be visible when parent is shown)
        assert not panel._advanced_widget.isHidden()

    def test_cohesion_slider_range(self, panel):
        """Cohesion slider maps to integer range 1-6."""
        slider, _, spec = panel._sliders["solver_iterations"]
        # At min (tick 0) -> 1
        slider.setValue(0)
        val = panel._slider_value(slider)
        assert val == 1

        # At max (tick 100) -> 6
        slider.setValue(100)
        val = panel._slider_value(slider)
        assert val == 6


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
