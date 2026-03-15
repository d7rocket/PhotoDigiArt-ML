# Phase 4: Stable Physics - Research

**Researched:** 2026-03-15
**Domain:** Real-time GPU particle physics -- Position Based Fluids, spatial hashing, force balance, organic motion
**Confidence:** HIGH

## Summary

Phase 4 replaces the current broken SPH simulation with a Position Based Fluids (PBF) solver that produces unconditionally stable, artistically controllable particle behavior. The existing simulation has five compounding bugs (stale spatial hash, double-counted gravity, unbounded forces, no CFL timestep, kernel coefficient explosion) that make parameter tuning impossible -- PBF eliminates these structural issues by solving positional constraints directly rather than accumulating forces.

The core technical challenge is implementing the full PBF pipeline as WGSL compute shaders: predict positions, GPU spatial hash rebuild (counting sort with atomics + prefix sum), density constraint solving (iterative), position correction with artificial pressure, and finalization with vorticity confinement and XSPH viscosity. On top of PBF, four additional systems create the "alive" aesthetic: per-particle home position attraction (elastic tether to photo-derived positions), curl noise flow fields (ocean current motion), breathing modulation (sine wave on home_strength and noise_amplitude), and force/velocity clamping (silent safety net).

**Primary recommendation:** Implement PBF as a new `pbf_solver.py` module with 6-8 new WGSL compute shaders, keep the existing `ParticleBuffer` pattern (extended with new buffers), and add home position + organic motion forces in the predict pass. Delete old SPH/forces shaders. All new parameters are hot-reloadable via uniform buffer -- no simulation restart needed for creative parameter changes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Home Position Feel**: Elastic tether model with feature-modulated strength (edge_map, depth_map). At rest, visible slow flow like embers. At max strength, micro-motion persists.
- **Organic Motion Character**: Ocean currents aesthetic (Refik Anadol reference). Curl noise at low frequency/high amplitude. Vortex confinement as subtle accent. Breathing ~4-6 second cycle. Photo features modulate noise parameters.
- **Default Solver Feel**: Default 2 iterations. Range 1-6. Changes crossfade over ~0.5s. Creative labeling ("Cohesion": "Ethereal" to "Liquid").
- **Stability vs Dynamism**: Home attraction dominant at defaults. Silent clamping (invisible to user). CFL-adaptive timestep purely internal. Zero CPU readback in simulation loop.

### Claude's Discretion
- PBF solver implementation details (relaxation parameter, constraint formulation)
- Exact clamping thresholds for force/velocity bounds
- CFL coefficient tuning
- GPU spatial hash implementation strategy (counting sort vs bitonic sort)
- Curl noise epsilon and sampling strategy refinements
- Breathing waveform shape (pure sine vs asymmetric)
- Feature modulation mapping functions (linear, sigmoid, etc.)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PHYS-01 | Per-particle home position attraction | Elastic tether spring force in PBF predict pass; home_positions buffer; feature-modulated strength via edge_map/depth_map texture sampling |
| PHYS-02 | PBF solver replaces SPH | Full PBF algorithm (Macklin & Muller 2013) with predict/hash/density/correct/finalize passes; unconditionally stable constraint resolution |
| PHYS-03 | GPU spatial hash rebuilt every frame | Counting sort with atomicAdd + tree-reduction prefix sum in WGSL; 3 compute dispatches (count, scan, scatter) |
| PHYS-04 | Force and velocity clamping | MAX_FORCE and MAX_VELOCITY constants applied silently in predict and finalize passes; prevents NaN/Inf propagation |
| PHYS-05 | CFL-adaptive timestep | GPU reduction to find max velocity; dt = min(dt_target, CFL_COEFF * h / v_max); purely internal |
| PHYS-06 | Curl noise flow fields | Refined curl noise using existing Perlin/FBM infrastructure; low frequency, high amplitude for ocean-current feel |
| PHYS-07 | Vortex confinement | omega = curl(velocity), eta = gradient(|omega|), f_vorticity = epsilon * (normalize(eta) x omega); added in finalize pass |
| PHYS-08 | Breathing modulation | Sine wave on home_strength and noise_amplitude; ~4-6 second cycle; applied per-frame in uniform buffer update |
| PHYS-09 | Solver iterations as creative control | iterations parameter (1-6) in PBF constraint loop; 1=gas/wispy, 2=default, 4+=liquid/cohesive; crossfade via parameter interpolation |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| wgpu-py | 0.31.0 | GPU compute shaders (WGSL) + buffer management | Already in stack; compute + render on same device; AMD Vulkan/DX12 support |
| numpy | 1.26+ | Initial position/color array preparation on CPU | Already in stack; used for buffer upload only, not per-frame |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PySide6 | 6.8+ | GUI parameter panels for new physics controls | Wiring new sliders (cohesion, breathing_rate) to simulation params |
| pygfx | 0.16.0 | Rendering (reads compute output buffers) | Unchanged -- zero-copy buffer sharing preserved |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WGSL compute | Taichi Lang | No GPU buffer interop with wgpu/pygfx; CPU roundtrip kills performance |
| WGSL compute | NVIDIA Warp | CUDA-only; dead on AMD RDNA 4 |
| Custom PBF | PySPH library | Scientific focus; no real-time rendering integration; Python loops |

