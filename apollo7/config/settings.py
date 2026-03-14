"""Default application settings for Apollo 7.

All values are module-level constants that serve as defaults.
"""

# -- Point rendering defaults --
POINT_SIZE_DEFAULT: float = 2.0
POINT_SIZE_RANGE: tuple[float, float] = (0.5, 10.0)
OPACITY_DEFAULT: float = 1.0
OPACITY_RANGE: tuple[float, float] = (0.0, 1.0)

# -- Depth projection --
DEPTH_EXAGGERATION_DEFAULT: float = 4.0
DEPTH_EXAGGERATION_RANGE: tuple[float, float] = (1.0, 10.0)

# -- Background colors (dark gradient) --
BG_COLOR_TOP: str = "#1a1a1a"
BG_COLOR_BOTTOM: str = "#0a0a0a"

# -- Accent color --
ACCENT_COLOR: str = "#0078FF"

# -- Viewport performance --
VIEWPORT_MIN_FPS: int = 30

# -- LOD thresholds (distance in scene units) --
LOD_FULL_DISTANCE: float = 5.0       # Full resolution within this distance
LOD_MEDIUM_DISTANCE: float = 20.0    # 50% decimation between full and medium
LOD_LOW_DISTANCE: float = 50.0       # 10% decimation beyond medium
LOD_POINT_BUDGET: int = 5_000_000    # Max visible points at any time

# -- Window dimensions --
WINDOW_SIZE: tuple[int, int] = (1920, 1080)
MIN_WINDOW_SIZE: tuple[int, int] = (1280, 720)
