# Phase 2: Creative Sculpting - Research

**Researched:** 2026-03-14
**Domain:** GPU particle simulation, post-processing effects, creative tool UX (PySide6 + pygfx + wgpu)
**Confidence:** MEDIUM

## Summary

Phase 2 transforms Apollo 7 from a static point cloud viewer into a real-time GPU-accelerated creative sculpting tool. The core technical challenge is implementing compute-shader-based particle simulation (Perlin flow fields, attraction/repulsion, SPH fluid dynamics, gravity/wind) running on millions of particles at interactive frame rates, all within the existing pygfx/wgpu/PySide6 stack on an AMD GPU via DirectML/Vulkan.

The existing stack (pygfx 0.6+, wgpu-py 0.19+) provides the foundation: pygfx handles scene rendering with PointsGaussianBlobMaterial, while wgpu-py exposes the full WebGPU compute shader API (storage buffers, compute pipelines, dispatch). Bloom is natively supported via `PhysicalBasedBloomPass`, but depth-of-field and ambient occlusion must be implemented as custom effect passes. Offscreen rendering for high-res export is supported via `wgpu.gui.offscreen.WgpuCanvas`. Undo/redo uses Qt's built-in `QUndoStack`/`QUndoCommand`.

**Primary recommendation:** Build the simulation engine as a standalone module using wgpu compute shaders (WGSL) with double-buffered storage buffers for particle state. Keep simulation logic completely decoupled from pygfx rendering -- the sim writes positions/colors to GPU buffers, and pygfx reads them for display. This separation enables the "Simulate" button flow and performance mode toggle cleanly.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Continuous loop animation: simulation runs continuously -- sculptures are always in motion
- Speed/turbulence sliders control energy level
- Four force types, all available simultaneously: Perlin noise flow fields, attraction/repulsion, SPH fluid dynamics, gravity + wind
- Features drive simulation as initial conditions AND continuous influence on flow fields
- Target: millions of particles (1-5M) in real-time on GPU compute
- Fading alpha trails
- Post-processing: bloom/glow, depth of field, motion trails, ambient occlusion -- all adjustable via sliders
- Manual "Simulate" button: user reviews static point cloud first, then clicks to bring it alive
- Always interactive during simulation: orbit, zoom, adjust sliders
- FPS counter visible in viewport
- Performance mode toggle
- Visual params hot-reload, physics params restart sim
- Project file includes: all parameters, photo references (paths), cached extraction data, point cloud snapshot
- Export: PNG only (lossless with alpha transparency)
- Export resolutions: viewport/2x/4x + custom + presets (4K, 8K, Instagram square)
- Transparent background option on export
- Categorized preset library with browse/preview
- Debounced slider undo: slider drags collapse into one undo entry
- Ctrl+Z undo, Ctrl+Shift+Z redo
- Per-section reset buttons + global Reset All
- Keyboard shortcuts: Ctrl+Z/Shift+Z, Ctrl+S, Ctrl+E, Space pause/resume

### Claude's Discretion
- Controls panel organization (collapsible sections vs tabbed)
- Project file format (JSON, binary, or compressed archive)
- SPH solver parameters and defaults
- Perlin noise octaves and frequency defaults
- Performance mode quality reduction strategy
- Bloom implementation approach (screen-space blur passes)

