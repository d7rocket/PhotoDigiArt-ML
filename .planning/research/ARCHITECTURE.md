# Architecture Patterns

**Domain:** Real-time generative art pipeline (data sculptures from photographs)
**Researched:** 2026-03-15
**Focus:** v2.0 integration -- fluid physics, UI rework, Claude creative direction

## Verdict: Keep pygfx + PySide6, Replace SPH with PBF, Add Claude Parameter Pipeline

**Keep pygfx+PySide6.** The stack is sound -- pygfx provides WebGPU rendering with wgpu-py compute shader support, and PySide6 is the most mature Python desktop GUI framework. The problems are not framework problems; they are physics implementation bugs and missing architectural layers. Switching frameworks would cost months and solve nothing.

**Replace SPH with Position Based Fluids (PBF).** The "particles explode" problem is a fundamental numerical stability issue with the current SPH implementation, not a parameter tuning problem. PBF (Macklin & Muller 2013) is unconditionally stable and purpose-built for real-time GPU particle art. This is the single most impactful architectural change.

**Add a Claude Parameter Pipeline** as a new top-level module that sits between the Claude API and the simulation engine, using structured outputs with Pydantic schemas for guaranteed valid parameter generation.

## Why Particles Explode: Root Cause Analysis

The current simulation has several compounding stability issues identified from code review:

### 1. No CFL-Adaptive Timestep (Critical)
The integration shader uses a fixed `dt = 0.016` (60fps assumption). SPH requires the timestep to satisfy the CFL condition: `dt < h / (c_s + v_max)` where `h` is the smoothing radius and `c_s` is the speed of sound. With `smoothing_radius = 0.1` and unclamped velocities, particles easily exceed stable timestep bounds within a few frames.

### 2. Static Spatial Hash (Critical)
`build_spatial_hash()` runs only at simulation init/restart, not per-frame. As particles move, their neighbor lookups become stale -- particles that are now nearby remain invisible to force calculations, while distant particles still register as neighbors. This causes asymmetric forces that amplify exponentially.

### 3. Force Accumulation Without Clamping
Forces from the `forces.wgsl` pass (attraction/repulsion) and inline flow forces in `integrate.wgsl` are summed without any magnitude clamping. A single frame where two particles are nearly coincident produces near-infinite repulsion (`1/r^2` with no cap), which cascades.

### 4. Double-Counting Gravity and Wind
Both `forces.wgsl` (lines 85-91) and `integrate.wgsl` (lines 206-212) compute gravity and wind forces independently. The integration pass adds `external_forces` (which already includes gravity/wind from forces.wgsl) AND computes gravity/wind again inline. Gravity is applied twice per step.

### 5. Boundary Bounce After Position Update
In `integrate.wgsl`, `clamp_boundary()` modifies velocity based on position, but it runs AFTER the position update. The velocity correction happens too late -- the particle has already been clamped to the boundary with its full velocity, then gets a corrected velocity for the next frame. This creates oscillation at boundaries.

## Recommended Architecture: v2.0

### High-Level Component Map

```
+-------------------------------------------------------------------+
|  PySide6 MainWindow                                               |
|  +------------------------------+  +---------------------------+  |
|  |  Viewport (pygfx via         |  |  Right Sidebar            |  |
|  |  QRenderWidget)              |  |  +---------------------+  |  |
|  |                              |  |  | Controls Panel      |  |  |
|  |  SimulationEngine (wgpu      |  |  +---------------------+  |  |
|  |  compute shaders)            |  |  | Claude Panel (NEW)  |  |  |
|  |  - PBF Solver (NEW)         |  |  +---------------------+  |  |
|  |  - Flow Field               |  |  | Simulation Panel    |  |  |
|  |  - Integration              |  |  +---------------------+  |  |
|  |                              |  |  | Library Panel       |  |  |
|  +------------------------------+  |  +---------------------+  |  |
|  +------------------------------+  +---------------------------+  |
|  |  Feature Strip / Viewer      |                                 |
|  +------------------------------+                                 |
+-------------------------------------------------------------------+
         |                    |                      |
    SimulationEngine    ClaudeDirector (NEW)    MappingEngine
         |                    |                      |
    PBFSolver (NEW)     ParameterSchema (NEW)   MappingGraph
```

### Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|--------------|
| `simulation.pbf_solver` | Position Based Fluids constraint solver | SimulationEngine, ParticleBuffer | **NEW** |
| `simulation.engine` | Orchestrate compute passes, manage lifecycle | PBFSolver, ParticleBuffer, ViewportWidget | **MODIFIED** |
| `simulation.buffers` | GPU buffer management, per-frame spatial hash | SimulationEngine | **MODIFIED** |
| `simulation.parameters` | Simulation parameter schema + uniform packing | Engine, ClaudeDirector, UI panels | **MODIFIED** |
| `api.claude_director` | Claude API calls for creative parameter generation | EnrichmentService, ParameterSchema | **NEW** |
| `api.parameter_schema` | Pydantic models defining valid parameter ranges | ClaudeDirector, SimulationEngine | **NEW** |
| `gui.panels.claude_panel` | UI for Claude creative direction interaction | ClaudeDirector, MainWindow | **NEW** |
| `gui.main_window` | Layout, signal wiring, render loop | All panels, viewport | **MODIFIED** |
| `gui.theme` | Stylesheet, color tokens, spacing system | All widgets | **MODIFIED** |
| `rendering.viewport` | Scene management, camera, post-fx | MainWindow | Unchanged |
| `gui.widgets.viewport_widget` | pygfx embed, sim integration, point clouds | SimulationEngine, MainWindow | **MODIFIED** |

### Data Flow: Photo to Living Sculpture

```
Photos -> Ingestion -> Extraction (depth, color, edges, CLIP)
                          |
                          v
                    PointCloudGenerator -> positions + colors
                          |
                          v
                    SimulationEngine.initialize(positions, colors)
                          |
                          v
              +--- PBF Compute Pipeline (per frame) ---+
              |  1. Predict positions (apply forces)    |
              |  2. Build spatial hash (GPU)            |
              |  3. Find neighbors                      |
              |  4. Solve density constraints (iter)    |
              |  5. Apply position corrections          |
              |  6. Update velocities from dx           |
              |  7. Apply vorticity confinement         |
              |  8. Apply XSPH viscosity                |
              +----------------------------------------+
                          |
                          v
                    pygfx Points geometry update
                          |
                          v
                    Renderer.render(scene, camera)
```

### Data Flow: Claude Creative Direction

```
User clicks "Get Direction" or "Auto-direct"
          |
          v
    ClaudeDirector.generate_parameters(
        image_data,        # current photo(s)
        clip_tags,         # semantic understanding
        current_params,    # what's currently set
        mood_request       # optional user text
    )
          |
          v
    Claude API (structured output with Pydantic schema)
          |
          v
    SculptureDirection (validated Pydantic model)
    {
        "noise_frequency": 1.2,
        "noise_amplitude": 0.8,
        "damping": 0.97,
        "gravity": [0.0, -0.02, 0.0],
        "description": "Gentle ocean swell...",
        "reasoning": "The blues and horizon..."
    }
          |
          v
    ClaudePanel displays description + reasoning
          |
          v
    User clicks "Apply" or "Apply with Crossfade"
          |
          v
    SimulationEngine receives parameter updates
    (visual params hot-reload, no restart needed)
```

## Patterns to Follow

### Pattern 1: Position Based Fluids (PBF) Solver

**What:** Replace SPH force-based simulation with PBF constraint-based simulation. PBF is unconditionally stable because it directly solves positional constraints rather than accumulating forces that can explode.

**Why:** SPH requires careful CFL-compliant timesteps and can diverge with any numerical error. PBF works with large timesteps (one step per frame at 60fps) and never explodes because positions are directly corrected to satisfy density constraints.

**Architecture:**

