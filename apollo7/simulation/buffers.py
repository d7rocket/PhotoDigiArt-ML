"""Double-buffered GPU particle storage for compute shader simulation.

Each particle is stored as 2x vec4 (position.xyz + life, velocity.xyz + mass)
= 32 bytes. A separate color buffer stores RGBA per particle (16 bytes).

The ParticleBuffer manages ping-pong swap between buf_a and buf_b to
prevent read-write conflicts during parallel compute shader execution.
"""

from __future__ import annotations

import logging

import numpy as np

from apollo7.simulation.parameters import SimulationParams

logger = logging.getLogger(__name__)

# Bytes per particle in state buffer: 2x vec4<f32> = 32 bytes
PARTICLE_STATE_STRIDE = 32
# Bytes per particle in color buffer: vec4<f32> RGBA = 16 bytes
PARTICLE_COLOR_STRIDE = 16


class ParticleBuffer:
    """Manages double-buffered GPU storage for particle simulation.

    Particle state layout per particle (32 bytes):
      vec4: position.xyz, life (w)
      vec4: velocity.xyz, mass (w)

    Color layout per particle (16 bytes):
      vec4: r, g, b, a
    """

    def __init__(self, device, max_particles: int):
        """Create double-buffered particle state and color buffers.

        Args:
            device: wgpu.GPUDevice for buffer creation.
            max_particles: Maximum number of particles to allocate for.
        """
        import wgpu

        self._device = device
        self._max_particles = max_particles
        self._particle_count = 0

        state_size = max_particles * PARTICLE_STATE_STRIDE
        color_size = max_particles * PARTICLE_COLOR_STRIDE

        usage = (
            wgpu.BufferUsage.STORAGE
            | wgpu.BufferUsage.COPY_SRC
            | wgpu.BufferUsage.COPY_DST
        )

        self._buf_a = device.create_buffer(size=state_size, usage=usage)
        self._buf_b = device.create_buffer(size=state_size, usage=usage)
        self._color_buf = device.create_buffer(size=color_size, usage=usage)

        # Track which buffer is input vs output
        self._current_input = "a"

        # Uniform buffer for SimulationParams
        self._params_buf = device.create_buffer(
            size=SimulationParams.UNIFORM_SIZE,
            usage=wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST,
        )

        logger.info(
            "ParticleBuffer created: max_particles=%d, state=%d bytes, colors=%d bytes",
            max_particles,
            state_size,
            color_size,
        )

    def upload(self, positions: np.ndarray, colors: np.ndarray) -> None:
        """Upload initial particle state to GPU.

        Args:
            positions: (N, 3) float32 array of XYZ positions.
            colors: (N, 4) float32 array of RGBA colors.
        """
        n = positions.shape[0]
        if n > self._max_particles:
            raise ValueError(
                f"Particle count {n} exceeds max {self._max_particles}"
            )
        self._particle_count = n

        # Pack state: each particle = [px, py, pz, life=1.0, vx=0, vy=0, vz=0, mass=1.0]
        state = np.zeros((n, 8), dtype=np.float32)
        state[:, 0:3] = positions[:, 0:3].astype(np.float32)
        state[:, 3] = 1.0  # life
        # velocity starts at zero, mass = 1.0
        state[:, 7] = 1.0  # mass

        state_bytes = state.tobytes()
        self._device.queue.write_buffer(self._buf_a, 0, state_bytes)

        # Upload colors
        colors_f32 = colors[:, 0:4].astype(np.float32)
        self._device.queue.write_buffer(self._color_buf, 0, colors_f32.tobytes())

        # Reset to read from buf_a
        self._current_input = "a"

        logger.info("Uploaded %d particles to GPU", n)

    def swap(self) -> None:
        """Swap input and output buffer references (pointer swap, no GPU copy)."""
        self._current_input = "b" if self._current_input == "a" else "a"

    def update_params(self, params: SimulationParams) -> None:
        """Upload simulation parameters to the uniform buffer.

        Args:
            params: SimulationParams to pack and upload.
        """
        self._device.queue.write_buffer(
            self._params_buf, 0, params.to_uniform_bytes()
        )

    def read_positions(self) -> np.ndarray:
        """Read back positions from the current output buffer (CPU readback).

        WARNING: This is expensive -- use only for export/save, NOT per-frame.

        Returns:
            (N, 3) float32 array of current positions.
        """
        buf = self.output_buffer
        n = self._particle_count
        size = n * PARTICLE_STATE_STRIDE

        # Map buffer for reading
        raw = self._device.queue.read_buffer(buf, 0, size)
        state = np.frombuffer(raw, dtype=np.float32).reshape(n, 8)
        return state[:, 0:3].copy()

    @property
    def input_buffer(self):
        """Current input (read) buffer for compute shaders."""
        return self._buf_a if self._current_input == "a" else self._buf_b

    @property
    def output_buffer(self):
        """Current output (write) buffer for compute shaders."""
        return self._buf_b if self._current_input == "a" else self._buf_a

    @property
    def color_buffer(self):
        """Color buffer (RGBA per particle)."""
        return self._color_buf

    @property
    def params_buffer(self):
        """Uniform buffer for SimulationParams."""
        return self._params_buf

    @property
    def particle_count(self) -> int:
        """Number of active particles."""
        return self._particle_count

    @property
    def max_particles(self) -> int:
        """Maximum particle capacity."""
        return self._max_particles
