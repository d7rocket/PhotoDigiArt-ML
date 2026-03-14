"""Tests for SimulationParams and ParticleBuffer.

GPU-dependent tests use pytest.importorskip to skip gracefully
when wgpu is unavailable.
"""

import struct

import numpy as np
import pytest

from apollo7.simulation.parameters import SimulationParams


class TestSimulationParamsDefaults:
    """Verify default parameter values are set correctly."""

    def test_noise_defaults(self):
        p = SimulationParams()
        assert p.noise_frequency == 0.5
        assert p.noise_amplitude == 1.0
        assert p.noise_octaves == 4
        assert p.turbulence_scale == 1.0

    def test_sph_defaults(self):
        p = SimulationParams()
        assert p.viscosity == 0.1
        assert p.pressure_strength == 1.0
        assert p.surface_tension == 0.01
        assert p.smoothing_radius == 0.1
        assert p.rest_density == 1000.0
        assert p.gas_constant == 2.0

    def test_force_defaults(self):
        p = SimulationParams()
        assert p.attraction_strength == 0.5
        assert p.repulsion_strength == 0.3
        assert p.repulsion_radius == 0.1
        assert p.gravity == (0.0, -0.1, 0.0)
        assert p.wind == (0.0, 0.0, 0.0)

    def test_integration_defaults(self):
        p = SimulationParams()
        assert p.speed == 1.0
        assert p.dt == 0.016
        assert p.damping == 0.99


class TestUniformBytes:
    """Verify to_uniform_bytes() produces correctly packed data."""

    def test_byte_count_is_multiple_of_16(self):
        p = SimulationParams()
        data = p.to_uniform_bytes()
        assert len(data) % 16 == 0

    def test_byte_count_matches_uniform_size(self):
        p = SimulationParams()
        data = p.to_uniform_bytes()
        assert len(data) == SimulationParams.UNIFORM_SIZE

    def test_uniform_size_is_112(self):
        assert SimulationParams.UNIFORM_SIZE == 112

    def test_gravity_packed_correctly(self):
        p = SimulationParams(gravity=(1.0, 2.0, 3.0))
        data = p.to_uniform_bytes()
        # Gravity is at vec4 index 4 = offset 64 bytes
        gx, gy, gz, gpad = struct.unpack_from("<4f", data, 64)
        assert gx == 1.0
        assert gy == 2.0
        assert gz == 3.0
        assert gpad == 0.0

    def test_wind_packed_correctly(self):
        p = SimulationParams(wind=(0.5, 0.0, -1.0))
        data = p.to_uniform_bytes()
        # Wind is at vec4 index 5 = offset 80 bytes
        wx, wy, wz, wpad = struct.unpack_from("<4f", data, 80)
        assert wx == 0.5
        assert wy == 0.0
        assert wz == -1.0
        assert wpad == 0.0

    def test_noise_frequency_at_offset_0(self):
        p = SimulationParams(noise_frequency=2.5)
        data = p.to_uniform_bytes()
        val = struct.unpack_from("<f", data, 0)[0]
        assert val == pytest.approx(2.5)

    def test_time_at_correct_offset(self):
        p = SimulationParams(time=42.0)
        data = p.to_uniform_bytes()
        # Time is at vec4 index 6 = offset 96 bytes
        val = struct.unpack_from("<f", data, 96)[0]
        assert val == pytest.approx(42.0)


class TestParamClassification:
    """Verify visual vs physics parameter classification."""

    def test_visual_params(self):
        visual = [
            "noise_frequency",
            "noise_amplitude",
            "noise_octaves",
            "turbulence_scale",
            "speed",
            "damping",
        ]
        for name in visual:
            assert SimulationParams.is_visual_param(name), f"{name} should be visual"
            assert not SimulationParams.is_physics_param(name), (
                f"{name} should not be physics"
            )

    def test_physics_params(self):
        physics = [
            "viscosity",
            "pressure_strength",
            "surface_tension",
            "attraction_strength",
            "repulsion_strength",
            "repulsion_radius",
            "smoothing_radius",
            "rest_density",
            "gas_constant",
            "gravity",
            "wind",
        ]
        for name in physics:
            assert SimulationParams.is_physics_param(name), (
                f"{name} should be physics"
            )
            assert not SimulationParams.is_visual_param(name), (
                f"{name} should not be visual"
            )

    def test_unknown_param_is_neither(self):
        assert not SimulationParams.is_visual_param("nonexistent")
        assert not SimulationParams.is_physics_param("nonexistent")


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