```
simulation/
  pbf_solver.py          # PBF constraint solver orchestration
  shaders/
    pbf_predict.wgsl     # Apply forces, predict positions
    pbf_hash.wgsl        # Build spatial hash on GPU (per-frame)
    pbf_density.wgsl     # Compute density constraint (poly6 kernel)
    pbf_correct.wgsl     # Compute position corrections (lambda)
    pbf_finalize.wgsl    # Update velocity, vorticity confinement, XSPH
```

**Core algorithm per frame:**
```
1. for each particle i:
     v_i = v_i + dt * f_ext(x_i)    # apply gravity, wind, flow field
     x_pred_i = x_i + dt * v_i       # predict position

2. build_spatial_hash(x_pred)         # GPU spatial hash, EVERY frame

3. for iter in 0..solver_iterations:  # typically 3-4 iterations
     for each particle i:
       compute density rho_i from neighbors (poly6 kernel)
       compute constraint C_i = (rho_i / rho_0) - 1
       compute lambda_i = -C_i / (sum_grad_C^2 + epsilon)
     for each particle i:
       compute dx_i from lambda_i + neighbor lambdas (spiky kernel)
       add artificial pressure term (tensile instability fix)
       x_pred_i = x_pred_i + dx_i

4. for each particle i:
     v_i = (x_pred_i - x_i) / dt     # velocity from position change
     apply vorticity confinement      # re-inject lost energy
     apply XSPH viscosity             # smooth velocity field
     x_i = x_pred_i                   # commit new position
```

**Key advantage for art:** The solver iterations parameter directly controls fluid behavior -- 1 iteration gives gas-like behavior, 4+ gives liquid. This is an intuitive creative control.

**Confidence:** HIGH. PBF is the standard approach for real-time GPU fluid art (used by NVIDIA FleX, Houdini FLIP solver concepts). The Macklin & Muller 2013 paper has 1000+ citations and the algorithm maps directly to compute shaders.

### Pattern 2: Per-Frame GPU Spatial Hash

**What:** Move spatial hash construction from CPU (one-time at init) to GPU (every frame).

**Why:** The current CPU-based spatial hash in `buffers.py` (lines 146-213) runs a Python for-loop over all particles -- O(N) in slow Python. It only runs at init, so neighbor data goes stale immediately. A GPU spatial hash using atomic operations runs in a single compute dispatch.

**Architecture:**

```wgsl
// pbf_hash.wgsl - Three dispatches:
// Pass 1: Count particles per cell (atomicAdd to cell_counts)
// Pass 2: Prefix sum on cell_counts -> cell_offsets
// Pass 3: Scatter particles into sorted_indices by cell
```

**Buffer layout (reuse existing buffers):**
- `cell_counts_buf` -- zeroed each frame, atomicAdd per particle
- `cell_offsets_buf` -- parallel prefix sum of cell_counts
- `sorted_indices_buf` -- particle indices sorted by cell hash

### Pattern 3: Claude Structured Output for Parameter Generation

**What:** Use Claude's structured outputs (Pydantic schema) to guarantee valid simulation parameters, not freeform JSON parsing.

**Why:** The current `EnrichmentService.suggest_mappings()` returns `list[dict]` with no schema validation -- Claude can return anything and the `json.loads()` call can fail silently. Structured outputs guarantee schema compliance at the token generation level.

**Architecture:**

```python
# api/parameter_schema.py
from pydantic import BaseModel, Field

class SculptureDirection(BaseModel):
    """Claude's creative direction for a data sculpture."""

    # Physics parameters (bounded to safe ranges)
    noise_frequency: float = Field(ge=0.01, le=5.0)
    noise_amplitude: float = Field(ge=0.0, le=3.0)
    turbulence_scale: float = Field(ge=0.0, le=3.0)
    damping: float = Field(ge=0.9, le=1.0)
    speed: float = Field(ge=0.0, le=3.0)
    viscosity: float = Field(ge=0.0, le=2.0)
    surface_tension: float = Field(ge=0.0, le=1.0)
    gravity_y: float = Field(ge=-1.0, le=0.0)
    solver_iterations: int = Field(ge=1, le=8)

    # Creative metadata
    title: str = Field(max_length=60)
    description: str = Field(max_length=200)
    mood: str = Field(max_length=30)
    reasoning: str = Field(max_length=300)


# api/claude_director.py
class ClaudeDirector:
    """Generates creative sculpture parameters via Claude API."""

    def generate_direction(
        self,
        image_path: str,
        clip_tags: list[tuple[str, float]],
        current_params: SimulationParams,
        user_mood: str | None = None,
    ) -> SculptureDirection:
        response = self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=DIRECTOR_SYSTEM_PROMPT,
            messages=[...],
            # Use structured output for guaranteed schema
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sculpture_direction",
                    "schema": SculptureDirection.model_json_schema(),
                    "strict": True,
                },
            },
        )
        return SculptureDirection.model_validate_json(
            response.content[0].text
        )
```