### Deferred Ideas (OUT OF SCOPE)
- UI polish pass -- could be a dedicated polish phase or part of Phase 3

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXTRACT-05 | User can view extracted features per photo (color palette, edge map, depth map, semantic tags) | Feature viewer panel -- extends existing FeatureStripPanel with full detail view |
| RENDER-04 | GPU-computed particle system with physically-based dynamics | wgpu compute shaders with WGSL, storage buffers for particle state, multi-pass simulation |
| RENDER-05 | Post-processing effects (bloom, DoF, AO) | pygfx PhysicalBasedBloomPass for bloom; custom EffectPass subclasses for DoF and SSAO |
| RENDER-06 | Render-then-interact pattern | "Simulate" button triggers compute pipeline; viewport remains lightweight pygfx render loop |
| SIM-01 | Research and integrate particle/generative models | Perlin/simplex noise flow fields, SPH kernels, attraction/repulsion forces -- all in WGSL compute |
| SIM-02 | GPU-accelerated fluid dynamics (SPH) | 3-pass SPH: density calc, force computation, integration -- WGSL compute shaders |
| SIM-03 | Flow field generation from extracted features | Feature maps (edges, depth, color) uploaded as textures, sampled in compute shader to modulate flow |
| SIM-04 | Visually pleasing output (aesthetic hard requirement) | Post-processing chain + alpha trails + feature-driven flow produce gallery-worthy results |
| CTRL-01 | Parameter panel with real-time viewport updates | Extend ControlsPanel with Simulation, Forces, Post-FX collapsible sections |
| CTRL-03 | Undo/redo on all parameter changes | QUndoStack + QUndoCommand with mergeWith() for slider debouncing |
| CTRL-04 | Save/load full project state | JSON project file with all params, photo paths, cached features, camera state |
| CTRL-05 | Export high-res still images | pygfx offscreen rendering via WgpuCanvas at arbitrary resolution, PNG with alpha |
| CTRL-06 | Preset library | JSON-based preset files organized by category, with save/load/browse UI |

</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pygfx | >=0.6 | Scene graph, rendering, materials | Already powers the viewport; has PhysicalBasedBloomPass for bloom |
| wgpu-py | >=0.19 | WebGPU API for compute shaders | Direct GPU compute access, WGSL shader language, storage buffers |
| PySide6 | >=6.8 | GUI framework | QUndoStack/QUndoCommand for undo/redo, signals/slots for controls |
| numpy | >=2.1 | CPU-side array operations | Buffer preparation, data marshalling |
| rendercanvas | >=2.6 | Qt-wgpu bridge | QRenderWidget already in use |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | >=11 | PNG export with alpha | Save rendered frames as PNG with transparency |
| scipy | >=1.14 | Spatial algorithms | Optional: KD-tree for attraction/repulsion neighbor search on CPU fallback |

### No New Dependencies Required
The existing stack covers all Phase 2 needs. Compute shaders are written in WGSL (text strings in Python), not requiring additional packages. Post-processing passes subclass pygfx internals. JSON for project files uses stdlib.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WGSL compute for SPH | PyOpenCL/cupy | Adds dependency, CUDA-only; wgpu works on AMD via Vulkan |
| Custom DoF/AO passes | Wait for pygfx to add them | pygfx roadmap unclear; custom passes give us control now |
| JSON project files | SQLite or msgpack | JSON is human-readable, debuggable; perf fine for project state |

## Architecture Patterns

### Recommended Project Structure
```
apollo7/
  simulation/
    __init__.py
    engine.py           # SimulationEngine: orchestrates compute passes
    shaders/
      __init__.py
      noise.wgsl        # Perlin/simplex noise functions
      flow_field.wgsl   # Flow field computation from features
      forces.wgsl       # Attraction/repulsion, gravity/wind
      sph.wgsl          # SPH density + force + integration
      integrate.wgsl    # Final position/velocity integration
    buffers.py          # ParticleBuffer: manages GPU storage buffers
    parameters.py       # SimulationParams dataclass
  postfx/
    __init__.py
    dof_pass.py         # DepthOfFieldPass (custom EffectPass)
    ssao_pass.py        # SSAOPass (custom EffectPass)
    trails.py           # Alpha trail accumulation
  project/
    __init__.py
    save_load.py        # Project serialization/deserialization
    presets.py          # Preset library management
  gui/
    panels/
      simulation_panel.py  # Simulation controls (forces, speed, turbulence)
      postfx_panel.py      # Post-processing controls
      export_panel.py      # Export controls
      preset_panel.py      # Preset browser
      feature_viewer.py    # Full feature viewer (EXTRACT-05)
    widgets/
      fps_counter.py       # FPS overlay widget
      undo_commands.py     # QUndoCommand subclasses
```

