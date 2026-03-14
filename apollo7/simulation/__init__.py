"""GPU-accelerated particle simulation engine.

Provides compute-shader-based particle simulation with Perlin flow fields,
attraction/repulsion forces, SPH fluid dynamics, and gravity/wind.
All simulation runs on GPU via wgpu compute shaders (WGSL).
"""

from apollo7.simulation.parameters import SimulationParams
from apollo7.simulation.buffers import ParticleBuffer
from apollo7.simulation.engine import SimulationEngine

__all__ = ["SimulationParams", "ParticleBuffer", "SimulationEngine"]
