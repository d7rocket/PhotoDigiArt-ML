"""GPU-accelerated particle simulation engine.

Orchestrates compute shader pipelines for flow field, forces, SPH,
and integration passes. Manages simulation lifecycle (init, step,
pause, restart) and provides GPU buffer access for rendering.

Designed for 1-5M particles with chunked dispatch for AMD TDR prevention.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import replace

import numpy as np

from apollo7.simulation.buffers import ParticleBuffer
from apollo7.simulation.parameters import SimulationParams
from apollo7.simulation.shaders import build_combined_shader, load_shader

logger = logging.getLogger(__name__)

# Maximum particles per compute dispatch (AMD TDR prevention)
_CHUNK_SIZE = 256 * 1024  # 256K particles
_WORKGROUP_SIZE = 256


class SimState(enum.Enum):
    """Simulation lifecycle states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationEngine:
    """Orchestrates GPU compute pipelines for particle simulation.

    Lifecycle: IDLE -> initialize() -> RUNNING -> pause() -> PAUSED
    -> resume() -> RUNNING -> restart() -> RUNNING

    The engine manages:
    - Double-buffered particle state (ParticleBuffer)
    - Compute pipelines for each simulation pass
    - Feature texture upload and binding
    - Chunked dispatch for AMD TDR prevention
    - Visual param hot-reload vs physics param restart
    """

    def __init__(self, device):
        """Create simulation engine with the given wgpu device.

        Args:
            device: wgpu.GPUDevice for buffer and pipeline creation.
        """
        import wgpu

        self._device = device
        self._state = SimState.IDLE
        self._params = SimulationParams()
        self._particle_buffer: ParticleBuffer | None = None
        self._initial_positions: np.ndarray | None = None
        self._initial_colors: np.ndarray | None = None
        self._time: float = 0.0
        self._sim_steps_per_frame: int = 1
        self._performance_mode: bool = False
        self._has_feature_textures: bool = False

        # Compute pipelines (created during initialize)
        self._integrate_pipeline = None
        self._integrate_bind_group = None

        logger.info("SimulationEngine created")

    def initialize(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        feature_textures: dict[str, np.ndarray] | None = None,
    ) -> None:
        """Upload initial point cloud state and set up compute pipelines.

        Args:
            positions: (N, 3) float32 array of XYZ positions.
            colors: (N, 4) float32 array of RGBA colors.
            feature_textures: Optional dict of feature maps.
                Keys: "edge_map", "depth_map" with (H, W) float32 arrays.
        """
        import wgpu

        n = positions.shape[0]
        logger.info("Initializing simulation with %d particles", n)

        # Store initial state for restart
        self._initial_positions = positions.copy()
        self._initial_colors = colors.copy()

        # Create particle buffer
        self._particle_buffer = ParticleBuffer(self._device, max_particles=n)
        self._particle_buffer.upload(positions, colors)

        # Upload feature textures if provided (stored for future multi-pass use)
        if feature_textures:
            self._upload_feature_textures(feature_textures)
            self._has_feature_textures = True
        else:
            self._has_feature_textures = False

        # Build compute pipeline (single-pass: forces computed inline in shader)
        self._build_integrate_pipeline()

        # Upload initial params
        self._particle_buffer.update_params(self._params)

        self._time = 0.0
        self._state = SimState.RUNNING
        logger.info("Simulation initialized and running")

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

    def _build_integrate_pipeline(self) -> None:
        """Build the integration compute pipeline.

        Single-pass pipeline: forces (flow field, gravity, wind) are computed
        inline in the shader. No separate force accumulation buffer needed.
        """
        import wgpu

        shader_source = load_shader("integrate")
        shader_module = self._device.create_shader_module(code=shader_source)

        # Bind group layout: particles_in, particles_out, params
        bgl = self._device.create_bind_group_layout(
            entries=[
                {
                    "binding": 0,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {
                        "type": wgpu.BufferBindingType.read_only_storage
                    },
                },
                {
                    "binding": 1,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {"type": wgpu.BufferBindingType.storage},
                },
                {
                    "binding": 2,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {"type": wgpu.BufferBindingType.uniform},
                },
            ],
        )

        pipeline_layout = self._device.create_pipeline_layout(
            bind_group_layouts=[bgl]
        )
        self._integrate_pipeline = self._device.create_compute_pipeline(
            layout=pipeline_layout,
            compute={"module": shader_module, "entry_point": "integrate"},
        )

        # Create bind group (will be recreated on buffer swap)
        self._integrate_bgl = bgl
        self._rebuild_integrate_bind_group()

    def _rebuild_integrate_bind_group(self) -> None:
        """Rebuild bind group after buffer swap."""
        pb = self._particle_buffer
        self._integrate_bind_group = self._device.create_bind_group(
            layout=self._integrate_bgl,
            entries=[
                {
                    "binding": 0,
                    "resource": {
                        "buffer": pb.input_buffer,
                        "offset": 0,
                        "size": pb.input_buffer.size,
                    },
                },
                {
                    "binding": 1,
                    "resource": {
                        "buffer": pb.output_buffer,
                        "offset": 0,
                        "size": pb.output_buffer.size,
                    },
                },
                {
                    "binding": 2,
                    "resource": {
                        "buffer": pb.params_buffer,
                        "offset": 0,
                        "size": pb.params_buffer.size,
                    },
                },
            ],
        )

    def step(self) -> None:
        """Execute one simulation frame (all compute passes).

        Dispatches compute shaders in chunked fashion to prevent AMD TDR.
        After all passes, swaps particle buffers.
        """
        if self._state != SimState.RUNNING:
            return

        for _ in range(self._sim_steps_per_frame):
            self._step_once()

    def _step_once(self) -> None:
        """Execute a single simulation step."""
        # Update time
        self._time += self._params.dt
        updated_params = self._params.with_update(
            time=self._time,
            sph_enabled=0.0 if self._performance_mode else 1.0,
            performance_mode=1.0 if self._performance_mode else 0.0,
        )
        self._particle_buffer.update_params(updated_params)

        n = self._particle_buffer.particle_count

        # Rebuild bind group for current buffer orientation
        self._rebuild_integrate_bind_group()

        # Dispatch integration pass (chunked)
        encoder = self._device.create_command_encoder()
        compute_pass = encoder.begin_compute_pass()
        self._dispatch_chunked(
            compute_pass,
            self._integrate_pipeline,
            self._integrate_bind_group,
            n,
        )
        compute_pass.end()
        self._device.queue.submit([encoder.finish()])

        # Swap buffers
        self._particle_buffer.swap()

    def _dispatch_chunked(
        self, pass_encoder, pipeline, bind_group, total_particles: int
    ) -> None:
        """Dispatch compute shader in chunks to prevent AMD TDR timeout.

        Args:
            pass_encoder: Active compute pass encoder.
            pipeline: Compute pipeline to dispatch.
            bind_group: Bind group for the pipeline.
            total_particles: Total number of particles to process.
        """
        pass_encoder.set_pipeline(pipeline)
        pass_encoder.set_bind_group(0, bind_group)

        for offset in range(0, total_particles, _CHUNK_SIZE):
            count = min(_CHUNK_SIZE, total_particles - offset)
            workgroups = (count + _WORKGROUP_SIZE - 1) // _WORKGROUP_SIZE
            pass_encoder.dispatch_workgroups(workgroups)

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

        logger.info("Restarting simulation")
        self._particle_buffer.upload(
            self._initial_positions, self._initial_colors
        )
        self._particle_buffer.update_params(self._params)
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

    def set_performance_mode(self, enabled: bool) -> None:
        """Toggle performance mode (skips SPH pass).

        Args:
            enabled: True to enable performance mode.
        """
        self._performance_mode = enabled
        logger.info("Performance mode: %s", "ON" if enabled else "OFF")

    def set_sim_steps_per_frame(self, n: int) -> None:
        """Set number of simulation steps per frame.

        Args:
            n: Steps per frame (default 1). Higher = faster sim, lower FPS.
        """
        self._sim_steps_per_frame = max(1, n)

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