### Pattern 1: Double-Buffered GPU Particle Simulation
**What:** Two storage buffers (A and B) for particle state. Each frame: read from A, compute, write to B. Next frame: swap. Prevents read-write conflicts in parallel compute.
**When to use:** All particle simulation steps.
**Example:**
```python
# Simplified compute pipeline setup using wgpu-py
import wgpu

device = wgpu.utils.get_default_device()

# Particle struct: vec4 position (xyz + w=life), vec4 velocity (xyz + w=mass)
particle_count = 2_000_000
buf_size = particle_count * 32  # 8 floats * 4 bytes

buf_a = device.create_buffer(size=buf_size, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)
buf_b = device.create_buffer(size=buf_size, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST)

# WGSL compute shader reads buf_a, writes buf_b
shader_code = """
@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<storage, read_write> particles_out: array<Particle>;
@group(0) @binding(2) var<uniform> params: SimParams;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x;
    if (i >= arrayLength(&particles_in)) { return; }
    var p = particles_in[i];
    // ... apply forces, update velocity, integrate position ...
    particles_out[i] = p;
}
"""
```

### Pattern 2: Simulation Engine with Parameter Hot-Reload
**What:** SimulationEngine class manages the compute pipeline lifecycle. Visual params (point size, colors, bloom intensity) update immediately via pygfx material properties. Physics params (forces, viscosity) trigger sim restart from initial conditions.
**When to use:** All parameter changes from UI.
**Example:**
```python
class SimulationEngine:
    def __init__(self, device: wgpu.GPUDevice):
        self._device = device
        self._running = False
        self._params = SimulationParams()  # dataclass with all tunables
        self._initial_positions = None     # snapshot for restart

    def start(self, positions: np.ndarray, colors: np.ndarray, features: dict):
        """Initialize buffers from point cloud data and start sim loop."""
        self._initial_positions = positions.copy()
        self._upload_buffers(positions, colors)
        self._upload_feature_textures(features)
        self._running = True

    def update_visual_param(self, name: str, value: float):
        """Hot-reload: update uniform buffer, no sim restart."""
        self._params.set(name, value)
        self._update_uniform_buffer()

    def update_physics_param(self, name: str, value: float):
        """Restart sim from initial conditions with new physics."""
        self._params.set(name, value)
        self._restart_from_initial()
```

### Pattern 3: Feature-Driven Flow Fields
**What:** Extracted features (edge maps, depth maps, color distributions) are uploaded as GPU textures. Compute shaders sample these textures to modulate flow field forces continuously.
**When to use:** Connecting photo features to simulation behavior.
**Example:**
```wgsl
// In flow_field.wgsl
@group(1) @binding(0) var edge_map: texture_2d<f32>;
@group(1) @binding(1) var depth_map: texture_2d<f32>;
@group(1) @binding(2) var edge_sampler: sampler;

fn sample_feature_force(pos: vec3<f32>) -> vec3<f32> {
    // Map 3D position back to 2D texture coordinates
    let uv = vec2<f32>(pos.x * 0.5 + 0.5, pos.y * 0.5 + 0.5);
    let edge_val = textureSampleLevel(edge_map, edge_sampler, uv, 0.0).r;
    let depth_val = textureSampleLevel(depth_map, edge_sampler, uv, 0.0).r;

    // Edge intensity -> turbulence, depth -> current direction
    let turbulence = edge_val * params.turbulence_scale;
    let current = vec3<f32>(0.0, 0.0, depth_val * params.depth_current_strength);
    return current + noise3d(pos * params.noise_freq + params.time) * turbulence;
}
```

### Pattern 4: Qt Undo/Redo with Slider Debouncing
**What:** QUndoCommand subclass with mergeWith() that collapses consecutive slider changes into a single undo entry.
**When to use:** All slider-driven parameter changes.
**Example:**
```python
from PySide6.QtGui import QUndoCommand

class ParameterChangeCommand(QUndoCommand):
    _MERGE_ID = 1000  # unique per parameter

    def __init__(self, param_name: str, old_value: float, new_value: float,
                 apply_fn, merge_id_offset: int = 0):
        super().__init__(f"Change {param_name}")
        self._param = param_name
        self._old = old_value
        self._new = new_value
        self._apply = apply_fn
        self._merge_id = self._MERGE_ID + merge_id_offset

    def redo(self):
        self._apply(self._param, self._new)

    def undo(self):
        self._apply(self._param, self._old)

    def id(self) -> int:
        return self._merge_id

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Collapse consecutive same-param changes (slider drag debounce)."""
        if other.id() != self.id():
            return False
        self._new = other._new  # keep latest value, discard intermediate
        return True
```