**Installation:**
No new dependencies. Phase 4 uses only existing packages.

## Architecture Patterns

### Recommended Project Structure
```
apollo7/simulation/
  engine.py              # MODIFIED: delegate to PBFSolver, remove SPH pipelines
  buffers.py             # MODIFIED: add home_positions, predicted_positions, lambda, delta_p buffers
  parameters.py          # MODIFIED: add PBF + home + breathing params, expand uniform layout
  pbf_solver.py          # NEW: PBF solver orchestration (build pipelines, dispatch passes)
  shaders/
    __init__.py          # UNCHANGED
    noise.wgsl           # KEEP: shared Perlin/simplex/FBM functions
    flow_field.wgsl      # KEEP: feature-texture-driven flow (referenced by predict pass)
    pbf_predict.wgsl     # NEW: apply forces (home attraction, curl noise, gravity), predict positions
    pbf_hash_count.wgsl  # NEW: count particles per cell (atomicAdd)
    pbf_hash_scan.wgsl   # NEW: parallel prefix sum on cell_counts -> cell_offsets
    pbf_hash_scatter.wgsl# NEW: scatter particles into sorted_indices by cell
    pbf_density.wgsl     # NEW: compute density constraint C_i and lambda_i
    pbf_correct.wgsl     # NEW: compute position corrections delta_p with artificial pressure
    pbf_finalize.wgsl    # NEW: velocity from dx, vorticity confinement, XSPH, velocity clamping
    integrate.wgsl       # DELETE (replaced by pbf_predict + pbf_finalize)
    forces.wgsl          # DELETE (forces inlined in pbf_predict)
    sph.wgsl             # DELETE (replaced by pbf_density + pbf_correct)
```

### Pattern 1: PBF Solver Algorithm (Macklin & Muller 2013)

**What:** Position Based Fluids solves density constraints by directly adjusting particle positions, rather than computing forces and integrating. This makes it unconditionally stable -- positions are corrected to satisfy constraints, so particles cannot explode.

**When to use:** Every simulation frame.

**Core Algorithm (per frame):**
```
1. PREDICT PASS (pbf_predict.wgsl):
   for each particle i:
     f_ext = home_attraction(x_i, home_i) + curl_noise(x_i, t) + gravity + wind
     v_i = v_i + dt * f_ext
     v_i = clamp(v_i, MAX_VELOCITY)
     x_pred_i = x_i + dt * v_i

2. HASH BUILD (3 dispatches):
   a. COUNT:  atomicAdd(cell_counts[hash(x_pred_i)], 1)
   b. SCAN:   parallel prefix sum -> cell_offsets
   c. SCATTER: sorted_indices[cell_offsets[hash(x_pred_i)] + local_offset] = i

3. CONSTRAINT LOOP (solver_iterations times):
   a. DENSITY (pbf_density.wgsl):
      for each particle i:
        rho_i = sum_j(m_j * W_poly6(x_pred_i - x_pred_j))
        C_i = (rho_i / rho_0) - 1
        lambda_i = -C_i / (sum_k(|grad_pk C_i|^2) + epsilon)

   b. CORRECT (pbf_correct.wgsl):
      for each particle i:
        dp_i = (1/rho_0) * sum_j((lambda_i + lambda_j + s_corr) * grad W_spiky)
        x_pred_i += dp_i

4. FINALIZE PASS (pbf_finalize.wgsl):
   for each particle i:
     v_i = (x_pred_i - x_i) / dt
     apply vorticity confinement
     apply XSPH viscosity
     v_i = clamp(v_i, MAX_VELOCITY)
     x_i = x_pred_i
```

