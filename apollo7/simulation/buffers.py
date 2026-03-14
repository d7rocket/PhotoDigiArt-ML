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

# Spatial hash grid size (128^3 cells)
GRID_SIZE = 128
GRID_TOTAL_CELLS = GRID_SIZE ** 3  # 2,097,152


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

        # --- Auxiliary buffers for forces/SPH passes ---
        aux_usage = wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST

        # Force accumulation: vec4<f32> per particle (16 bytes)
        self._forces_buf = device.create_buffer(
            size=max_particles * 16, usage=aux_usage
        )
        # SPH force accumulation: vec4<f32> per particle (16 bytes)
        self._sph_forces_buf = device.create_buffer(
            size=max_particles * 16, usage=aux_usage
        )
        # Density per particle: f32 (4 bytes)
        self._densities_buf = device.create_buffer(
            size=max_particles * 4, usage=aux_usage
        )
        # Spatial hash grid: cell_counts, cell_offsets (GRID_SIZE^3 * 4 bytes each)
        self._cell_counts_buf = device.create_buffer(
            size=GRID_TOTAL_CELLS * 4, usage=aux_usage
        )
        self._cell_offsets_buf = device.create_buffer(
            size=GRID_TOTAL_CELLS * 4, usage=aux_usage
        )
        # Sorted particle indices: one u32 per particle
        self._sorted_indices_buf = device.create_buffer(
            size=max_particles * 4, usage=aux_usage
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

        # Build spatial hash from initial positions
        self.build_spatial_hash(positions)

        logger.info("Uploaded %d particles to GPU", n)

    def build_spatial_hash(
        self, positions: np.ndarray, cell_size: float = 0.2
    ) -> None:
        """Build spatial hash grid on CPU and upload to GPU buffers.

        Computes cell assignments, counts, prefix-sum offsets, and sorted
        particle indices for neighbor lookup in forces/SPH shaders.

        Only needs to run at simulation start/restart, not per-frame.

        Args:
            positions: (N, 3) float32 array of XYZ positions.
            cell_size: Size of each grid cell (default: repulsion_radius * 2).
        """
        n = positions.shape[0]

        # Compute cell index for each particle
        # Grid is centered at origin with 64-unit offset
        cell_coords = np.floor(
            (positions[:, :3] + 64.0) / cell_size
        ).astype(np.int32)

        # Clamp to valid grid range [0, GRID_SIZE-1]
        cell_coords = np.clip(cell_coords, 0, GRID_SIZE - 1)

        # Compute flat cell hash: x + y * GRID_SIZE + z * GRID_SIZE^2
        cell_hashes = (
            cell_coords[:, 0]
            + cell_coords[:, 1] * GRID_SIZE
            + cell_coords[:, 2] * GRID_SIZE * GRID_SIZE
        ).astype(np.uint32)

        # Count particles per cell
        cell_counts = np.zeros(GRID_TOTAL_CELLS, dtype=np.uint32)
        for h in cell_hashes:
            cell_counts[h] += 1

        # Prefix sum for cell offsets
        cell_offsets = np.zeros(GRID_TOTAL_CELLS, dtype=np.uint32)
        if GRID_TOTAL_CELLS > 0:
            cell_offsets[0] = 0
            np.cumsum(cell_counts[:-1], out=cell_offsets[1:])

        # Build sorted indices (particles sorted by cell)
        sorted_indices = np.zeros(n, dtype=np.uint32)
        # Track current write position per cell
        write_pos = cell_offsets.copy()
        for i in range(n):
            h = cell_hashes[i]
            sorted_indices[write_pos[h]] = i
            write_pos[h] += 1

        # Upload to GPU
        self._device.queue.write_buffer(
            self._cell_counts_buf, 0, cell_counts.tobytes()
        )
        self._device.queue.write_buffer(
            self._cell_offsets_buf, 0, cell_offsets.tobytes()
        )
        self._device.queue.write_buffer(
            self._sorted_indices_buf, 0, sorted_indices.tobytes()
        )

        logger.debug(
            "Spatial hash built: %d particles, %d non-empty cells",
            n,
            int(np.count_nonzero(cell_counts)),
        )

    def clear_forces(self) -> None:
        """Clear force accumulation buffers to zeros.

        Must be called at the start of each simulation step before
        force/SPH compute passes write to these buffers.
        """
        n = self._particle_count
        if n == 0:
            return

        zeros_16 = np.zeros(n * 4, dtype=np.float32).tobytes()
        self._device.queue.write_buffer(self._forces_buf, 0, zeros_16)
        self._device.queue.write_buffer(self._sph_forces_buf, 0, zeros_16)

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
    def forces_buffer(self):
        """Force accumulation buffer (vec4<f32> per particle)."""
        return self._forces_buf

    @property
    def sph_forces_buffer(self):
        """SPH force accumulation buffer (vec4<f32> per particle)."""
        return self._sph_forces_buf

    @property
    def densities_buffer(self):
        """Density buffer (f32 per particle)."""
        return self._densities_buf

    @property
    def cell_counts_buffer(self):
        """Spatial hash cell counts buffer."""
        return self._cell_counts_buf

    @property
    def cell_offsets_buffer(self):
        """Spatial hash cell offsets buffer (prefix sum)."""
        return self._cell_offsets_buf

    @property
    def sorted_indices_buffer(self):
        """Sorted particle indices buffer (sorted by cell hash)."""
        return self._sorted_indices_buf

    @property
    def particle_count(self) -> int:
        """Number of active particles."""
        return self._particle_count

    @property
    def max_particles(self) -> int:
        """Maximum particle capacity."""
        return self._max_particles
