"""Tests for SimulationParams with PBF parameters and uniform packing.

GPU-dependent tests use pytest.importorskip to skip gracefully
when wgpu is unavailable.
"""

import math
import struct

import numpy as np
import pytest

from apollo7.simulation.parameters import SimulationParams


class TestSimulationParamsPBFDefaults:
    """Verify PBF parameter default values are set correctly."""

    def test_noise_defaults(self):
        p = SimulationParams()
        assert p.noise_frequency == 0.5
        assert p.noise_amplitude == 1.0
        assert p.noise_octaves == 4
        assert p.turbulence_scale == 1.0

    def test_pbf_home_defaults(self):
        p = SimulationParams()
        assert p.home_strength == 5.0
        assert p.breathing_rate == 0.2
        assert p.breathing_amplitude == 0.15

    def test_pbf_solver_defaults(self):
        p = SimulationParams()
        assert p.kernel_radius == 0.1
        assert p.rest_density == 6378.0
        assert p.epsilon_pbf == 600.0
        assert p.solver_iterations == 2

    def test_pbf_pressure_defaults(self):
        p = SimulationParams()
        assert p.artificial_pressure_k == 0.0001
        assert p.artificial_pressure_n == 4
        assert p.delta_q == 0.03
        assert p.xsph_c == 0.01

    def test_pbf_stability_defaults(self):
        p = SimulationParams()
        assert p.vorticity_epsilon == 0.01
        assert p.max_force == 50.0
        assert p.max_velocity == 10.0

    def test_integration_defaults(self):
        p = SimulationParams()
        assert p.speed == 1.0
        assert p.dt == 0.016
        assert p.damping == 0.99

    def test_force_defaults(self):
        p = SimulationParams()
        assert p.gravity == (0.0, -0.1, 0.0)
        assert p.wind == (0.0, 0.0, 0.0)

    def test_runtime_defaults(self):
        p = SimulationParams()
        assert p.time == 0.0
        assert p.breathing_mod == 1.0
        assert p.particle_count == 0


class TestOldSPHParamsRemoved:
    """Verify old SPH-only fields are removed."""

    def test_no_gas_constant(self):
        assert not hasattr(SimulationParams(), "gas_constant")

    def test_no_viscosity(self):
        assert not hasattr(SimulationParams(), "viscosity")

    def test_no_pressure_strength(self):
        assert not hasattr(SimulationParams(), "pressure_strength")

    def test_no_surface_tension(self):
        assert not hasattr(SimulationParams(), "surface_tension")

    def test_no_attraction_strength(self):
        assert not hasattr(SimulationParams(), "attraction_strength")

    def test_no_repulsion_strength(self):
        assert not hasattr(SimulationParams(), "repulsion_strength")

    def test_no_repulsion_radius(self):
        assert not hasattr(SimulationParams(), "repulsion_radius")

    def test_no_smoothing_radius(self):
        assert not hasattr(SimulationParams(), "smoothing_radius")

    def test_no_sph_enabled(self):
        assert not hasattr(SimulationParams(), "sph_enabled")

    def test_no_performance_mode(self):
        assert not hasattr(SimulationParams(), "performance_mode")

    def test_no_attractor_global_strength(self):
        assert not hasattr(SimulationParams(), "attractor_global_strength")


class TestUniformBytes:
    """Verify to_uniform_bytes() produces correctly packed PBF layout."""

    def test_uniform_size_is_128(self):
        assert SimulationParams.UNIFORM_SIZE == 128

    def test_byte_count_is_128(self):
        p = SimulationParams()
        data = p.to_uniform_bytes()
        assert len(data) == 128

    def test_byte_count_is_multiple_of_16(self):
        p = SimulationParams()
        data = p.to_uniform_bytes()
        assert len(data) % 16 == 0

    def test_home_strength_at_vec4_1_offset_16(self):
        p = SimulationParams(home_strength=7.5)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 16)[0]
        assert val == pytest.approx(7.5)

    def test_kernel_radius_at_vec4_2_offset_32(self):
        p = SimulationParams(kernel_radius=0.2)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 32)[0]
        assert val == pytest.approx(0.2)

    def test_vorticity_epsilon_at_vec4_4_offset_64(self):
        p = SimulationParams(vorticity_epsilon=0.05)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 64)[0]
        assert val == pytest.approx(0.05)

    def test_gravity_at_vec4_5_offset_80(self):
        p = SimulationParams(gravity=(1.0, 2.0, 3.0))
        data = p.to_uniform_bytes()
        gx, gy, gz, damping = struct.unpack_from("<4f", data, 80)
        assert gx == pytest.approx(1.0)
        assert gy == pytest.approx(2.0)
        assert gz == pytest.approx(3.0)

    def test_time_at_vec4_7_offset_112(self):
        p = SimulationParams(time=42.0)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 112)[0]
        assert val == pytest.approx(42.0)

    def test_noise_frequency_at_offset_0(self):
        p = SimulationParams(noise_frequency=2.5)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 0)[0]
        assert val == pytest.approx(2.5)