**Canonical Parameter Values (from Macklin, Stanford CS348C):**

| Parameter | Symbol | Value | Notes |
|-----------|--------|-------|-------|
| Kernel radius | h | 0.1 | Must match spatial hash cell size |
| Rest density | rho_0 | 6378.0 | Macklin's recommended value; tune for point cloud scale |
| Relaxation epsilon | epsilon | 600.0 | CFM parameter; prevents singularity with few neighbors |
| Solver iterations | n_iter | 2 (default) | 1=gas, 2=fluid, 4+=liquid, 6=near-solid |
| Artificial pressure k | s_corr | 0.0001 | Tensile instability fix strength |
| Artificial pressure delta_q | delta_q | 0.03 | Reference distance for artificial pressure |
| Artificial pressure exponent | n | 4 | Sharpness of artificial pressure kernel |
| XSPH viscosity | c | 0.01 | Velocity field smoothing (keep <= 0.01) |
| Vorticity confinement | eps_vort | 0.01 | Re-inject dissipated rotational energy |
| Timestep | dt | 0.0083 | ~120 substeps/s; with CFL may be smaller |

**Confidence:** HIGH. PBF paper has 1000+ citations, algorithm maps directly to compute shaders, values from the algorithm's creator.

### Pattern 2: GPU Spatial Hash via Counting Sort

**What:** Rebuild the spatial hash entirely on GPU every frame using three compute dispatches: count, scan, scatter. Uses `atomic<u32>` for thread-safe cell counting.

**When to use:** Every frame, between predict and density passes.

**Architecture:**

Pass 1 -- COUNT (`pbf_hash_count.wgsl`):
```wgsl
@group(0) @binding(0) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read_write> cell_counts: array<atomic<u32>>;

@compute @workgroup_size(256)
fn hash_count(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    if (idx >= arrayLength(&predicted_positions)) { return; }
    let pos = predicted_positions[idx].xyz;
    let cell = pos_to_cell(pos, cell_size);
    let hash = cell_to_hash(cell);
    atomicAdd(&cell_counts[hash], 1u);
}
```

Pass 2 -- SCAN (`pbf_hash_scan.wgsl`):
Tree-reduction parallel prefix sum. Workgroup size 256, processes 512 elements per group. For 128^3 = 2M cells, needs 2M/512 = ~4096 workgroups in first level, then ~8 workgroups for second level, then 1 final fixup dispatch. Three sub-dispatches total.

Pass 3 -- SCATTER (`pbf_hash_scatter.wgsl`):
```wgsl
@group(0) @binding(0) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read_write> cell_offsets: array<atomic<u32>>;
@group(0) @binding(2) var<storage, read_write> sorted_indices: array<u32>;

@compute @workgroup_size(256)
fn hash_scatter(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    if (idx >= arrayLength(&predicted_positions)) { return; }
    let pos = predicted_positions[idx].xyz;
    let cell = pos_to_cell(pos, cell_size);
    let hash = cell_to_hash(cell);
    let offset = atomicAdd(&cell_offsets[hash], 1u);
    sorted_indices[offset] = idx;
}
```

**Key detail:** The SCAN pass must output to `cell_offsets`. SCATTER then uses `atomicAdd` on cell_offsets to get unique write positions (each thread atomically increments to get its slot). This requires cell_offsets to be copied from the scan output to an atomic-typed buffer, OR the scatter pass uses a separate write_positions buffer initialized from scan output.

**Confidence:** HIGH. Counting sort spatial hash is the standard GPU approach. WGSL atomics (`atomic<u32>`, `atomicAdd`) are confirmed in the spec. Prefix sum tree-reduction works on all WebGPU backends including Metal.

### Pattern 3: Home Position Attraction (Elastic Tether)

**What:** Each particle has a stored home position (its photo-derived initial position). A spring force pulls it back, modulated by feature textures.

