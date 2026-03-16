"""Default application settings for Apollo 7.

All values are module-level constants that serve as defaults.
"""

import json
import os
from pathlib import Path

# -- Point rendering defaults --
POINT_SIZE_DEFAULT: float = 2.0
POINT_SIZE_RANGE: tuple[float, float] = (0.5, 10.0)
OPACITY_DEFAULT: float = 1.0
OPACITY_RANGE: tuple[float, float] = (0.0, 1.0)

# -- Depth projection --
DEPTH_EXAGGERATION_DEFAULT: float = 4.0
DEPTH_EXAGGERATION_RANGE: tuple[float, float] = (1.0, 10.0)

# -- Background colors (warm off-white gallery paper) --
BG_COLOR_TOP: str = "#F8F6F3"
BG_COLOR_BOTTOM: str = "#F5F3F0"

# -- Accent color --
ACCENT_COLOR: str = "#0078FF"

# -- Viewport performance --
VIEWPORT_MIN_FPS: int = 30

# -- LOD thresholds (distance in scene units) --
LOD_FULL_DISTANCE: float = 5.0       # Full resolution within this distance
LOD_MEDIUM_DISTANCE: float = 20.0    # 50% decimation between full and medium
LOD_LOW_DISTANCE: float = 50.0       # 10% decimation beyond medium
LOD_POINT_BUDGET: int = 5_000_000    # Max visible points at any time

# -- Simulation parameter ranges and defaults --

# PBF Essential Controls (visible by default)
SIM_COHESION_RANGE: tuple[int, int] = (1, 6)
SIM_COHESION_DEFAULT: int = 2
SIM_HOME_STRENGTH_RANGE: tuple[float, float] = (0.1, 20.0)
SIM_HOME_STRENGTH_DEFAULT: float = 5.0
SIM_FLOW_INTENSITY_RANGE: tuple[float, float] = (0.0, 5.0)
SIM_FLOW_INTENSITY_DEFAULT: float = 1.0
SIM_BREATHING_RATE_RANGE: tuple[float, float] = (0.05, 0.5)
SIM_BREATHING_RATE_DEFAULT: float = 0.2

# PBF Advanced Controls (collapsed section)
SIM_FLOW_SCALE_RANGE: tuple[float, float] = (0.05, 2.0)
SIM_FLOW_SCALE_DEFAULT: float = 0.5
SIM_SWIRL_RANGE: tuple[float, float] = (0.0, 0.1)
SIM_SWIRL_DEFAULT: float = 0.01
SIM_SMOOTHING_RANGE: tuple[float, float] = (0.0, 0.05)
SIM_SMOOTHING_DEFAULT: float = 0.01
SIM_DAMPING_RANGE: tuple[float, float] = (0.9, 1.0)
SIM_DAMPING_DEFAULT: float = 0.99
SIM_BREATHING_DEPTH_RANGE: tuple[float, float] = (0.0, 0.3)
SIM_BREATHING_DEPTH_DEFAULT: float = 0.15