### Anti-Patterns to Avoid
- **CPU-side particle simulation:** Even with numpy vectorization, 1M+ particles will not hit real-time on CPU. ALL simulation must be GPU compute.
- **Reading GPU buffers back to CPU each frame:** Only read back for export or save. For rendering, keep data on GPU -- pygfx can read from the same GPU buffers.
- **Single-threaded sim + render:** The simulation compute dispatch and the pygfx render call should be separate. Compute runs first, then render reads the output buffer.
- **Monolithic WGSL shader:** Split into separate passes (flow field, forces, SPH density, SPH forces, integration). Each pass is a separate compute pipeline. Easier to debug and toggle individually.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bloom/glow post-processing | Custom multi-pass blur | `pygfx.renderers.wgpu.PhysicalBasedBloomPass` | Already ships with pygfx, configurable strength/radius/mip levels |
| Undo/redo system | Custom undo stack | `PySide6.QtGui.QUndoStack` + `QUndoCommand` | Battle-tested, supports merge/compression, integrates with Qt actions |
| Perlin/simplex noise | Python noise generation | WGSL noise functions (port from munrocket/wgsl-noise gist) | Must run on GPU; well-known WGSL implementations exist |
| JSON serialization | Custom binary format | `json` stdlib + dataclass serialization | Human-readable, debuggable; project files are small (<1MB) |
| Offscreen high-res render | Manual framebuffer management | `wgpu.gui.offscreen.WgpuCanvas` + pygfx renderer | pygfx handles all GPU resource management |
| Anti-aliasing | Custom AA pass | pygfx built-in FXAA or DDAA passes | Already available as effect passes |
| FPS counter | Manual frame timing | `time.perf_counter()` in render callback + QLabel overlay | Simple; no library needed |

**Key insight:** The simulation engine (WGSL compute shaders) is the only truly custom component. Everything else leverages existing pygfx/Qt infrastructure.

## Common Pitfalls

### Pitfall 1: GPU Buffer Alignment and Padding
**What goes wrong:** WGSL structs have strict alignment rules (vec3 aligns to 16 bytes, not 12). Misaligned buffers cause silent data corruption or GPU crashes.
**Why it happens:** Python numpy arrays pack tightly; WGSL expects padding.
**How to avoid:** Use vec4 everywhere in WGSL (pad vec3 with a w component). Particle struct should be `vec4 pos` + `vec4 vel` (32 bytes, naturally aligned).
**Warning signs:** Particles appear at wrong positions, NaN values, GPU device lost errors.

### Pitfall 2: Compute-Render Synchronization
**What goes wrong:** Rendering reads particle buffer while compute is still writing, causing flickering or torn frames.
**Why it happens:** WebGPU command buffers execute asynchronously.
**How to avoid:** Double-buffer: compute writes to buffer B while render reads buffer A. Swap after compute completes. Submit compute and render as separate command buffers in sequence.
**Warning signs:** Flickering particles, intermittent visual glitches.

### Pitfall 3: SPH Neighbor Search Performance
**What goes wrong:** Naive O(N^2) neighbor search makes SPH unusable above 10K particles.
**Why it happens:** Each particle must find neighbors within smoothing radius.
**How to avoid:** Implement spatial hashing on GPU -- divide space into grid cells, sort particles by cell, only search adjacent cells. This reduces to O(N*k) where k is average neighbors per particle.
**Warning signs:** FPS drops dramatically when SPH is enabled, even with few particles.

### Pitfall 4: wgpu Device Lost on AMD
**What goes wrong:** Long-running compute shaders can trigger GPU timeout (TDR) on Windows, causing "device lost" error.
**Why it happens:** Windows has a ~2 second GPU timeout by default. A single compute dispatch processing 5M particles in one go can exceed this.
**How to avoid:** Split work into multiple dispatches per frame (e.g., 256K particles per dispatch). Process in chunks. Keep each dispatch under 100ms.
**Warning signs:** Application crashes after enabling simulation, "device lost" in logs.