**Implementation in pbf_predict.wgsl:**
```wgsl
fn compute_home_force(pos: vec3<f32>, home: vec3<f32>,
                       edge_val: f32, depth_val: f32,
                       home_strength: f32, breathing_mod: f32) -> vec3<f32> {
    let displacement = home - pos;
    let dist = length(displacement);
    if (dist < 0.0001) { return vec3<f32>(0.0); }

    let dir = displacement / dist;

    // Feature modulation: edges hold tighter, flat areas drift more
    let feature_mod = mix(0.5, 1.5, edge_val);  // sigmoid or linear

    // Breathing modulation applied to home_strength
    let effective_strength = home_strength * breathing_mod * feature_mod;

    // Elastic spring force (linear spring with distance)
    let force = dir * effective_strength * dist;

    return force;
}
```

**Buffer addition:** `home_positions` buffer (vec4<f32> per particle, xyz = home position, w = feature strength). Uploaded once at init alongside particle positions. Never changes during simulation.

**Confidence:** HIGH. Simple spring force, well-understood. Feature modulation via existing edge_map/depth_map textures.

### Pattern 4: Breathing Modulation (CPU-side Uniform Update)

**What:** A sine wave modulates home_strength and noise_amplitude each frame, creating a slow "inhale/exhale" cycle.

**Implementation in engine.py (Python side):**
```python
def _compute_breathing(self, time: float) -> float:
    """Compute breathing modulation factor [0.85, 1.15] range."""
    cycle = 2 * math.pi / self._params.breathing_period  # 4-6 seconds
    return 1.0 + self._params.breathing_amplitude * math.sin(time * cycle)
```

This modulation factor is written into the uniform buffer each frame. The shader reads it and applies it to home_strength and noise_amplitude. Pure CPU computation, negligible cost.

**Confidence:** HIGH. Sine wave modulation is trivial. Applied via uniform buffer, zero GPU overhead.

### Pattern 5: CFL-Adaptive Timestep

**What:** Compute maximum particle velocity on GPU, then compute safe timestep on CPU before next frame.

**GPU max velocity reduction:**
```wgsl
// In pbf_finalize.wgsl (or separate reduction pass):
// Encode max velocity as u32 for atomicMax:
let speed = length(v_i);
let speed_bits = bitcast<u32>(speed);
atomicMax(&max_velocity_atomic, speed_bits);
```

**CPU-side CFL computation:**
```python
def _compute_adaptive_dt(self, max_velocity: float) -> float:
    CFL_COEFF = 0.4  # Conservative CFL number
    h = self._params.kernel_radius
    dt_cfl = CFL_COEFF * h / max(max_velocity, 0.001)
    return min(self._params.dt_target, dt_cfl)
```

**Important:** Reading max_velocity requires a GPU readback of a single u32. This is acceptable (4 bytes, not 500K * 16 bytes). Alternatively, use a conservative fixed substep count: if dt_target/dt_cfl > 1, do multiple substeps.

**Confidence:** MEDIUM. The algorithm is standard, but the `bitcast<u32>` + `atomicMax` trick for float max-reduction needs validation on AMD. Fallback: use fixed substeps with conservative dt.

### Anti-Patterns to Avoid

- **Trying to fix SPH with parameter tuning:** The instability is structural (5 bugs), not parametric. Replace SPH entirely.
- **CPU spatial hash rebuild:** Even if "just for now," the Python for-loop over 500K particles is ~200ms. GPU hash is ~1ms.
- **Rebuilding bind groups every frame unconditionally:** Only rebuild when buffer identity changes (after swap). Cache bind groups for each orientation.
- **Making solver_iterations require simulation restart:** PBF naturally handles iteration count changes mid-simulation. Make it hot-reloadable.
- **Clearing force buffers via CPU zero-upload:** Use a compute shader to write zeros, or restructure PBF to not need separate force buffers (PBF accumulates position corrections, not forces).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fluid simulation | Custom SPH force solver | PBF constraint solver (Macklin 2013) | Unconditionally stable; SPH diverges without CFL compliance |
| Spatial neighbor search | CPU Python for-loop hash | GPU counting sort with atomics | 200x faster on GPU; required every frame |
| Prefix sum | Custom scan algorithm | Tree-reduction work-efficient scan | Standard algorithm; works on all WebGPU backends (no decoupled look-back, not supported on Metal) |
| Noise functions | New noise implementation | Existing noise.wgsl (Perlin, simplex, FBM) | Already implemented, tested, and working |
| Parameter interpolation | Manual lerp per frame | SimulationParams.with_update + crossfade timer | Consistent, covers all params, already has the immutable update pattern |