# Legacy constants kept for backward compatibility with imports
SIM_SPEED_RANGE: tuple[float, float] = (0.1, 5.0)
SIM_SPEED_DEFAULT: float = 1.0
SIM_TURBULENCE_RANGE: tuple[float, float] = (0.0, 3.0)
SIM_TURBULENCE_DEFAULT: float = 1.0
SIM_NOISE_FREQ_RANGE: tuple[float, float] = (0.1, 5.0)
SIM_NOISE_FREQ_DEFAULT: float = 0.5
SIM_NOISE_AMP_RANGE: tuple[float, float] = (0.0, 3.0)
SIM_NOISE_AMP_DEFAULT: float = 1.0
SIM_NOISE_OCTAVES_RANGE: tuple[int, int] = (1, 8)
SIM_NOISE_OCTAVES_DEFAULT: int = 4
SIM_ATTRACTION_RANGE: tuple[float, float] = (0.0, 2.0)
SIM_ATTRACTION_DEFAULT: float = 0.5
SIM_REPULSION_RANGE: tuple[float, float] = (0.0, 2.0)
SIM_REPULSION_DEFAULT: float = 0.3
SIM_REPULSION_RADIUS_RANGE: tuple[float, float] = (0.01, 0.5)
SIM_REPULSION_RADIUS_DEFAULT: float = 0.1
SIM_GRAVITY_Y_RANGE: tuple[float, float] = (-1.0, 1.0)
SIM_GRAVITY_Y_DEFAULT: float = -0.1
SIM_WIND_RANGE: tuple[float, float] = (-1.0, 1.0)
SIM_WIND_DEFAULT: float = 0.0
SIM_VISCOSITY_RANGE: tuple[float, float] = (0.0, 1.0)
SIM_VISCOSITY_DEFAULT: float = 0.1
SIM_PRESSURE_RANGE: tuple[float, float] = (0.0, 5.0)
SIM_PRESSURE_DEFAULT: float = 1.0
SIM_SURFACE_TENSION_RANGE: tuple[float, float] = (0.0, 0.1)
SIM_SURFACE_TENSION_DEFAULT: float = 0.01

# -- Window dimensions --
WINDOW_SIZE: tuple[int, int] = (1920, 1080)
MIN_WINDOW_SIZE: tuple[int, int] = (1280, 720)

# -- Post-processing: Bloom --
BLOOM_STRENGTH_DEFAULT: float = 0.3
BLOOM_STRENGTH_RANGE: tuple[float, float] = (0.0, 3.0)
BLOOM_FILTER_RADIUS: float = 0.015

# -- Post-processing: Depth of Field --
DOF_FOCAL_DEFAULT: float = 10.0
DOF_FOCAL_RANGE: tuple[float, float] = (0.0, 50.0)
DOF_APERTURE_DEFAULT: float = 2.0
DOF_APERTURE_RANGE: tuple[float, float] = (0.1, 5.0)

# -- Post-processing: Ambient Occlusion --
SSAO_RADIUS_DEFAULT: float = 0.5
SSAO_RADIUS_RANGE: tuple[float, float] = (0.1, 2.0)
SSAO_INTENSITY_DEFAULT: float = 1.0
SSAO_INTENSITY_RANGE: tuple[float, float] = (0.0, 2.0)

# -- Post-processing: Motion Trails --
TRAIL_LENGTH_DEFAULT: float = 0.5
TRAIL_LENGTH_RANGE: tuple[float, float] = (0.0, 1.0)

# -- Project file --
PROJECT_FILE_EXTENSION: str = ".apollo7"
DEFAULT_PRESETS_DIR: str = "~/.apollo7/presets/"

# -- Export resolution presets --
EXPORT_MAX_RESOLUTION: int = 15360

# -- Claude API enrichment (optional, offline-first) --
ENRICHMENT_ENABLED: bool = False
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

# -- Config file management --
_CONFIG_DIR = Path.home() / ".apollo7"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def load_api_key() -> str | None:
    """Load Anthropic API key from environment or config file.

    Priority:
      1. APOLLO7_CLAUDE_API_KEY environment variable
      2. ~/.apollo7/config.json anthropic_api_key field

    Returns:
        API key string, or None if not configured.
    """
    env_key = os.environ.get("APOLLO7_CLAUDE_API_KEY")
    if env_key:
        return env_key
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            return data.get("anthropic_api_key")
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_api_key(key: str) -> None:
    """Save Anthropic API key to ~/.apollo7/config.json.

    Creates the config directory if it doesn't exist. Preserves
    existing config values. Sets restrictive file permissions
    (best effort on Windows).
    """
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if _CONFIG_FILE.exists():
        try:
            config = json.loads(_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    config["anthropic_api_key"] = key
    _CONFIG_FILE.write_text(json.dumps(config, indent=2))
    # Restrictive permissions (best effort on Windows)
    try:
        _CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


CLAUDE_API_KEY: str | None = load_api_key()