### Pitfall 5: Qt Event Loop Starvation
**What goes wrong:** If simulation compute + render takes too long per frame, Qt stops processing mouse/keyboard events. UI freezes despite GPU work completing.
**Why it happens:** The animation callback runs synchronously in Qt's event loop.
**How to avoid:** Use `QTimer` with a target frame interval (33ms for 30fps). If a frame takes too long, skip simulation steps but still process Qt events. Performance mode reduces particle count or sim steps.
**Warning signs:** Sliders stop responding, orbit controls lag.

### Pitfall 6: Memory Exhaustion with High-Res Export
**What goes wrong:** Rendering at 8K resolution (7680x4320) requires ~130MB for a single RGBA frame. Multiple passes (bloom, DoF) multiply this.
**Why it happens:** Offscreen render creates full-resolution textures.
**How to avoid:** Export in tiles if resolution exceeds GPU memory limits. Show progress during export. Warn user about estimated memory usage.
**Warning signs:** Export fails silently or produces black image at very high resolutions.

## Code Examples

### Accessing wgpu Device from pygfx Renderer
```python
# Source: pygfx WgpuRenderer docs
# The renderer exposes the wgpu device for compute shader use
renderer = gfx.WgpuRenderer(canvas)
device = renderer.device  # wgpu.GPUDevice instance
```

### Bloom Effect Setup
```python
# Source: pygfx bloom2 example (docs.pygfx.org)
from pygfx.renderers.wgpu import PhysicalBasedBloomPass

bloom_pass = PhysicalBasedBloomPass(
    bloom_strength=0.4,      # 0.0 - 3.0
    max_mip_levels=6,        # 1 - 10
    filter_radius=0.005,
    use_karis_average=False,
)
renderer.effect_passes = [bloom_pass]
# Update at runtime:
bloom_pass.bloom_strength = 1.2
bloom_pass.enabled = True  # toggle on/off
```

### Offscreen High-Res Export
```python
# Source: pygfx offscreen rendering docs
from wgpu.gui.offscreen import WgpuCanvas
import numpy as np
from PIL import Image

def export_image(scene, camera, effect_passes, width, height, transparent=False):
    """Render scene at arbitrary resolution and save as PNG."""
    canvas = WgpuCanvas(size=(width, height), pixel_ratio=1)
    renderer = gfx.WgpuRenderer(canvas)
    renderer.effect_passes = effect_passes

    if transparent:
        # Clear to transparent black
        pass  # pygfx background handling -- remove Background object from scene

    canvas.request_draw(lambda: renderer.render(scene, camera))
    frame = np.asarray(canvas.draw())  # RGBA uint8 array

    img = Image.fromarray(frame, mode="RGBA")
    img.save("export.png", "PNG")
    return frame
```

### wgpu Compute Pipeline (Full Pattern)
```python
# Source: wgpu-py docs + utils
import wgpu
import numpy as np

device = wgpu.utils.get_default_device()

# 1. Create storage buffers
particle_data = np.zeros((100000, 8), dtype=np.float32)  # pos(4) + vel(4)
buf_in = device.create_buffer_with_data(
    data=particle_data.tobytes(),
    usage=wgpu.BufferUsage.STORAGE,
)
buf_out = device.create_buffer(
    size=particle_data.nbytes,
    usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC,
)

# 2. Create shader module
shader = device.create_shader_module(code=wgsl_code)

# 3. Create bind group layout + pipeline
bgl = device.create_bind_group_layout(entries=[
    {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
     "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
    {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
     "buffer": {"type": wgpu.BufferBindingType.storage}},
])
pipeline_layout = device.create_pipeline_layout(bind_group_layouts=[bgl])
pipeline = device.create_compute_pipeline(
    layout=pipeline_layout,
    compute={"module": shader, "entry_point": "main"},
)

# 4. Create bind group
bind_group = device.create_bind_group(
    layout=bgl,
    entries=[
        {"binding": 0, "resource": {"buffer": buf_in}},
        {"binding": 1, "resource": {"buffer": buf_out}},
    ],
)

# 5. Dispatch
encoder = device.create_command_encoder()
pass_enc = encoder.begin_compute_pass()
pass_enc.set_pipeline(pipeline)
pass_enc.set_bind_group(0, bind_group)
workgroups = (particle_data.shape[0] + 255) // 256  # ceil division
pass_enc.dispatch_workgroups(workgroups)
pass_enc.end()
device.queue.submit([encoder.finish()])
```