**Key insight:** PBF is specifically designed for real-time GPU particle art. It solves the exact problem (particles exploding) at the algorithmic level. No amount of engineering on top of SPH will achieve the same result.

## Common Pitfalls

### Pitfall 1: Prefix Sum Not Portable Across WebGPU Backends
**What goes wrong:** Decoupled look-back prefix sum (fastest algorithm) requires device-scope atomic barriers, which Metal (and therefore WebGPU) does not support.
**Why it happens:** WebGPU inherits Metal's limitation on cross-workgroup synchronization.
**How to avoid:** Use tree-reduction parallel scan (Blelloch-style). It requires 3 dispatch passes instead of 1, but works on all backends. For 2M cells, total scan time is still under 1ms.
**Warning signs:** Prefix sum produces wrong results on macOS/Metal but works on Windows/Vulkan.

### Pitfall 2: Atomic Buffer Type Mismatch
**What goes wrong:** `cell_counts` declared as `array<u32>` but used with `atomicAdd`. WGSL requires the buffer type to be `array<atomic<u32>>` for atomic operations.
**Why it happens:** Easy to forget that WGSL atomics are strictly typed -- you cannot atomicAdd on a regular u32.
**How to avoid:** Declare counting buffers as `array<atomic<u32>>` in WGSL. On the Python/wgpu side, the buffer is still created as regular storage -- the atomic typing is shader-side only.
**Warning signs:** Shader compilation errors mentioning atomic type mismatch.

### Pitfall 3: Double-Counting Forces (Existing Bug)
**What goes wrong:** Gravity and wind are computed in both forces.wgsl and integrate.wgsl, doubling their effect.
**Why it happens:** The multi-pass architecture accumulates forces across passes without tracking what each pass contributes.
**How to avoid:** In the new PBF architecture, ALL external forces are computed in a single predict pass. No separate forces shader. One place for gravity, wind, home attraction, curl noise.
**Warning signs:** Particles fall twice as fast as expected; reducing gravity by half gives "correct" behavior.

### Pitfall 4: Spatial Hash Cell Size vs Kernel Radius Mismatch
**What goes wrong:** If cell_size != kernel_radius (h), the 3x3x3 neighbor search misses particles within the kernel radius, or searches too many empty cells.
**Why it happens:** Cell size and kernel radius are set independently.
**How to avoid:** Always set `cell_size = h` (kernel radius). The 3x3x3 search then guarantees all particles within distance h are found.
**Warning signs:** Density computation returns wrong values; particles pass through each other.

### Pitfall 5: Buffer Clearing Between Frames
**What goes wrong:** Cell counts from the previous frame leak into the current frame's hash, producing incorrect neighbor data.
**Why it happens:** `cell_counts` buffer is not zeroed before the counting pass.
**How to avoid:** Add a buffer-clear compute dispatch (or CPU zero-upload for cell_counts) before each hash build. For 2M cells * 4 bytes = 8MB, a GPU compute clear is preferable.
**Warning signs:** Particle counts per cell grow monotonically frame over frame; neighbor search returns too many particles.

