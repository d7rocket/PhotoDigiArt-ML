"""Pydantic models for Claude structured outputs.

Defines bounded parameter models that Claude returns via messages.parse().
All fields have min/max constraints matching the simulation engine ranges
defined in apollo7/config/settings.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SculptureParams(BaseModel):
    """Claude-suggested sculpture parameters with bounded ranges.

    Each field maps to a simulation or rendering parameter. Pydantic
    validators enforce the same bounds as the UI sliders, so Claude
    cannot produce out-of-range values.
    """

    rationale: str = Field(
        description="2-3 sentence artistic rationale explaining why "
        "these parameters suit the photo"
    )
    solver_iterations: int = Field(
        ge=1, le=6,
        description="Cohesion: 1=ethereal gas, 6=dense liquid",
    )
    home_strength: float = Field(
        ge=0.1, le=20.0,
        description="How tightly particles hold their sculptural form",
    )
    noise_amplitude: float = Field(
        ge=0.0, le=5.0,
        description="Flow intensity: organic motion strength",
    )
    breathing_rate: float = Field(
        ge=0.05, le=0.5,
        description="Breathing animation speed",
    )
    point_size: float = Field(
        ge=0.5, le=10.0,
        description="Particle visual size",
    )
    opacity: float = Field(
        ge=0.0, le=1.0,
        description="Particle transparency",
    )

    def clamp_to_bounds(self) -> SculptureParams:
        """Return a copy with all values clamped to valid ranges.

        Defense-in-depth: even though Pydantic validates on construction,
        this ensures safety if values are mutated or deserialized loosely.
        """
        return SculptureParams(
            rationale=self.rationale,
            solver_iterations=max(1, min(6, self.solver_iterations)),
            home_strength=max(0.1, min(20.0, self.home_strength)),
            noise_amplitude=max(0.0, min(5.0, self.noise_amplitude)),
            breathing_rate=max(0.05, min(0.5, self.breathing_rate)),
            point_size=max(0.5, min(10.0, self.point_size)),
            opacity=max(0.0, min(1.0, self.opacity)),
        )

    def to_param_dict(self) -> dict[str, float]:
        """Convert to parameter dict compatible with CrossfadeEngine/preset format.

        Returns keys matching simulation engine parameter names so the
        dict can be passed directly to CrossfadeEngine.crossfade_to().
        """
        return {
            "solver_iterations": float(self.solver_iterations),
            "home_strength": self.home_strength,
            "noise_amplitude": self.noise_amplitude,
            "breathing_rate": self.breathing_rate,
            "point_size": self.point_size,
            "opacity": self.opacity,
        }