class TestParamClassification:
    """Verify visual vs physics parameter classification."""

    def test_all_pbf_params_are_visual(self):
        pbf_params = [
            "home_strength",
            "breathing_rate",
            "breathing_amplitude",
            "kernel_radius",
            "rest_density",
            "epsilon_pbf",
            "solver_iterations",
            "artificial_pressure_k",
            "artificial_pressure_n",
            "delta_q",
            "xsph_c",
            "vorticity_epsilon",
            "max_force",
            "max_velocity",
        ]
        for name in pbf_params:
            assert SimulationParams.is_visual_param(name), f"{name} should be visual"

    def test_noise_params_are_visual(self):
        for name in ["noise_frequency", "noise_amplitude", "noise_octaves", "turbulence_scale"]:
            assert SimulationParams.is_visual_param(name), f"{name} should be visual"

    def test_core_params_are_visual(self):
        for name in ["speed", "damping", "gravity", "wind"]:
            assert SimulationParams.is_visual_param(name), f"{name} should be visual"

    def test_no_physics_params(self):
        assert not SimulationParams.is_physics_param("home_strength")
        assert not SimulationParams.is_physics_param("solver_iterations")

    def test_unknown_param_is_neither(self):
        assert not SimulationParams.is_visual_param("nonexistent")
        assert not SimulationParams.is_physics_param("nonexistent")


class TestBreathingModulation:
    """Verify breathing computation."""

    def test_breathing_at_zero_time(self):
        p = SimulationParams(breathing_amplitude=0.15, breathing_rate=0.2)
        val = p.compute_breathing(0.0)
        assert val == pytest.approx(1.0)

    def test_breathing_range(self):
        p = SimulationParams(breathing_amplitude=0.15, breathing_rate=0.2)
        # Sample many time values
        values = [p.compute_breathing(t * 0.1) for t in range(100)]
        assert min(values) >= 0.85 - 1e-6
        assert max(values) <= 1.15 + 1e-6

    def test_breathing_is_periodic(self):
        p = SimulationParams(breathing_amplitude=0.15, breathing_rate=0.2)
        # Period = 1/0.2 = 5 seconds
        v1 = p.compute_breathing(1.0)
        v2 = p.compute_breathing(6.0)
        assert v1 == pytest.approx(v2, abs=1e-6)


class TestWithUpdate:
    """Verify immutable update pattern."""

    def test_creates_new_instance(self):
        p1 = SimulationParams()
        p2 = p1.with_update(speed=2.0)
        assert p1.speed == 1.0
        assert p2.speed == 2.0
        assert p1 is not p2

    def test_preserves_other_values(self):
        p1 = SimulationParams(noise_frequency=3.0)
        p2 = p1.with_update(speed=5.0)
        assert p2.noise_frequency == 3.0
        assert p2.speed == 5.0

    def test_with_update_home_strength(self):
        p1 = SimulationParams()
        p2 = p1.with_update(home_strength=10.0)
        assert p2.home_strength == 10.0
        assert p1.home_strength == 5.0

    def test_with_update_solver_iterations(self):
        p1 = SimulationParams()
        p2 = p1.with_update(solver_iterations=4)
        assert p2.solver_iterations == 4
        assert p1.solver_iterations == 2


class TestParticleBufferWithMock:
    """Test ParticleBuffer creation with mock device if wgpu unavailable."""

    def test_particle_buffer_creation(self):
        wgpu = pytest.importorskip("wgpu")
        device = wgpu.utils.get_default_device()

        from apollo7.simulation.buffers import ParticleBuffer

        buf = ParticleBuffer(device, max_particles=1000)
        assert buf.max_particles == 1000
        assert buf.particle_count == 0

    def test_particle_buffer_upload(self):
        wgpu = pytest.importorskip("wgpu")
        device = wgpu.utils.get_default_device()

        from apollo7.simulation.buffers import ParticleBuffer

        buf = ParticleBuffer(device, max_particles=1000)
        positions = np.random.randn(500, 3).astype(np.float32)
        colors = np.random.rand(500, 4).astype(np.float32)
        buf.upload(positions, colors)
        assert buf.particle_count == 500

    def test_particle_buffer_swap(self):
        wgpu = pytest.importorskip("wgpu")
        device = wgpu.utils.get_default_device()

        from apollo7.simulation.buffers import ParticleBuffer

        buf = ParticleBuffer(device, max_particles=100)
        input_before = buf.input_buffer
        output_before = buf.output_buffer
        buf.swap()
        assert buf.input_buffer is output_before
        assert buf.output_buffer is input_before

    def test_particle_buffer_exceeds_max(self):
        wgpu = pytest.importorskip("wgpu")
        device = wgpu.utils.get_default_device()

        from apollo7.simulation.buffers import ParticleBuffer

        buf = ParticleBuffer(device, max_particles=10)
        positions = np.random.randn(20, 3).astype(np.float32)
        colors = np.random.rand(20, 4).astype(np.float32)
        with pytest.raises(ValueError, match="exceeds max"):
            buf.upload(positions, colors)

    def test_params_buffer_update(self):
        wgpu = pytest.importorskip("wgpu")
        device = wgpu.utils.get_default_device()

        from apollo7.simulation.buffers import ParticleBuffer

        buf = ParticleBuffer(device, max_particles=100)
        params = SimulationParams(speed=2.0)
        # Should not raise
        buf.update_params(params)