**Confidence:** HIGH. Claude structured outputs are production-ready (beta since Nov 2025). Pydantic schema generation works directly with the API.

### Pattern 4: Parameter Crossfade for Live Direction Changes

**What:** When Claude suggests new parameters or the user applies a preset, smoothly interpolate all simulation parameters over N frames rather than snapping instantly.

**Why:** Instant parameter changes cause jarring visual discontinuities. Lerping over 30-60 frames (0.5-1 second) creates organic transitions that feel like the sculpture is "breathing" into a new state.

**Architecture:**

```python
# simulation/crossfade.py (extend existing animation/crossfade concept)
class ParameterCrossfader:
    """Smoothly interpolates between parameter sets."""

    def __init__(self, duration_frames: int = 45):
        self._from_params: SimulationParams | None = None
        self._to_params: SimulationParams | None = None
        self._progress: float = 1.0  # 1.0 = complete
        self._duration: int = duration_frames

    def start(self, from_p: SimulationParams, to_p: SimulationParams):
        self._from_params = from_p
        self._to_params = to_p
        self._progress = 0.0

    def tick(self) -> SimulationParams | None:
        """Advance one frame. Returns interpolated params or None if done."""
        if self._progress >= 1.0:
            return None
        self._progress += 1.0 / self._duration
        t = self._ease_in_out(min(self._progress, 1.0))
        return self._lerp_params(self._from_params, self._to_params, t)
```

This integrates into the existing render loop in `ViewportWidget._animate()`.

### Pattern 5: Eliminate CPU Readback in Render Loop

**What:** Replace the current `read_positions()` CPU readback with direct GPU buffer sharing between compute and render pipelines.

**Why:** `_update_points_from_sim()` in `viewport_widget.py` (line 499) calls `read_positions()` which does a full GPU->CPU->GPU roundtrip every frame. This is the single biggest performance bottleneck -- it serializes the GPU pipeline and adds latency proportional to particle count.

**Architecture:**

pygfx `gfx.Buffer` can wrap an existing wgpu buffer. Instead of reading back positions and creating a new `gfx.Buffer` each frame, create the pygfx geometry buffer once using the compute shader's output buffer directly:

```python
# In ViewportWidget.init_simulation():
# Instead of creating a new gfx.Points with numpy data,
# create geometry that references the compute output buffer directly.

# Option A: Use pygfx's buffer update mechanism
# Update geometry.positions.data in-place from GPU buffer
# (still requires readback but avoids allocation)

# Option B: Custom shader material that reads from storage buffer
# Write a custom pygfx material that reads particle positions
# from the compute shader's storage buffer directly.
# This requires pygfx's custom shader API.
```

**Confidence:** MEDIUM. pygfx's custom shader API supports this conceptually but the exact integration between a wgpu storage buffer and a pygfx material needs validation. The mapped buffer API in wgpu-py is intentionally limited. The fallback (Option A with in-place update) still eliminates per-frame allocation.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Trying to Fix SPH with Parameter Tuning
**What:** Spending time adjusting `rest_density`, `smoothing_radius`, `gas_constant` etc. to find stable SPH parameters.
**Why bad:** The instability is structural (stale spatial hash, double gravity, no CFL timestep). Even with perfect parameters, the spatial hash goes stale after frame 1. Parameter tuning on a broken foundation wastes weeks.
**Instead:** Replace SPH with PBF. Fix the structural bugs (double gravity, static hash) first.

