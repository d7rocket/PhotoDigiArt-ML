"""GPU-accelerated particle simulation engine.

Orchestrates the PBF (Position Based Fluids) solver for particle simulation.
Manages simulation lifecycle (init, step, pause, restart) and provides
GPU buffer access for rendering.

Designed for 1-5M particles with CFL-adaptive timestep.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import replace

import numpy as np

from apollo7.simulation.buffers import ParticleBuffer
from apollo7.simulation.parameters import SimulationParams

logger = logging.getLogger(__name__)

# CFL coefficient for adaptive timestep
_CFL_COEFF = 0.4


class SimState(enum.Enum):
    """Simulation lifecycle states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationEngine:
    """Orchestrates the PBF solver for particle simulation.

    Lifecycle: IDLE -> initialize() -> RUNNING -> pause() -> PAUSED
    -> resume() -> RUNNING -> restart() -> RUNNING

    The engine manages:
    - Particle state (ParticleBuffer)
    - PBF solver delegation
    - Feature texture upload and home position modulation
    - CFL-adaptive timestep
    - Visual param hot-reload
    """

    def __init__(self, device):
        """Create simulation engine with the given wgpu device.

        Args:
            device: wgpu.GPUDevice for buffer and pipeline creation.
        """
        self._device = device
        self._state = SimState.IDLE
        self._params = SimulationParams()
        self._particle_buffer: ParticleBuffer | None = None
        self._initial_positions: np.ndarray | None = None
        self._initial_colors: np.ndarray | None = None
        self._time: float = 0.0
        self._has_feature_textures: bool = False

        # PBF solver (created during initialize)
        self._pbf_solver = None

        # Attractor data (from collection analysis)
        self._attractors: list[tuple[np.ndarray, float]] = []
        self._attractor_buffer = None  # GPU buffer for attractor vec4 data
        self._max_attractors = 16

        logger.info("SimulationEngine created")

    def initialize(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        feature_textures: dict[str, np.ndarray] | None = None,
    ) -> None:
        """Upload initial point cloud state and set up PBF solver.

        Args:
            positions: (N, 3) float32 array of XYZ positions.
            colors: (N, 4) float32 array of RGBA colors.
            feature_textures: Optional dict of feature maps.
                Keys: "edge_map", "depth_map" with (H, W) float32 arrays.
        """
        from apollo7.simulation.pbf_solver import PBFSolver

        n = positions.shape[0]
        logger.info("Initializing simulation with %d particles", n)

        # Store initial state for restart
        self._initial_positions = positions.copy()
        self._initial_colors = colors.copy()

        # Create particle buffer
        self._particle_buffer = ParticleBuffer(self._device, max_particles=n)
        self._particle_buffer.upload(positions, colors)

        # Upload feature textures if provided and modulate home positions
        if feature_textures:
            self._upload_feature_textures(feature_textures)
            self._apply_feature_modulation(positions, feature_textures)
            self._has_feature_textures = True
        else:
            self._has_feature_textures = False

        # Create PBF solver
        self._pbf_solver = PBFSolver(self._device, self._particle_buffer)

        # Upload initial params with particle count
        self._params = self._params.with_update(particle_count=n)
        self._particle_buffer.update_params(self._params)

        self._time = 0.0
        self._state = SimState.RUNNING
        logger.info("Simulation initialized and running with PBF solver")

    def _upload_feature_textures(
        self, textures: dict[str, np.ndarray]
    ) -> None:
        """Upload edge_map and depth_map as GPU textures.

        Args:
            textures: Dict with "edge_map" and/or "depth_map" keys.
        """
        import wgpu

        for name in ("edge_map", "depth_map"):
            if name in textures:
                data = textures[name].astype(np.float32)
                h, w = data.shape[:2]
                texture = self._device.create_texture(
                    size=(w, h, 1),
                    format=wgpu.TextureFormat.r32float,
                    usage=(
                        wgpu.TextureUsage.TEXTURE_BINDING
                        | wgpu.TextureUsage.COPY_DST
                    ),
                )
                self._device.queue.write_texture(
                    {"texture": texture},
                    data.tobytes(),
                    {"bytes_per_row": w * 4, "rows_per_image": h},
                    (w, h, 1),
                )
                setattr(self, f"_{name}_texture", texture)
                logger.info("Uploaded %s texture: %dx%d", name, w, h)

    def _apply_feature_modulation(
        self,
        positions: np.ndarray,
        feature_textures: dict[str, np.ndarray],
    ) -> None:
        """Modulate home position strength based on feature textures.

        Particles on edges (high edge_map value) get tighter home attraction
        (w=1.5), while particles in flat areas drift more freely (w=0.5).

        Args:
            positions: (N, 3) float32 particle positions.
            feature_textures: Dict with "edge_map" and/or "depth_map".
        """
        if "edge_map" not in feature_textures:
            return

        edge_map = feature_textures["edge_map"].astype(np.float32)
        h, w = edge_map.shape[:2]
        n = positions.shape[0]

        # Compute UV coordinates from XY positions
        # Map position range to [0, 1] using bounding box
        pos_xy = positions[:, :2].copy()
        xy_min = pos_xy.min(axis=0)
        xy_max = pos_xy.max(axis=0)
        xy_range = xy_max - xy_min
        xy_range[xy_range < 1e-6] = 1.0  # prevent division by zero

        uv = (pos_xy - xy_min) / xy_range  # [0, 1]

        # Sample edge map at UV coordinates
        pixel_x = np.clip((uv[:, 0] * (w - 1)).astype(np.int32), 0, w - 1)
        pixel_y = np.clip((uv[:, 1] * (h - 1)).astype(np.int32), 0, h - 1)
        edge_values = edge_map[pixel_y, pixel_x]

        # Map edge values [0, 1] to feature_strength [0.5, 1.5]
        # High edge = tight hold (1.5), low edge = loose (0.5)
        feature_strength = 0.5 + edge_values * 1.0

        # Update home_positions.w with feature strength
        home = np.zeros((n, 4), dtype=np.float32)
        home[:, 0:3] = positions[:, :3].astype(np.float32)
        home[:, 3] = feature_strength
        self._device.queue.write_buffer(
            self._particle_buffer.home_positions_buffer, 0, home.tobytes()
        )
        logger.info(
            "Applied feature modulation: strength range [%.2f, %.2f]",
            feature_strength.min(),
            feature_strength.max(),
        )

    def set_attractors(
        self, attractors: list[tuple[np.ndarray, float]]
    ) -> None:
        """Set force attractor positions and weights from collection analysis.

        Creates a GPU buffer containing attractor data packed as vec4
        (x, y, z, weight) per attractor, padded to max_attractors.

        Args:
            attractors: List of (3D position, weight) tuples from
                CollectionAnalyzer.get_force_attractors().
        """
        import wgpu

        self._attractors = attractors[:self._max_attractors]

        # Pack attractor data as vec4 array (position.xyz + weight)
        data = np.zeros((self._max_attractors, 4), dtype=np.float32)
        for i, (pos, weight) in enumerate(self._attractors):
            data[i, :3] = pos
            data[i, 3] = weight

        # Create or update GPU buffer
        buffer_size = data.nbytes
        if self._attractor_buffer is None:
            self._attractor_buffer = self._device.create_buffer(
                size=buffer_size,
                usage=(
                    wgpu.BufferUsage.STORAGE
                    | wgpu.BufferUsage.COPY_DST
                ),
            )

        self._device.queue.write_buffer(
            self._attractor_buffer, 0, data.tobytes()
        )
        logger.info(
            "Set %d attractors (max %d)",
            len(self._attractors),
            self._max_attractors,
        )

    def clear_attractors(self) -> None:
        """Remove all force attractors."""
        self._attractors = []
        if self._attractor_buffer is not None:
            # Zero out the buffer
            data = np.zeros(
                (self._max_attractors, 4), dtype=np.float32
            )
            self._device.queue.write_buffer(
                self._attractor_buffer, 0, data.tobytes()
            )
        logger.info("Attractors cleared")

    def step(self) -> None:
        """Execute one simulation frame via PBF solver.

        Delegates to PBFSolver.step() which handles the full pipeline:
        predict, hash, density/correct loop, finalize, and buffer swap.
        """
        if self._state != SimState.RUNNING:
            return

        self._step_once()

    def _step_once(self) -> None:
        """Execute a single PBF simulation step.

        Pipeline:
        1. Update time and compute breathing modulation
        2. Update params with time, breathing_mod, and CFL-adaptive dt
        3. Delegate to PBFSolver.step()
        """
        # Update time
        self._time += self._params.dt

        # Compute breathing modulation
        breathing_mod = self._params.compute_breathing(self._time)

        # CFL-adaptive timestep
        # Use conservative fixed dt for initial implementation
        # The CFL mechanism adjusts dt based on max particle velocity
        dt_target = self._params.dt
        adaptive_dt = dt_target  # default to target

        # If we have a particle buffer, try CFL adaptation
        # For now use the target dt -- full CFL readback can be added
        # as an enhancement (read max_velocity from GPU, compute
        # dt = min(dt_target, CFL_COEFF * h / max(v_max, 0.001)))
        adaptive_dt = min(
            dt_target,
            _CFL_COEFF * self._params.kernel_radius / max(self._params.max_velocity * 0.1, 0.001),
        )
        # Clamp to reasonable range
        adaptive_dt = max(adaptive_dt, dt_target * 0.1)
        adaptive_dt = min(adaptive_dt, dt_target)

        # Update params with runtime values
        updated_params = self._params.with_update(
            time=self._time,
            breathing_mod=breathing_mod,
            dt=adaptive_dt,
            particle_count=self._particle_buffer.particle_count,
        )

        # Delegate to PBF solver
        self._pbf_solver.step(updated_params)

    def get_positions_buffer(self):
        """Return current output buffer for rendering (NO CPU readback).

        Returns:
            wgpu.GPUBuffer containing particle state (position + velocity).
        """
        if self._particle_buffer is None:
            return None
        return self._particle_buffer.output_buffer

    def get_colors_buffer(self):
        """Return color buffer for rendering.

        Returns:
            wgpu.GPUBuffer containing RGBA colors per particle.
        """
        if self._particle_buffer is None:
            return None
        return self._particle_buffer.color_buffer

    def update_visual_param(self, name: str, value) -> None:
        """Hot-reload a visual parameter (no simulation restart).

        Args:
            name: Parameter name (must be a visual param).
            value: New parameter value.
        """
        if not SimulationParams.is_visual_param(name):
            logger.warning(
                "update_visual_param called with non-visual param: %s", name
            )
        self._params = self._params.with_update(**{name: value})
        if self._particle_buffer is not None:
            self._particle_buffer.update_params(self._params)

    def update_physics_param(self, name: str, value) -> None:
        """Update a physics parameter (triggers simulation restart).

        Args:
            name: Parameter name (must be a physics param).
            value: New parameter value.
        """
        if not SimulationParams.is_physics_param(name):
            logger.warning(
                "update_physics_param called with non-physics param: %s", name
            )
        self._params = self._params.with_update(**{name: value})
        self.restart()

    def restart(self) -> None:
        """Reset to initial positions with current parameters."""
        if self._initial_positions is None:
            logger.warning("Cannot restart: no initial state")
            return

        from apollo7.simulation.pbf_solver import PBFSolver

        logger.info("Restarting simulation")
        self._particle_buffer.upload(
            self._initial_positions, self._initial_colors
        )
        self._particle_buffer.update_params(self._params)

        # Rebuild PBF solver for clean state
        self._pbf_solver = PBFSolver(self._device, self._particle_buffer)

        self._time = 0.0
        self._state = SimState.RUNNING

    def pause(self) -> None:
        """Pause the simulation loop."""
        if self._state == SimState.RUNNING:
            self._state = SimState.PAUSED
            logger.info("Simulation paused")

    def resume(self) -> None:
        """Resume the simulation loop."""
        if self._state == SimState.PAUSED:
            self._state = SimState.RUNNING
            logger.info("Simulation resumed")

    def toggle_pause(self) -> None:
        """Toggle between paused and running states."""
        if self._state == SimState.RUNNING:
            self.pause()
        elif self._state == SimState.PAUSED:
            self.resume()

    @property
    def running(self) -> bool:
        """Whether the simulation is actively running."""
        return self._state == SimState.RUNNING

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        return self._state == SimState.PAUSED

    @property
    def state(self) -> SimState:
        """Current simulation state."""
        return self._state

    @property
    def particle_count(self) -> int:
        """Number of active particles."""
        if self._particle_buffer is None:
            return 0
        return self._particle_buffer.particle_count

    @property
    def params(self) -> SimulationParams:
        """Current simulation parameters."""
        return self._params