### Pitfall 6: NaN Propagation from Division by Zero
**What goes wrong:** Lambda computation divides by `(sum_grad_C^2 + epsilon)`. If epsilon is too small and all neighbors have zero gradient, lambda becomes NaN, which propagates to all particles via the correction pass.
**Why it happens:** Particles at the edge of the simulation with few/no neighbors.
**How to avoid:** Use a substantial epsilon (600.0 per Macklin's recommendation). Add NaN guard: `if (isnan(lambda_i) || isinf(lambda_i)) { lambda_i = 0.0; }`. Add similar guards in position correction.
**Warning signs:** Simulation runs fine for a while then suddenly all particles snap to (0,0,0) or disappear.

## Code Examples

### Uniform Buffer Extension (parameters.py)

The current 112-byte uniform buffer (7 x vec4) needs extension for PBF + home + breathing params:

```python
# New SimParams WGSL layout (extended):
# vec4 0: noise_frequency, noise_amplitude, noise_octaves, turbulence_scale
# vec4 1: home_strength, breathing_rate, breathing_amplitude, breathing_mod (computed)
# vec4 2: kernel_radius, rest_density, epsilon_pbf, solver_iterations
# vec4 3: artificial_pressure_k, artificial_pressure_n, delta_q, xsph_c
# vec4 4: vorticity_epsilon, max_force, max_velocity, dt
# vec4 5: gravity.xyz, damping
# vec4 6: wind.xyz, speed
# vec4 7: time, cell_size, particle_count, _pad
# Total: 8 * 16 = 128 bytes

# NOTE: Old SPH params (viscosity, pressure_strength, surface_tension,
# attraction_strength, repulsion_strength, repulsion_radius, smoothing_radius,
# rest_density, gas_constant) are REMOVED. PBF replaces them entirely.
```

### Home Position Buffer Addition (buffers.py)

```python
# In ParticleBuffer.__init__:
# Home positions: vec4<f32> per particle (xyz = home pos, w = feature_strength)
self._home_positions_buf = device.create_buffer(
    size=max_particles * 16, usage=aux_usage
)

# Predicted positions: vec4<f32> per particle (PBF needs separate predicted vs current)
self._predicted_buf = device.create_buffer(
    size=max_particles * 16, usage=aux_usage
)

# Lambda: f32 per particle (constraint multiplier)
self._lambda_buf = device.create_buffer(
    size=max_particles * 4, usage=aux_usage
)

# Delta position: vec4<f32> per particle (position corrections)
self._delta_p_buf = device.create_buffer(
    size=max_particles * 16, usage=aux_usage
)
```

### PBF Solver Orchestration (pbf_solver.py)

```python
class PBFSolver:
    """Orchestrates PBF compute pipeline per frame."""

    def step(self, particle_buffer, params, time):
        """Execute one PBF frame."""
        n = particle_buffer.particle_count

        # 1. Predict positions (forces + Euler step)
        self._dispatch(self._predict_pipeline, self._predict_bg, n)

        # 2. Build spatial hash from predicted positions
        self._clear_cell_counts(particle_buffer)
        self._dispatch(self._hash_count_pipeline, self._hash_count_bg, n)
        self._dispatch_prefix_sum(particle_buffer)  # multiple sub-dispatches
        self._dispatch(self._hash_scatter_pipeline, self._hash_scatter_bg, n)

        # 3. Solve constraints (iterate)
        iterations = int(params.solver_iterations)
        for _ in range(iterations):
            self._dispatch(self._density_pipeline, self._density_bg, n)
            self._dispatch(self._correct_pipeline, self._correct_bg, n)

        # 4. Finalize (velocity from dx, vorticity, XSPH, clamping)
        self._dispatch(self._finalize_pipeline, self._finalize_bg, n)

        # 5. Swap buffers (current = predicted)
        particle_buffer.swap()
```

### Vorticity Confinement (in pbf_finalize.wgsl)

```wgsl
// Compute vorticity omega = curl(velocity field) at particle i
fn compute_vorticity(pos_i: vec3<f32>, vel_i: vec3<f32>) -> vec3<f32> {
    var omega = vec3<f32>(0.0);
    // Sum over neighbors j:
    // omega += (v_j - v_i) x grad_W(x_i - x_j, h)
    // (neighbor loop using spatial hash)
    return omega;
}

// Compute vorticity confinement force
fn vorticity_confinement(pos_i: vec3<f32>, omega_i: vec3<f32>) -> vec3<f32> {
    // eta = gradient(|omega|) at particle i (finite difference from neighbors)
    let eta = compute_omega_gradient(pos_i);  // vec3 pointing toward higher vorticity
    let eta_len = length(eta);
    if (eta_len < 0.0001) { return vec3<f32>(0.0); }
    let N = eta / eta_len;  // normalized direction
    return params.vorticity_epsilon * cross(N, omega_i);
}
```

### XSPH Viscosity (in pbf_finalize.wgsl)

```wgsl
fn compute_xsph(pos_i: vec3<f32>, vel_i: vec3<f32>) -> vec3<f32> {
    var v_xsph = vec3<f32>(0.0);
    // Sum over neighbors j:
    // v_xsph += (v_j - v_i) * W_poly6(x_i - x_j, h)
    // (neighbor loop using spatial hash)
    return v_xsph * params.xsph_c;
}

// Applied in finalize:
// v_i = v_i + vorticity_force * dt + xsph_correction
```

## State of the Art

| Old Approach (v1.0) | New Approach (v2.0 Phase 4) | Impact |
|----------------------|-----------------------------|--------|
| SPH force-based solver | PBF position-based solver | Unconditionally stable; no explosion possible |
| CPU spatial hash at init only | GPU counting sort hash every frame | Correct neighbor data; ~200x faster |
| No home positions | Elastic tether to photo-derived positions | Coherent sculptural forms indefinitely |
| No force/velocity clamping | Silent MAX_FORCE / MAX_VELOCITY caps | No NaN, Inf, or runaway values |
| Fixed dt = 0.016 | CFL-adaptive dt <= 0.016 | Stable under all velocity conditions |
| Basic curl noise (existing) | Curl noise + vortex confinement + breathing | Ocean-current organic living motion |
| Double-counted gravity/wind | Single predict pass for all forces | Correct force accumulation |
| SPH params (gas_constant, etc.) | PBF params (iterations, rest_density, epsilon) | Artistically intuitive controls |

**Deprecated/outdated:**
- `sph.wgsl`: Entire file deleted; PBF replaces SPH
- `forces.wgsl`: Entire file deleted; forces inlined in PBF predict pass
- `integrate.wgsl`: Entire file deleted; split into PBF predict + finalize
- `gas_constant`, `pressure_strength`, `surface_tension` params: Removed; PBF uses `solver_iterations`, `rest_density`, `epsilon_pbf`

## Open Questions

1. **Prefix sum for 2M cells -- exact dispatch sizing**
   - What we know: Tree-reduction works, 256 workgroup size, 512 elements per group. 2M cells needs 4096 first-level groups.
   - What's unclear: Whether a 3-level hierarchical scan is needed or 2 levels suffice. 4096 block sums need 8 groups at the second level, which fits in a single dispatch.
   - Recommendation: Implement 2-level scan first (handles up to 512 * 512 = 262K blocks = 134M cells). 2M cells is well within range.

2. **rest_density tuning for point cloud scale**
   - What we know: Macklin recommends 6378.0 for physically-scaled simulations.
   - What's unclear: Apollo 7 point clouds are not physically scaled -- positions range roughly [-50, 50]. The rest_density value depends on inter-particle spacing and kernel radius.
   - Recommendation: Start with Macklin's value, tune experimentally. The key relationship is: rest_density should produce C_i near 0 for a uniformly distributed particle cloud at the target spacing.

3. **bitcast<u32> for float atomicMax on AMD**
   - What we know: This is a standard GPU trick for float max via integer atomics.
   - What's unclear: Whether wgpu-py on AMD Vulkan handles bitcast + atomicMax correctly.
   - Recommendation: Implement and test. Fallback: read back a small buffer (one u32 per workgroup) and compute max on CPU. For 500K particles / 256 = 2K workgroups, this is a 8KB readback.

4. **Optimal grid size for spatial hash**
   - What we know: Current grid is 128^3 = 2M cells. Most cells are empty.
   - What's unclear: Whether a smaller grid (64^3 = 262K cells) would suffice and reduce prefix sum cost.
   - Recommendation: Start with 128^3 (proven). If prefix sum becomes a bottleneck, reduce to 64^3. The cell_size = kernel_radius constraint determines effective resolution.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | None (default pytest discovery) |
| Quick run command | `python -m pytest tests/test_simulation_engine.py tests/test_simulation_params.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PHYS-01 | Home position attraction keeps particles near home | integration | `python -m pytest tests/test_pbf_solver.py::test_home_attraction_holds_form -x` | Wave 0 |
| PHYS-02 | PBF solver runs without explosion for 1000+ frames | integration | `python -m pytest tests/test_pbf_solver.py::test_stability_1000_frames -x` | Wave 0 |
| PHYS-03 | GPU spatial hash produces correct neighbor data | unit | `python -m pytest tests/test_pbf_solver.py::test_gpu_spatial_hash_correctness -x` | Wave 0 |
| PHYS-04 | Force/velocity clamping prevents NaN/Inf | unit | `python -m pytest tests/test_pbf_solver.py::test_no_nan_inf_after_1000_frames -x` | Wave 0 |
| PHYS-05 | CFL-adaptive timestep adjusts under high velocity | unit | `python -m pytest tests/test_pbf_solver.py::test_cfl_timestep_adapts -x` | Wave 0 |
| PHYS-06 | Curl noise produces non-zero divergence-free flow | unit | `python -m pytest tests/test_pbf_solver.py::test_curl_noise_produces_flow -x` | Wave 0 |
| PHYS-07 | Vorticity confinement adds rotational energy | integration | `python -m pytest tests/test_pbf_solver.py::test_vorticity_confinement_effect -x` | Wave 0 |
| PHYS-08 | Breathing modulation oscillates home_strength | unit | `python -m pytest tests/test_simulation_params.py::test_breathing_modulation -x` | Wave 0 |
| PHYS-09 | Solver iterations 1 vs 4 produce visibly different behavior | integration | `python -m pytest tests/test_pbf_solver.py::test_iteration_count_affects_density -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_pbf_solver.py tests/test_simulation_params.py tests/test_simulation_engine.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pbf_solver.py` -- covers PHYS-01 through PHYS-09 (new file, all PBF-specific tests)
- [ ] Update `tests/test_simulation_params.py` -- add tests for new PBF params (home_strength, breathing_rate, solver_iterations, kernel_radius)
- [ ] Update `tests/test_simulation_engine.py` -- update to reflect PBF pipeline (remove SPH-specific tests, add PBF lifecycle tests)

*(Existing test infrastructure covers basic engine lifecycle, param packing, and buffer management. New tests needed for PBF-specific behavior.)*

## Sources

### Primary (HIGH confidence)
- [Position Based Fluids -- Macklin & Muller 2013](https://mmacklin.com/pbf_sig_preprint.pdf) -- foundational PBF algorithm, pseudocode, equations
- [Stanford CS348C PBF Assignment -- Macklin's parameter values](https://graphics.stanford.edu/courses/cs348c-20-winter/HW_PBF_Houdini/index.html) -- canonical parameter values (rest_density=6378, epsilon=600, etc.)
- [WGSL Spec -- Atomic Types](https://google.github.io/tour-of-wgsl/types/atomics/atomic-types/) -- atomic<u32>, atomicAdd, atomicMax confirmed in spec
- [Prefix Sum on Portable Compute Shaders -- Raph Levien](https://raphlinus.github.io/gpu/2021/11/17/prefix-sum-portable.html) -- confirmed decoupled look-back NOT portable; tree reduction recommended
- [WebGPU Unleashed -- Prefix Sum](https://shi-yan.github.io/webgpuunleashed/Compute/prefix_sum.html) -- 3-pass tree-reduction prefix sum with WGSL code, workgroup_size(256)
- Direct codebase analysis of `engine.py`, `buffers.py`, `parameters.py`, `integrate.wgsl`, `forces.wgsl`, `sph.wgsl` -- existing architecture and bugs

### Secondary (MEDIUM confidence)
- [Vorticity Confinement -- Wikipedia](https://en.wikipedia.org/wiki/Vorticity_confinement) -- formula: F = epsilon * (N x omega)
- [Brandon Nguyen PBF Implementation](https://people.engr.tamu.edu/sueda/courses/CSCE450/2022F/projects/Brandon_Nguyen/index.html) -- 4-6 iterations recommended; float precision critical on GPU
- [CFL Condition -- SimScale](https://www.simscale.com/blog/cfl-condition/) -- CFL formula and adaptive timestep
- [WebGPU Compute Shaders -- Histogram (atomicAdd pattern)](https://webgpufundamentals.org/webgpu/lessons/webgpu-compute-shaders-histogram.html) -- confirmed WGSL atomicAdd pattern

### Tertiary (LOW confidence)
- GPU max-reduction via bitcast<u32> + atomicMax -- standard GPU trick but untested on AMD/wgpu-py specifically
- RDNA 4 wavefront size (32 vs 64) impact on workgroup_size(256) -- no direct testing evidence

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing packages proven in v1.0
- Architecture: HIGH -- PBF algorithm is foundational (1000+ citations), maps directly to compute shaders, parameter values from algorithm creator
- Pitfalls: HIGH -- 5 existing bugs identified via direct code review, PBF fixes all structurally
- GPU spatial hash: HIGH -- counting sort + prefix sum is standard; atomics confirmed in WGSL spec
- CFL adaptive timestep: MEDIUM -- algorithm is standard, but float atomicMax via bitcast needs AMD validation
- Vorticity confinement: MEDIUM -- formula is well-known, but particle-based approximation quality depends on neighbor density

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain -- PBF algorithm unchanged since 2013)