### Anti-Pattern 2: Switching to a Different Rendering Framework
**What:** Replacing pygfx with Taichi, Open3D, VTK, or a custom Vulkan renderer.
**Why bad:** pygfx+wgpu already provides everything needed -- compute shaders, point rendering, scene graph, Qt embedding. The rendering works. The problem is in the simulation compute shaders and the CPU readback bottleneck.
**Instead:** Fix the compute pipeline and eliminate CPU readback. pygfx is approaching 1.0 (July 2026) and is actively maintained.

### Anti-Pattern 3: Running Claude API Calls on the Main Thread
**What:** Making synchronous Claude API calls that block the UI/render loop.
**Why bad:** Claude API calls take 1-5 seconds. Blocking the main thread freezes the viewport and kills the "living sculpture" feel.
**Instead:** Use the existing `EnrichmentWorker` pattern (QRunnable + QThreadPool) for all Claude API calls. Emit results via Qt signals.

### Anti-Pattern 4: Making Every Parameter Change Restart the Simulation
**What:** Calling `SimulationEngine.restart()` when creative parameters change.
**Why bad:** Restart resets all particle positions to initial state, destroying the current sculpture state. PBF parameters can be changed mid-simulation without instability.
**Instead:** All creative parameters should be hot-reloadable via uniform buffer updates. Only structural changes (particle count, initial positions) require restart.

### Anti-Pattern 5: Building a Node Editor for Parameter Mapping
**What:** Complex visual programming interface for connecting features to parameters.
**Why bad:** Over-engineering. The existing `MappingGraph` + `MappingConnection` model is sufficient. A node editor adds complexity without proportional value for an art tool where Claude handles the creative mapping.
**Instead:** Keep the existing patch bay UI. Let Claude suggest connections programmatically via structured output.

## New Module Specifications

### Module: `simulation/pbf_solver.py`

**Purpose:** Orchestrate the PBF compute pipeline.

**Interface:**
```python
class PBFSolver:
    def __init__(self, device, max_particles: int):
        """Build all PBF compute pipelines."""

    def step(self, particle_buffer: ParticleBuffer, params: SimulationParams):
        """Execute one PBF frame: predict -> hash -> solve -> finalize."""

    @property
    def solver_iterations(self) -> int:
        """Number of constraint solver iterations (1=gas, 4=liquid)."""
```

**Compute passes per frame (5 dispatches):**
1. `pbf_predict` -- apply external forces, compute predicted positions
2. `pbf_hash` -- build spatial hash from predicted positions (3 sub-passes: count, prefix-sum, scatter)
3. `pbf_density` -- compute density and constraint lambda per particle
4. `pbf_correct` -- compute and apply position corrections with artificial pressure
5. `pbf_finalize` -- compute velocity from position delta, vorticity confinement, XSPH viscosity

### Module: `api/claude_director.py`

**Purpose:** Generate creative sculpture parameters via Claude API.

**Interface:**
```python
class ClaudeDirector:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """Initialize with API credentials."""

    def generate_direction(
        self,
        image_path: str | None,
        clip_tags: list[tuple[str, float]],
        current_params: SimulationParams,
        user_mood: str | None = None,
    ) -> SculptureDirection:
        """Generate a creative parameter set. Blocking call."""

    def generate_variation(
        self,
        base_direction: SculptureDirection,
        variation_type: str,  # "subtle", "dramatic", "complement"
    ) -> SculptureDirection:
        """Generate a variation on an existing direction."""
```

**Relationship to existing `EnrichmentService`:** ClaudeDirector replaces the `suggest_mappings()` method with a more structured approach. `enrich_tags()` stays as-is for semantic enrichment. The two services can share the Anthropic client instance.

### Module: `api/parameter_schema.py`

**Purpose:** Pydantic models defining valid parameter ranges for Claude output.

