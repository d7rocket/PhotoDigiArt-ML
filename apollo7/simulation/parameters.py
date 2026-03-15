"""Simulation parameters dataclass with WGSL-aligned uniform packing.

All tunable simulation parameters are stored here. Parameters are
categorized as visual (hot-reload) or physics (requires sim restart).
The to_uniform_bytes() method packs values into a flat buffer matching
the WGSL SimParams struct layout with vec4 alignment throughout.

PBF (Position Based Fluids) replaces the former SPH solver. All params
are hot-reloadable -- the compute shader reads the uniform buffer each
frame, so no restart is needed for any parameter change.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field, fields


@dataclass
class SimulationParams:
    """All tunable parameters for the PBF particle simulation.

    WGSL uniform layout (vec4-aligned, 16-byte boundaries):
      vec4 0: noise_frequency, noise_amplitude, noise_octaves(f32), turbulence_scale
      vec4 1: home_strength, breathing_rate, breathing_amplitude, breathing_mod
      vec4 2: kernel_radius, rest_density, epsilon_pbf, solver_iterations(f32)
      vec4 3: artificial_pressure_k, artificial_pressure_n(f32), delta_q, xsph_c
      vec4 4: vorticity_epsilon, max_force, max_velocity, dt
      vec4 5: gravity.xyz, damping
      vec4 6: wind.xyz, speed
      vec4 7: time, cell_size(=kernel_radius), particle_count(f32), _pad
    Total: 8 * 16 = 128 bytes
    """

    # -- Noise / flow field --
    noise_frequency: float = 0.5
    noise_amplitude: float = 1.0
    noise_octaves: int = 4
    turbulence_scale: float = 1.0

    # -- Home attraction / breathing --
    home_strength: float = 5.0
    breathing_rate: float = 0.2
    breathing_amplitude: float = 0.15

    # -- PBF solver core --
    kernel_radius: float = 0.1
    rest_density: float = 6378.0
    epsilon_pbf: float = 600.0
    solver_iterations: int = 2

    # -- Artificial pressure / XSPH --
    artificial_pressure_k: float = 0.0001
    artificial_pressure_n: int = 4
    delta_q: float = 0.03
    xsph_c: float = 0.01

    # -- Stability / clamping --
    vorticity_epsilon: float = 0.01
    max_force: float = 50.0
    max_velocity: float = 10.0

    # -- Integration --
    speed: float = 1.0
    dt: float = 0.016
    damping: float = 0.99

    # -- Directional forces (stored as 3-tuples) --
    gravity: tuple[float, float, float] = (0.0, -0.1, 0.0)
    wind: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # -- Runtime state (not user-tunable, but part of uniform) --
    time: float = 0.0
    breathing_mod: float = 1.0
    particle_count: int = 0

    # Category sets for hot-reload vs restart classification
    # All params are visual (hot-reload) -- the compute shader reads
    # everything from the uniform buffer each frame, no restart needed.
    _visual_params: set[str] = field(
        default_factory=lambda: {
            "noise_frequency",
            "noise_amplitude",
            "noise_octaves",
            "turbulence_scale",
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
            "speed",
            "damping",
            "gravity",
            "wind",
        },
        repr=False,
        compare=False,
    )

    _physics_params: set[str] = field(
        default_factory=lambda: set(),
        repr=False,
        compare=False,
    )

    # Uniform byte count (must be multiple of 16)
    UNIFORM_SIZE: int = field(default=128, repr=False, compare=False)

    def to_uniform_bytes(self) -> bytes:
        """Pack parameters into a flat float32 buffer matching WGSL layout.

        Layout (8 x vec4 = 128 bytes):
          [0..15]    noise_frequency, noise_amplitude, float(noise_octaves), turbulence_scale
          [16..31]   home_strength, breathing_rate, breathing_amplitude, breathing_mod
          [32..47]   kernel_radius, rest_density, epsilon_pbf, float(solver_iterations)
          [48..63]   artificial_pressure_k, float(artificial_pressure_n), delta_q, xsph_c
          [64..79]   vorticity_epsilon, max_force, max_velocity, dt
          [80..95]   gravity.x, gravity.y, gravity.z, damping
          [96..111]  wind.x, wind.y, wind.z, speed
          [112..127] time, cell_size(=kernel_radius), float(particle_count), 0.0

        Returns:
            bytes of length UNIFORM_SIZE (128).
        """
        values = [
            # vec4 0: noise
            self.noise_frequency,
            self.noise_amplitude,
            float(self.noise_octaves),
            self.turbulence_scale,
            # vec4 1: home / breathing
            self.home_strength,
            self.breathing_rate,
            self.breathing_amplitude,
            self.breathing_mod,
            # vec4 2: PBF solver core
            self.kernel_radius,
            self.rest_density,
            self.epsilon_pbf,
            float(self.solver_iterations),
            # vec4 3: artificial pressure / XSPH
            self.artificial_pressure_k,
            float(self.artificial_pressure_n),
            self.delta_q,
            self.xsph_c,
            # vec4 4: stability
            self.vorticity_epsilon,
            self.max_force,
            self.max_velocity,
            self.dt,
            # vec4 5: gravity + damping
            self.gravity[0],
            self.gravity[1],
            self.gravity[2],
            self.damping,
            # vec4 6: wind + speed
            self.wind[0],
            self.wind[1],
            self.wind[2],
            self.speed,
            # vec4 7: runtime
            self.time,
            self.kernel_radius,  # cell_size = kernel_radius
            float(self.particle_count),
            0.0,  # padding
        ]
        return struct.pack(f"<{len(values)}f", *values)

    def compute_breathing(self, time: float) -> float:
        """Compute breathing modulation factor for the given time.

        Returns a value oscillating around 1.0 with amplitude
        breathing_amplitude and frequency breathing_rate Hz.

        Args:
            time: Current simulation time in seconds.

        Returns:
            Modulation factor, e.g. 1.0 + 0.15 * sin(2*pi*0.2*t)
            giving range [0.85, 1.15] for default params.
        """
        return 1.0 + self.breathing_amplitude * math.sin(
            2.0 * math.pi * self.breathing_rate * time
        )

    @classmethod
    def is_visual_param(cls, name: str) -> bool:
        """Check if a parameter supports hot-reload (no sim restart).

        All params are visual -- the compute shader reads everything
        from the uniform buffer each frame.
        """
        return name in {
            "noise_frequency",
            "noise_amplitude",
            "noise_octaves",
            "turbulence_scale",
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
            "speed",
            "damping",
            "gravity",
            "wind",
        }

    @classmethod
    def is_physics_param(cls, name: str) -> bool:
        """Check if a parameter requires simulation restart."""
        return False

    def with_update(self, **kwargs) -> SimulationParams:
        """Return a new SimulationParams with updated values.

        This creates a copy with the specified fields changed,
        leaving the original immutable.
        """
        current = {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if not f.name.startswith("_") and f.name != "UNIFORM_SIZE"
        }
        current.update(kwargs)
        return SimulationParams(**current)
