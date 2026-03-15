# Phase 5: Visual Quality - Research

**Researched:** 2026-03-15
**Domain:** GPU rendering quality, post-processing, depth enhancement, parameter animation
**Confidence:** HIGH

## Summary

Phase 5 transforms Apollo 7 from functional to gallery-worthy. The work spans five distinct domains: (1) luminous particle aesthetics via alpha blending and bloom retuning on white background, (2) GPU buffer sharing to eliminate the CPU readback bottleneck at 1M+ particles, (3) a unified crossfade engine for smooth parameter transitions, (4) CLAHE-enhanced depth maps for continuous 3D volume, and (5) per-pixel color sampling with saturation boost for vibrant sculptures.

The existing codebase provides strong foundations: `PointsGaussianBlobMaterial` already renders soft Gaussian blobs, `BloomController` wraps pygfx's `PhysicalBasedBloomPass`, and the `ParticleBuffer` double-buffer architecture already exposes `output_buffer` and `color_buffer` properties. The critical optimization is replacing the `read_positions()` CPU readback in `_update_points_from_sim()` with direct GPU buffer injection into pygfx's `Buffer._wgpu_object`. OpenCV 4.13's `cv2.createCLAHE` is confirmed working in the environment.

**Primary recommendation:** Tackle GPU buffer sharing first (highest risk, highest impact), then visual quality tuning (bloom, background, alpha), then CLAHE depth enhancement, then crossfade engine, then color extraction enrichment.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Luminous cluster look: clusters brighten where particles overlap; colors stay rich in dense regions (saturated red stays red, NOT wash to white)
- Soft Gaussian falloff via existing PointsGaussianBlobMaterial -- no shape change needed
- Try alpha + bloom + Gaussian blob approximation first; escalate to custom WGSL fragment shader only if needed
- Warm off-white background (~#F8F6F3 range) -- white only, no dark/light toggle
- Bloom creates colored halos (not white glow) -- warm color spread from particle colors
- GUI panels stay dark themed (Phase 6 handles UI theming)
- All visual parameters crossfade smoothly with ease-out curve (~0.3-0.5s)
- Only discrete params (solver_iterations) snap instantly
- Unified crossfade system: one engine for both slider changes AND A/B preset CrossfadeWidget transitions
- Per-pixel color sampling from source photo -- each particle gets color from exact pixel location
- Full contrast CLAHE on depth map only (not color extraction)
- Vivid saturation boost 20-40% beyond source photo levels, applied uniformly
- Color mapping baked at extraction time (not dynamic render-time)

### Claude's Discretion
- Exact alpha value and bloom parameters for luminous cluster approximation
- Whether custom WGSL shader is needed (try approximation first)
- CLAHE parameters (clip limit, tile grid size) for optimal depth contrast
- Exact warm off-white hex value in the #F8F6F3 range
- GPU buffer sharing implementation strategy between compute and render
- Crossfade engine internals (timer mechanism, interpolation math)
- Saturation boost exact percentage within 20-40% range

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REND-01 | Particles render as round, soft points instead of hard squares | Already achieved via PointsGaussianBlobMaterial; verify alpha tuning preserves softness |
| REND-02 | Viewport uses white background by default | Change BG_COLOR_TOP/BOTTOM to warm off-white; retune bloom for white bg |
| REND-03 | Additive blending creates luminous, glowing particle clusters | Alpha < 1.0 with vertex colors + bloom; test approximation before custom shader |
| REND-04 | Bloom/glow post-processing enhances particle aesthetics | Retune PhysicalBasedBloomPass: increase strength, increase filter_radius for colored halos |
| REND-05 | GPU buffer sharing eliminates CPU readback for 1M+ particles | Inject wgpu buffer into pygfx Buffer._wgpu_object; bypass read_positions() |
| REND-06 | Parameter changes crossfade smoothly instead of popping | Unified crossfade engine with QTimer-driven ease-out interpolation |
| DPTH-01 | Depth maps use CLAHE post-processing for proper contrast | cv2.createCLAHE before min-max normalization in DepthExtractor.extract() |
| DPTH-02 | Depth-to-color mapping uses richer, more expressive color range | Per-pixel color from source photo + HSV saturation boost at extraction time |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pygfx | 0.16.0 | 3D rendering engine | Already in stack; PointsGaussianBlobMaterial, PhysicalBasedBloomPass |
| wgpu | 0.31.0 | GPU API | Already in stack; buffer creation, compute pipeline |
| OpenCV | 4.13.0 | Image processing | Already in stack; CLAHE, HSV conversion, saturation boost |
| numpy | >=2.1 | Array operations | Already in stack; buffer packing, color manipulation |
| PySide6 | >=6.8 | GUI framework | Already in stack; QTimer for crossfade engine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cv2.createCLAHE | OpenCV built-in | Contrast-limited adaptive histogram equalization | Depth map enhancement before normalization |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alpha approximation for luminous look | Custom WGSL additive blend shader | Try alpha first; shader needed only if dense clusters wash out |
| pygfx Buffer._wgpu_object injection | wgpu copy_buffer_to_buffer per frame | Injection is zero-copy; copy adds one GPU-to-GPU copy per frame |

**Installation:**
No new packages needed -- all dependencies already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
apollo7/
  rendering/
    crossfade.py           # NEW: Unified crossfade engine
  postfx/
    bloom.py               # MODIFY: Retune for white background
  extraction/
    depth.py               # MODIFY: Add CLAHE step
    color.py               # MODIFY: Per-pixel sampling + saturation boost
  pointcloud/
    depth_projection.py    # MODIFY: Use enriched colors from extraction
  config/
    settings.py            # MODIFY: White background, bloom defaults
  gui/widgets/
    viewport_widget.py     # MODIFY: Buffer sharing, crossfade integration
```

### Pattern 1: GPU Buffer Sharing (Zero-Copy)
**What:** Inject simulation output buffer directly into pygfx Geometry, bypassing CPU readback
**When to use:** Every frame during simulation rendering
**Example:**
```python
# Source: pygfx source code inspection (engine/update.py)
import pygfx as gfx

# Create a pygfx Buffer shell with matching dimensions but NO data
n_particles = 1_000_000
STRIDE = 32  # 2x vec4<f32> per particle = 32 bytes
shared_buf = gfx.Buffer(
    nbytes=n_particles * STRIDE,
    nitems=n_particles,
    format="4xf4",  # vec4<f32> -- positions
)

# Inject the wgpu buffer from simulation directly
# This prevents pygfx from creating its own buffer
shared_buf._wgpu_object = sim_engine.get_positions_buffer()

# Use in geometry -- pygfx renders from this buffer directly
geometry = gfx.Geometry(positions=shared_buf, colors=color_buf, sizes=size_buf)
```

**Critical detail:** The simulation ParticleBuffer stores particles as 2x vec4 (pos.xyz+life, vel.xyz+mass = 32 bytes per particle). pygfx Geometry.positions expects (N, 3) float32. Two approaches:
1. **Extract positions via a compute shader** that copies xyz from stride-32 layout into a packed (N, 3) positions buffer -- one GPU dispatch per frame, very fast
2. **Restructure ParticleBuffer** to store positions in a separate contiguous (N, 3) buffer -- cleaner but requires changes to all compute shaders

Recommendation: Approach 1 (extract compute shader) -- minimal disruption to existing PBF pipeline.

### Pattern 2: Unified Crossfade Engine
**What:** Single engine that drives smooth parameter transitions for both individual slider changes and A/B preset crossfades
**When to use:** Any time a visual parameter changes
**Example:**
```python
# Source: project pattern analysis
from PySide6.QtCore import QTimer

class CrossfadeEngine:
    """Drives smooth parameter transitions with ease-out curve."""

    TICK_MS = 16          # ~60fps update rate
    DURATION_MS = 400     # ~0.4s transition

    def __init__(self, apply_fn):
        self._apply_fn = apply_fn  # callback(name, value)
        self._active: dict[str, _Transition] = {}
        self._timer = QTimer()
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_target(self, name: str, target: float, current: float):
        """Start smooth transition from current to target value."""
        self._active[name] = _Transition(current, target, 0.0)
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        done = []
        for name, t in self._active.items():
            t.progress = min(1.0, t.progress + self.TICK_MS / self.DURATION_MS)
            # Ease-out: 1 - (1-t)^3
            eased = 1.0 - (1.0 - t.progress) ** 3
            value = t.start + (t.end - t.start) * eased
            self._apply_fn(name, value)
            if t.progress >= 1.0:
                done.append(name)
        for name in done:
            del self._active[name]
        if not self._active:
            self._timer.stop()
```

### Pattern 3: CLAHE Depth Enhancement
**What:** Apply CLAHE to raw depth output before min-max normalization
**When to use:** During depth extraction, after model inference, before normalization
**Example:**
```python
# Source: OpenCV docs + codebase analysis
import cv2
import numpy as np

def enhance_depth_clahe(depth_raw: np.ndarray, clip_limit: float = 3.0,
                         tile_size: int = 8) -> np.ndarray:
    """Apply CLAHE to raw depth map for full contrast stretch.

    Args:
        depth_raw: Raw depth output from model (arbitrary float range)
        clip_limit: CLAHE clip limit (3.0 balances contrast vs noise)
        tile_size: Grid size for local equalization (8x8 default)

    Returns:
        Enhanced depth map in [0, 1] float32 range
    """
    # Scale to uint8 for CLAHE (operates on integer histograms)
    d_min, d_max = depth_raw.min(), depth_raw.max()
    depth_uint8 = ((depth_raw - d_min) / (d_max - d_min + 1e-8) * 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    enhanced = clahe.apply(depth_uint8)

    return enhanced.astype(np.float32) / 255.0
```

### Anti-Patterns to Avoid
- **CPU readback per frame:** Current `_update_points_from_sim()` calls `read_positions()` which does `device.queue.read_buffer()` -- this stalls the GPU pipeline and caps throughput at ~100K particles. Must replace with buffer sharing.
- **White glow bloom on white background:** PhysicalBasedBloomPass adds glow based on luminance. On white background, white bloom is invisible. Must ensure particle emissive colors drive the bloom, producing colored halos.
- **Instant parameter snapping:** Setting values directly without interpolation creates jarring visual pops. All continuous parameters must route through the crossfade engine.
- **CLAHE after normalization:** Applying CLAHE after [0,1] normalization loses information. Apply CLAHE to the raw model output first, then normalize.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Histogram equalization | Custom per-pixel contrast stretch | cv2.createCLAHE | Handles local contrast, tile-based, well-tested |
| Bloom post-processing | Custom blur/composite pipeline | pygfx PhysicalBasedBloomPass | Already integrated, physically-based, efficient |
| Ease-out interpolation | Complex animation framework | Simple cubic ease-out: `1-(1-t)^3` | Three lines of math, no dependency |
| Color space conversion | Manual RGB math | cv2.cvtColor HSV/RGB | Handles edge cases, fast |
| Timer-driven animation | Threading / asyncio | PySide6 QTimer | Already in event loop, no threading issues |

**Key insight:** Phase 5 is mostly wiring and tuning existing components, not building new systems. The only truly new code is the crossfade engine and the buffer-sharing bridge.

## Common Pitfalls

### Pitfall 1: Buffer Usage Flags Mismatch
**What goes wrong:** pygfx creates wgpu buffers with VERTEX usage; simulation creates with STORAGE usage. If the shared buffer lacks required flags, rendering fails silently or crashes.
**Why it happens:** wgpu buffers must declare all usage flags at creation time. STORAGE | VERTEX is needed for compute+render sharing.
**How to avoid:** When creating ParticleBuffer's position output buffer, add `wgpu.BufferUsage.VERTEX` flag. Currently buffers have `STORAGE | COPY_SRC | COPY_DST`. Add VERTEX to the output buffer.
**Warning signs:** Black screen, no particles visible, wgpu validation errors in console.

### Pitfall 2: Bloom Invisible on White Background
**What goes wrong:** Bloom adds brightness-based glow. On white background (#F8F6F3), any white/bright glow is invisible -- it blends into the background.
**Why it happens:** PhysicalBasedBloomPass uses luminance thresholding. Particles with alpha < 1.0 have lower luminance, and their bloom contribution is subtle.
**How to avoid:** Increase bloom_strength significantly (0.3-0.8 range vs current 0.04). Increase filter_radius (0.01-0.02) for wider colored spread. Particles must have saturated colors so bloom spreads color, not white.
**Warning signs:** Particles look flat, no visible glow halo around clusters.

### Pitfall 3: Double-Buffer Swap Timing with Shared Buffers
**What goes wrong:** pygfx reads from the buffer during render, while simulation writes to it during compute. If both happen simultaneously, visual tearing or corruption occurs.
**Why it happens:** The ping-pong buffer swap means the "output" buffer alternates each frame. pygfx must always read from the most recently completed output.
**How to avoid:** Update the `_wgpu_object` reference on the pygfx Buffer after each swap. Or use the extract-compute-shader approach which writes to a stable render buffer.
**Warning signs:** Flickering particles, positions jumping between frames.

### Pitfall 4: CLAHE Over-Enhancement
**What goes wrong:** High clip_limit creates extreme local contrast, making depth maps noisy with artificial bands.
**Why it happens:** CLAHE amplifies noise in uniform regions when clip_limit is too high.
**How to avoid:** Start with clip_limit=3.0, tile_size=8. The goal is to separate "pancake layers" into continuous volume, not maximize contrast. Test with real photos.
**Warning signs:** Depth map looks grainy, artificial contour lines visible.

### Pitfall 5: Crossfade Engine Memory Leak
**What goes wrong:** If QTimer keeps running when no transitions are active, or if transition objects accumulate.
**Why it happens:** Forgetting to stop the timer, or not cleaning completed transitions.
**How to avoid:** Stop QTimer when `_active` dict is empty. Remove transitions when progress >= 1.0.
**Warning signs:** Increasing CPU usage over time, stuttering.

## Code Examples

### Background Color Change
```python
# Source: codebase analysis (settings.py + viewport_widget.py)
# In settings.py:
BG_COLOR_TOP: str = "#F8F6F3"    # Warm off-white (was #1a1a1a)
BG_COLOR_BOTTOM: str = "#F5F3F0"  # Slightly warmer at bottom (was #0a0a0a)

# In viewport_widget.py __init__:
self._scene.add(gfx.Background.from_color(BG_COLOR_TOP, BG_COLOR_BOTTOM))
```

### Luminous Alpha Tuning
```python
# Source: codebase analysis (viewport_widget.py)
# Current: _BLEND_ALPHA = 0.7
# Recommendation: Start at 0.4-0.5 for luminous overlap effect
# Lower alpha = more visible overlap brightening in dense regions
_BLEND_ALPHA: float = 0.45

# When creating point colors, apply alpha:
colors[:, 3] = _BLEND_ALPHA  # uniform alpha for luminous look
```

### Bloom Retuning for White Background
```python
# Source: codebase analysis (bloom.py + settings.py)
# Current defaults: strength=0.04, filter_radius=0.005
# New defaults for white background with colored halos:
BLOOM_STRENGTH_DEFAULT: float = 0.5    # Was 0.04 -- much stronger
BLOOM_FILTER_RADIUS: float = 0.015     # Was 0.005 -- wider spread

# In BloomController.__init__:
self._bloom_pass = PhysicalBasedBloomPass(
    bloom_strength=self._clamp_strength(strength),
    max_mip_levels=6,
    filter_radius=0.015,        # Wider for colored halo spread
    use_karis_average=True,     # Prevent firefly artifacts
)
```

### GPU Buffer Sharing Bridge
```python
# Source: pygfx source analysis (engine/update.py ensure_wgpu_object)
import wgpu
import pygfx as gfx

def create_shared_position_buffer(device, n_particles: int) -> tuple:
    """Create a wgpu buffer usable by both compute and pygfx render.

    Returns (wgpu_buffer, pygfx_buffer) pair.
    """
    byte_size = n_particles * 12  # 3 x float32 per position

    # Create with BOTH storage (compute) and vertex (render) usage
    wgpu_buf = device.create_buffer(
        size=byte_size,
        usage=(
            wgpu.BufferUsage.STORAGE
            | wgpu.BufferUsage.VERTEX
            | wgpu.BufferUsage.COPY_DST
            | wgpu.BufferUsage.COPY_SRC
        ),
    )

    # Create pygfx Buffer shell and inject wgpu buffer
    pygfx_buf = gfx.Buffer(
        nbytes=byte_size,
        nitems=n_particles,
        format="3xf4",
    )
    pygfx_buf._wgpu_object = wgpu_buf

    return wgpu_buf, pygfx_buf
```

### Extract Positions Compute Shader (WGSL)
```wgsl
// Extracts xyz positions from stride-32 particle state buffer
// into a packed float3 positions buffer for rendering

struct Particle {
    pos: vec4<f32>,   // xyz + life
    vel: vec4<f32>,   // xyz + mass
};

@group(0) @binding(0) var<storage, read> particles: array<Particle>;
@group(0) @binding(1) var<storage, read_write> positions: array<vec4<f32>>;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let idx = id.x;
    if (idx >= arrayLength(&particles)) { return; }
    positions[idx] = vec4<f32>(particles[idx].pos.xyz, 1.0);
}
```

### Per-Pixel Color Extraction with Saturation Boost
```python
# Source: codebase + OpenCV docs
import cv2
import numpy as np

def extract_enriched_colors(image_rgb: np.ndarray, saturation_boost: float = 1.3) -> np.ndarray:
    """Extract per-pixel colors with saturation boost.

    Args:
        image_rgb: H x W x 3 float32 [0, 1]
        saturation_boost: Multiplier for saturation (1.3 = 30% boost)

    Returns:
        H x W x 4 float32 RGBA with boosted saturation
    """
    # Convert to uint8 for HSV
    img_uint8 = (np.clip(image_rgb, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV)

    # Boost saturation channel
    hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * saturation_boost, 0, 255).astype(np.uint8)

    # Convert back to RGB
    boosted = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0

    # Add alpha channel
    alpha = np.ones((*boosted.shape[:2], 1), dtype=np.float32)
    return np.concatenate([boosted, alpha], axis=-1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CPU readback per frame | GPU buffer sharing via _wgpu_object injection | pygfx 0.6+ | 10-100x throughput for 1M+ particles |
| Simple min-max depth normalization | CLAHE + normalization | Well-established | Fixes "pancake layer" depth artifacts |
| Instant parameter changes | Ease-out crossfade transitions | Industry standard | Professional, polished feel |
| Dark background default | White gallery background | Design decision | Matches art gallery aesthetic |

**Deprecated/outdated:**
- SPH solver (replaced by PBF in Phase 4) -- all particle references use PBF pipeline
- `_BLEND_ALPHA = 0.7` default -- needs retuning for luminous cluster effect

## Open Questions

1. **Exact bloom parameters for colored halos on white**
   - What we know: strength needs significant increase from 0.04; filter_radius affects spread
   - What's unclear: Exact values depend on particle density and color -- needs visual tuning
   - Recommendation: Start with strength=0.5, filter_radius=0.015, iterate visually

2. **Whether alpha approximation is sufficient for luminous look**
   - What we know: pygfx PointsGaussianBlobMaterial does NOT expose blend_mode; current workaround is alpha < 1.0
   - What's unclear: Whether alpha compositing with Gaussian falloff produces true "overlapping brightness" or just transparency
   - Recommendation: Try alpha=0.4-0.5 first. If clusters look washed/transparent rather than luminous, write custom WGSL fragment shader with additive blending

3. **Buffer stride compatibility**
   - What we know: Simulation stores particles as stride-32 (2x vec4). pygfx expects (N, 3) float32 for positions.
   - What's unclear: Whether pygfx can handle stride-32 with format="3xf4" and offset, or if extraction shader is required
   - Recommendation: Use extraction compute shader (safest, most flexible)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with pytest-timeout) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x --timeout=30` |
| Full suite command | `python -m pytest tests/ --timeout=30` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REND-01 | Particles render as soft round points | manual-only | Visual inspection | N/A -- rendering is visual |
| REND-02 | White background default | unit | `python -m pytest tests/test_visual_quality.py::test_white_background -x` | Wave 0 |
| REND-03 | Luminous cluster blending | unit | `python -m pytest tests/test_visual_quality.py::test_blend_alpha_configured -x` | Wave 0 |
| REND-04 | Bloom produces visible halos | unit | `python -m pytest tests/test_visual_quality.py::test_bloom_tuned_for_white -x` | Wave 0 |
| REND-05 | GPU buffer sharing (no CPU readback) | unit | `python -m pytest tests/test_visual_quality.py::test_buffer_sharing -x` | Wave 0 |
| REND-06 | Smooth parameter crossfade | unit | `python -m pytest tests/test_crossfade_engine.py -x` | Wave 0 |
| DPTH-01 | CLAHE depth enhancement | unit | `python -m pytest tests/test_depth_extractor.py::test_clahe_enhancement -x` | Wave 0 |
| DPTH-02 | Rich color mapping with saturation boost | unit | `python -m pytest tests/test_visual_quality.py::test_saturation_boost -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x --timeout=30`
- **Per wave merge:** `python -m pytest tests/ --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_visual_quality.py` -- covers REND-02, REND-03, REND-04, REND-05, DPTH-02
- [ ] `tests/test_crossfade_engine.py` -- covers REND-06
- [ ] `tests/test_depth_extractor.py::test_clahe_enhancement` -- new test in existing file for DPTH-01

*(Existing test_postfx.py covers bloom controller basics but needs new tests for retuned parameters)*

## Sources

### Primary (HIGH confidence)
- pygfx source code (v0.16.0) -- `engine/update.py` ensure_wgpu_object, Buffer.__init__, PointsGaussianBlobMaterial params
- wgpu-py source (v0.31.0) -- BufferUsage flags, create_buffer API
- OpenCV 4.13.0 -- cv2.createCLAHE verified working in environment
- Apollo 7 codebase -- viewport_widget.py, bloom.py, depth.py, buffers.py, settings.py

### Secondary (MEDIUM confidence)
- [pygfx documentation](https://docs.pygfx.org/stable/basics.html) -- Geometry, Buffer, material concepts
- [pygfx GitHub](https://github.com/pygfx/pygfx) -- approaching v1.0 (expected July 2026), API may change
- [OpenCV CLAHE docs](https://docs.opencv.org/4.x/d2/d74/tutorial_js_histogram_equalization.html) -- parameter guidance
- [wgpu-py GitHub](https://github.com/pygfx/wgpu-py) -- WebGPU for Python

### Tertiary (LOW confidence)
- Bloom parameter values (0.5 strength, 0.015 filter_radius) -- educated starting points, need visual tuning
- Alpha value for luminous look (0.4-0.5) -- theory-based, needs empirical validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified
- Architecture: HIGH -- GPU buffer sharing mechanism confirmed via source code reading
- Pitfalls: HIGH -- identified from codebase analysis and API inspection
- Bloom/alpha tuning: MEDIUM -- correct approach confirmed, exact values need experimentation
- CLAHE parameters: MEDIUM -- well-documented technique, optimal values depend on input data

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- pygfx pinned at 0.16.0, no expected breaking changes)