**Key types:**
```python
class SculptureDirection(BaseModel):
    """Complete creative direction from Claude."""
    # All simulation params with validated ranges
    # Creative metadata (title, description, mood, reasoning)

class DirectionVariation(BaseModel):
    """A variation on an existing direction."""
    # Subset of params that changed + reasoning
```

### Module: `gui/panels/claude_panel.py`

**Purpose:** UI panel for Claude creative direction.

**Elements:**
- "Get Direction" button -- triggers Claude API call with current photo context
- Mood text input -- optional user guidance ("make it feel oceanic")
- Direction display -- shows Claude's title, description, reasoning
- "Apply" / "Apply with Crossfade" buttons
- "Variation" buttons -- subtle/dramatic/complement
- History list -- previous directions with one-click re-apply

## Modifications to Existing Components

### `simulation/engine.py` -- Major Refactor

- Remove SPH pipeline construction (`_build_sph_pipelines`, `_rebuild_sph_bind_group`)
- Remove forces pipeline (forces computation moves into PBF predict pass)
- Remove inline flow field from `integrate.wgsl` (moves to PBF predict)
- Add `PBFSolver` instantiation and delegation
- Keep double-buffered `ParticleBuffer` (PBF uses same pattern)
- Add `solver_iterations` parameter
- Remove `_performance_mode` flag (PBF is inherently fast)

### `simulation/buffers.py` -- Moderate Changes

- Remove `build_spatial_hash()` Python method (GPU hash replaces it)
- Add `predicted_positions_buffer` (PBF needs separate predicted vs current)
- Add `lambda_buffer` (constraint multipliers, f32 per particle)
- Add `delta_position_buffer` (position corrections, vec4 per particle)
- Keep existing `cell_counts`, `cell_offsets`, `sorted_indices` buffers

### `simulation/parameters.py` -- Add PBF Parameters

New fields:
```python
solver_iterations: int = 4        # PBF constraint iterations
rest_density_pbf: float = 6000.0  # target density (tuned for point cloud scale)
epsilon_pbf: float = 100.0        # relaxation parameter
artificial_pressure_k: float = 0.1  # tensile instability prevention
artificial_pressure_n: float = 4    # kernel power for artificial pressure
vorticity_epsilon: float = 0.01   # vorticity confinement strength
xsph_c: float = 0.01             # XSPH viscosity coefficient
```

Remove or deprecate: `gas_constant`, `pressure_strength` (SPH-specific).

### `simulation/shaders/` -- Replace WGSL Files

| Current File | Action | Replacement |
|-------------|--------|-------------|
| `integrate.wgsl` | **DELETE** | `pbf_predict.wgsl` + `pbf_finalize.wgsl` |
| `forces.wgsl` | **DELETE** | Force computation inlined in `pbf_predict.wgsl` |
| `sph.wgsl` | **DELETE** | `pbf_density.wgsl` + `pbf_correct.wgsl` |
| `noise.wgsl` | **KEEP** | Shared noise functions, imported by pbf_predict |
| `flow_field.wgsl` | **KEEP** | Referenced by pbf_predict for artistic flow forces |

### `gui/widgets/viewport_widget.py` -- Eliminate CPU Readback

Replace `_update_points_from_sim()` which does full CPU readback:

```python
# Current (slow): GPU -> CPU -> numpy -> new gfx.Buffer -> GPU
positions = self._sim_engine._particle_buffer.read_positions()
geo.positions = gfx.Buffer(positions.astype(np.float32))

# Target (fast): Update gfx.Buffer data in-place, let pygfx sync
# Or: Use compute output buffer directly via custom material
```

### `gui/main_window.py` -- Wire Claude Panel

- Add `ClaudePanel` to right sidebar (between Controls and Simulation)
- Wire `ClaudeDirector` signals to parameter crossfade system
- Add keyboard shortcut (Ctrl+D) for "Get Direction"

### `gui/theme.py` -- UI Rework

The UI rework is primarily a theme/layout concern, not architectural. Key changes:
- White/light viewport background option (user requested)
- Consistent spacing system (4px grid)
- Collapsible panel headers
- Better visual hierarchy with section dividers

## Scalability Considerations