### QUndoStack Integration
```python
# Source: PySide6 QUndoStack docs (doc.qt.io)
from PySide6.QtGui import QUndoStack, QUndoCommand
from PySide6.QtWidgets import QShortcut
from PySide6.QtCore import Qt

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._undo_stack = QUndoStack(self)

        # Ctrl+Z / Ctrl+Shift+Z shortcuts
        undo_action = self._undo_stack.createUndoAction(self, "Undo")
        undo_action.setShortcut(Qt.CTRL | Qt.Key_Z)
        redo_action = self._undo_stack.createRedoAction(self, "Redo")
        redo_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_Z)
        self.addAction(undo_action)
        self.addAction(redo_action)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OpenGL compute shaders | WebGPU/wgpu compute shaders (WGSL) | 2023-2024 | Cross-platform (Vulkan/Metal/DX12), Python-native via wgpu-py |
| CPU SPH (scipy/numpy) | GPU SPH via compute shaders | Ongoing | 100x+ speedup, enables 1M+ particles real-time |
| Custom bloom shader | pygfx PhysicalBasedBloomPass | pygfx 0.6+ | No custom shader needed for bloom |
| Manual GPU buffer management | wgpu `compute_with_buffers` utility | wgpu 0.19+ | Simplified compute for prototyping; manual for production |

**Deprecated/outdated:**
- pyshader (pygfx's old shader compiler): replaced by direct WGSL strings
- OpenGL-based rendering: pygfx uses wgpu exclusively

## Open Questions

1. **pygfx buffer sharing between compute and render**
   - What we know: pygfx uses wgpu internally; compute output buffers should be usable as vertex buffers for rendering
   - What's unclear: Whether pygfx's `gfx.Buffer` can wrap an existing wgpu storage buffer, or if we need to copy data between compute output and pygfx geometry buffers
   - Recommendation: Prototype early -- if sharing fails, fall back to `device.queue.write_buffer()` to update pygfx geometry each frame. The copy cost for 2M particles (64MB) should be <1ms on modern GPU.

2. **Custom EffectPass subclassing for DoF and SSAO**
   - What we know: pygfx has `PhysicalBasedBloomPass` and `FXAAPass` as examples; the `effect_passes` property accepts a list
   - What's unclear: The exact base class interface for custom EffectPass (undocumented, need to read pygfx source)
   - Recommendation: Study pygfx `PhysicalBasedBloomPass` source code to understand the EffectPass contract. Implement DoF first (simpler than SSAO). SSAO may need depth buffer access.

3. **Alpha trails implementation**
   - What we know: User wants fading ghost particles showing flow history
   - What's unclear: Best approach -- accumulation buffer with fade, or separate trail particle system
   - Recommendation: Use an accumulation texture approach: render current frame at reduced alpha onto a persistent texture that fades each frame. This is a standard motion blur/trail technique implementable as a custom effect pass.

4. **Performance mode quality reduction**
   - What we know: Need to keep FPS above 30 during interaction
   - What's unclear: Best reduction strategy
   - Recommendation: Multi-tiered: (1) reduce sim steps per frame, (2) skip SPH pass, (3) reduce rendered particle count via stride sampling. Auto-detect based on frame time.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-timeout |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --timeout=30` |
