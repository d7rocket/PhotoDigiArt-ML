"""Simulation parameters dataclass with WGSL-aligned uniform packing.

All tunable simulation parameters are stored here. Parameters are
categorized as visual (hot-reload) or physics (requires sim restart).
The to_uniform_bytes() method packs values into a flat buffer matching
the WGSL SimParams struct layout with vec4 alignment throughout.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field, fields


@dataclass
class SimulationParams:
    """All tunable parameters for the particle simulation.

    WGSL uniform layout (vec4-aligned, 16-byte boundaries):
      vec4: noise_frequency, noise_amplitude, noise_octaves(u32->f32), turbulence_scale
      vec4: viscosity, pressure_strength, surface_tension, attraction_strength
      vec4: repulsion_strength, repulsion_radius, smoothing_radius, rest_density
      vec4: gas_constant, speed, dt, damping
      vec4: gravity.xyz, _pad0
      vec4: wind.xyz, _pad1
      vec4: time, sph_enabled, performance_mode, attractor_global_strength
    Total: 7 * 16 = 112 bytes
    """

    # -- Noise / flow field --
    noise_frequency: float = 0.5
    noise_amplitude: float = 1.0
    noise_octaves: int = 4
    turbulence_scale: float = 1.0

    # -- SPH fluid dynamics --
    viscosity: float = 0.1
    pressure_strength: float = 1.0
    surface_tension: float = 0.01
    attraction_strength: float = 0.5

    # -- Attraction / repulsion --
    repulsion_strength: float = 0.3
    repulsion_radius: float = 0.1
    smoothing_radius: float = 0.1
    rest_density: float = 1000.0

    # -- Integration --
    gas_constant: float = 2.0
    speed: float = 1.0
    dt: float = 0.016
    damping: float = 0.99

    # -- Directional forces (stored as 3-tuples) --
    gravity: tuple[float, float, float] = (0.0, -0.1, 0.0)
    wind: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # -- Collection attractors --
    attractor_global_strength: float = 0.5

    # -- Runtime state (not user-tunable, but part of uniform) --
    time: float = 0.0
    sph_enabled: float = 1.0
    performance_mode: float = 0.0

    # Category sets for hot-reload vs restart classification
    # All params are visual (hot-reload) for now — the single-pass shader
    # reads everything from the uniform buffer each frame, so no restart needed.
    _visual_params: set[str] = field(
        default_factory=lambda: {
            "noise_frequency",
            "noise_amplitude",
            "noise_octaves",
            "turbulence_scale",
            "speed",
            "damping",
            "gravity",
            "wind",
            "viscosity",
            "pressure_strength",
            "surface_tension",
            "attraction_strength",
            "repulsion_strength",
            "repulsion_radius",
            "smoothing_radius",
            "rest_density",
            "gas_constant",
            "attractor_global_strength",
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
    UNIFORM_SIZE: int = field(default=112, repr=False, compare=False)

    def to_uniform_bytes(self) -> bytes:
        """Pack parameters into a flat float32 buffer matching WGSL layout.

        Layout (7 x vec4 = 112 bytes):
          [0..15]   noise_frequency, noise_amplitude, float(noise_octaves), turbulence_scale
          [16..31]  viscosity, pressure_strength, surface_tension, attraction_strength
          [32..47]  repulsion_strength, repulsion_radius, smoothing_radius, rest_density
          [48..63]  gas_constant, speed, dt, damping
          [64..79]  gravity.x, gravity.y, gravity.z, 0.0
          [80..95]  wind.x, wind.y, wind.z, 0.0
          [96..111] time, sph_enabled, performance_mode, attractor_global_strength

        Returns:
            bytes of length UNIFORM_SIZE (112).
        """
        values = [
            # vec4 0
            self.noise_frequency,
            self.noise_amplitude,
            float(self.noise_octaves),
            self.turbulence_scale,
            # vec4 1
            self.viscosity,
            self.pressure_strength,
            self.surface_tension,
            self.attraction_strength,
            # vec4 2
            self.repulsion_strength,
            self.repulsion_radius,
            self.smoothing_radius,
            self.rest_density,
            # vec4 3
            self.gas_constant,
            self.speed,
            self.dt,
            self.damping,
            # vec4 4: gravity + pad
            self.gravity[0],
            self.gravity[1],
            self.gravity[2],
            0.0,
            # vec4 5: wind + pad
            self.wind[0],
            self.wind[1],
            self.wind[2],
            0.0,
            # vec4 6: runtime state + attractor strength
            self.time,
            self.sph_enabled,
            self.performance_mode,
            self.attractor_global_strength,
        ]
        return struct.pack(f"<{len(values)}f", *values)

    @classmethod
    def is_visual_param(cls, name: str) -> bool:
        """Check if a parameter supports hot-reload (no sim restart).

        All params are visual for now — the single-pass shader reads
        everything from the uniform buffer each frame.
        """
        return name in {
            "noise_frequency",
            "noise_amplitude",
            "noise_octaves",
            "turbulence_scale",
            "speed",
            "damping",
            "gravity",
            "wind",
            "viscosity",
            "pressure_strength",
            "surface_tension",
            "attraction_strength",
            "repulsion_strength",
            "repulsion_radius",
            "smoothing_radius",
            "rest_density",
            "gas_constant",
            "attractor_global_strength",
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