| Concern | At 100K particles | At 1M particles | At 5M particles |
|---------|-------------------|-----------------|-----------------|
| PBF solver | 60fps easily | 30-60fps with 4 iterations | 15-30fps, reduce to 2 iterations |
| Spatial hash | Negligible | ~1ms GPU | ~3ms GPU |
| CPU readback | 0.4ms | 4ms (kills framerate) | 20ms (unusable) |
| GPU buffer sharing | 0ms | 0ms | 0ms |
| Claude API latency | N/A (async) | N/A (async) | N/A (async) |
| Memory (16GB VRAM) | ~50MB | ~500MB | ~2.5GB (fine) |

The 16GB VRAM on the RX 9060 XT is generous. PBF buffers per particle: position(16B) + predicted_pos(16B) + velocity(16B) + lambda(4B) + color(16B) + delta_pos(16B) = 84 bytes. At 5M particles = 420MB, well within budget.

## Build Order (Dependency-Aware)

This ordering minimizes wasted work and ensures each step produces testable results:

### Phase A: Fix Physics (blocks everything else)
1. **Fix double gravity/wind** in existing shaders (30 min fix, immediate improvement)
2. **Add force clamping** to existing integration shader (quick stability win)
3. **Implement PBF solver** with new WGSL shaders
4. **Per-frame GPU spatial hash** (required by PBF)
5. **Remove old SPH/forces pipeline** from SimulationEngine
6. **Add PBF parameters** to SimulationParams

### Phase B: Eliminate CPU Readback (blocks performance at scale)
7. **GPU buffer sharing** between compute and render
8. **Test at 1M+ particles** to validate performance

### Phase C: Claude Creative Direction (independent of physics)
9. **ParameterSchema** Pydantic models
10. **ClaudeDirector** with structured outputs
11. **ClaudePanel** UI
12. **Parameter crossfade** system
13. **Wire into MainWindow**

### Phase D: UI Rework (independent, can parallel with C)
14. **Theme rework** -- spacing, colors, viewport background
15. **Panel layout cleanup** -- collapsible sections, visual hierarchy
16. **Claude Panel integration** into sidebar

**Phase A must come first** because nothing else matters if the particles explode. Phase B should follow because it removes the performance ceiling. Phases C and D can run in parallel after A.

## Sources

- [Position Based Fluids -- Macklin & Muller 2013](https://mmacklin.com/pbf_sig_preprint.pdf) -- HIGH confidence, foundational paper
- [pygfx documentation](https://docs.pygfx.org/stable/basics.html) -- HIGH confidence, official docs
- [wgpu-py GitHub](https://github.com/pygfx/wgpu-py) -- HIGH confidence, official source
- [Claude Structured Outputs documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- HIGH confidence, official Anthropic docs
- [SPH CFL condition and timestep stability](https://www.simscale.com/blog/cfl-condition/) -- HIGH confidence, well-established numerical methods
- [DualSPHysics SPH formulation](https://github.com/DualSPHysics/DualSPHysics/wiki/3.-SPH-formulation) -- MEDIUM confidence, reference implementation
- [WebGPU Fluid Simulations -- Codrops](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/) -- MEDIUM confidence, contemporary WebGPU fluid work
- [Houdini FLIP Solver docs](https://www.sidefx.com/docs/houdini/nodes/dop/flipsolver.html) -- HIGH confidence, industry reference for CFL in fluid sim
- [XPBD GPU-based approach 2025](https://asmedigitalcollection.asme.org/IDETC-CIE/proceedings-abstract/IDETC-CIE2025/89213/V02BT02A008/1225800) -- MEDIUM confidence, confirms GPU XPBD viability
- [SPH tensile instability remedies](https://www.sciencedirect.com/science/article/abs/pii/S0965997824002552) -- MEDIUM confidence, academic source
- [Claude structured outputs with Pydantic](https://thomas-wiegold.com/blog/claude-api-structured-output/) -- MEDIUM confidence, verified against official docs
- [wgpu-py buffer mapping discussion](https://github.com/pygfx/wgpu-py/issues/114) -- HIGH confidence, official repo issue