| Full suite command | `pytest tests/ --timeout=30` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTRACT-05 | Feature viewer shows all extracted features | manual-only | Manual: load photo, extract, inspect viewer | N/A |
| RENDER-04 | GPU particle system with physics | unit | `pytest tests/test_simulation_engine.py -x` | Wave 0 |
| RENDER-05 | Bloom, DoF, AO post-processing | unit | `pytest tests/test_postfx.py -x` | Wave 0 |
| RENDER-06 | Render-then-interact flow | integration | `pytest tests/test_sim_lifecycle.py -x` | Wave 0 |
| SIM-01 | Particle/generative model integration | unit | `pytest tests/test_simulation_engine.py -x` | Wave 0 |
| SIM-02 | SPH fluid dynamics | unit | `pytest tests/test_sph.py -x` | Wave 0 |
| SIM-03 | Flow field from features | unit | `pytest tests/test_flow_field.py -x` | Wave 0 |
| SIM-04 | Aesthetic quality | manual-only | Manual: visual inspection of output | N/A |
| CTRL-01 | Parameter panel with real-time updates | manual-only | Manual: adjust sliders, verify viewport | N/A |
| CTRL-03 | Undo/redo | unit | `pytest tests/test_undo_redo.py -x` | Wave 0 |
| CTRL-04 | Save/load project | unit | `pytest tests/test_project_save_load.py -x` | Wave 0 |
| CTRL-05 | High-res export | unit | `pytest tests/test_export.py -x` | Wave 0 |
| CTRL-06 | Preset library | unit | `pytest tests/test_presets.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --timeout=30`
- **Per wave merge:** `pytest tests/ --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_simulation_engine.py` -- covers RENDER-04, SIM-01 (parameter dataclass, buffer sizing, sim lifecycle)
- [ ] `tests/test_sph.py` -- covers SIM-02 (SPH kernel math validation with known inputs)
- [ ] `tests/test_flow_field.py` -- covers SIM-03 (feature texture upload, flow vector computation)
- [ ] `tests/test_postfx.py` -- covers RENDER-05 (bloom pass config, effect pass pipeline)
- [ ] `tests/test_sim_lifecycle.py` -- covers RENDER-06 (start/stop/restart sim state machine)
- [ ] `tests/test_undo_redo.py` -- covers CTRL-03 (QUndoStack push/undo/redo, merge behavior)
- [ ] `tests/test_project_save_load.py` -- covers CTRL-04 (roundtrip serialize/deserialize)
- [ ] `tests/test_export.py` -- covers CTRL-05 (offscreen render produces valid PNG with alpha)
- [ ] `tests/test_presets.py` -- covers CTRL-06 (save/load/list/categorize presets)

Note: GPU-dependent tests (simulation, postfx, export) require a wgpu device. Tests should use `pytest.importorskip("wgpu")` and create a device via `wgpu.utils.get_default_device()`. Non-GPU tests (undo/redo, project save/load, presets) can run without GPU.

## Sources

### Primary (HIGH confidence)
- [pygfx bloom2 example](https://docs.pygfx.org/latest/_gallery/feature_demo/bloom2.html) - PhysicalBasedBloomPass API and usage
- [pygfx offscreen rendering](https://docs.pygfx.org/v0.11.0/_gallery/introductory/offscreen.html) - WgpuCanvas offscreen render to numpy array
- [wgpu-py utils docs](https://wgpu-py.readthedocs.io/en/stable/utils.html) - compute_with_buffers utility
- [wgpu-py guide](https://wgpu-py.readthedocs.io/en/stable/guide.html) - compute pipeline, storage buffers, device API
- [PySide6 QUndoStack docs](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QUndoStack.html) - undo/redo framework

### Secondary (MEDIUM confidence)
- [wgpu-py DeepWiki](https://deepwiki.com/pygfx/wgpu-py) - compute shader architecture overview
- [WebGPU fluid sim (Codrops)](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/) - SPH performance characteristics with WebGPU
- [webgpu-compute-exploration (GitHub)](https://github.com/scttfrdmn/webgpu-compute-exploration) - SPH 3-pass architecture reference
- [WGSL Noise gist (munrocket)](https://gist.github.com/munrocket/236ed5ba7e409b8bdf1ff6eca5dcdc39) - Perlin/simplex/value noise in WGSL

### Tertiary (LOW confidence)
- pygfx custom EffectPass base class interface - needs source code inspection; undocumented
- Alpha trail accumulation approach - standard technique, but untested in pygfx specifically
- AMD-specific TDR timeout behavior with wgpu compute dispatches - anecdotal; needs testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and proven in Phase 1
- Architecture (compute shaders): MEDIUM - wgpu compute API is well-documented, but integration with pygfx rendering requires prototyping
- Architecture (post-processing): MEDIUM - bloom is proven; DoF/AO/trails require custom EffectPass subclassing which is undocumented
- Pitfalls: HIGH - well-known GPU compute pitfalls with verified documentation
- SPH implementation: MEDIUM - algorithm is well-understood, but GPU perf tuning (spatial hashing) adds complexity

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack, pygfx approaching 1.0 by mid-2026)
