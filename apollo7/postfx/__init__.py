"""Post-processing effects for Apollo 7 viewport.

Provides bloom, depth of field, SSAO, and motion trails effects
that enhance visual quality of particle renders.
"""

from apollo7.postfx.bloom import BloomController
from apollo7.postfx.dof_pass import DepthOfFieldPass
from apollo7.postfx.ssao_pass import SSAOPass
from apollo7.postfx.trails import TrailAccumulator

__all__ = [
    "BloomController",
    "DepthOfFieldPass",
    "SSAOPass",
    "TrailAccumulator",
]
