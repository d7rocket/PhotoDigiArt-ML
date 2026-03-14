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

# -- Simulation parameter ranges and defaults --

# Simulation Control section
SIM_SPEED_RANGE: tuple[float, float] = (0.1, 5.0)
SIM_SPEED_DEFAULT: float = 1.0
SIM_TURBULENCE_RANGE: tuple[float, float] = (0.0, 3.0)
SIM_TURBULENCE_DEFAULT: float = 1.0

# Flow Field section
SIM_NOISE_FREQ_RANGE: tuple[float, float] = (0.1, 5.0)
SIM_NOISE_FREQ_DEFAULT: float = 0.5
SIM_NOISE_AMP_RANGE: tuple[float, float] = (0.0, 3.0)
SIM_NOISE_AMP_DEFAULT: float = 1.0
SIM_NOISE_OCTAVES_RANGE: tuple[int, int] = (1, 8)
SIM_NOISE_OCTAVES_DEFAULT: int = 4

# Forces section
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

# Fluid (SPH) section
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
BLOOM_STRENGTH_DEFAULT: float = 0.04
BLOOM_STRENGTH_RANGE: tuple[float, float] = (0.0, 3.0)

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
