# Pitfalls Research

**Domain:** Generative art pipeline — fluid particle simulation, UI rework, LLM integration, AMD GPU compute
**Researched:** 2026-03-15
**Confidence:** HIGH (based on direct codebase analysis + domain knowledge)

## Critical Pitfalls

### Pitfall 1: The "Explosion Problem" — SPH Kernel Coefficients Blow Up at Small Smoothing Radii

**What goes wrong:**
Particles fly apart instantly or within a few frames, producing a rapidly expanding cloud instead of coherent fluid-like motion. This is the primary v1.0 failure mode.

**Why it happens:**
Direct analysis of `sph.wgsl` reveals the root cause. The SPH kernels use standard formulas with denominators containing `pow(h, 9)` (poly6) and `pow(h, 6)` (spiky). With `smoothing_radius = 0.1`:

- `h^9 = 1e-9`, making poly6 coefficient = `315 / (64 * pi * 1e-9)` = ~1.56e9
- `h^6 = 1e-6`, making spiky coefficient = `45 / (pi * 1e-6)` = ~1.43e7

These astronomical kernel values produce enormous density estimates, which feed into pressure calculation `gas_constant * (density - rest_density)`. With `gas_constant = 2.0` and `rest_density = 1000.0`, if computed density reaches 1e6+ (easily happens with these coefficients), pressure forces are in the millions. No amount of damping at 0.99 per frame can counteract forces of that magnitude.

Additionally, the attraction force in `forces.wgsl` uses `attraction_strength / (dist^2 + 0.01)` with no upper clamp. When particles are close, this produces unbounded forces that compound with the SPH explosion.

**How to avoid:**
1. **Normalize kernel coefficients to your spatial scale.** If your world uses units where particles are 0.01-1.0 apart, set `smoothing_radius` to match (0.2-0.5 range). Or pre-scale the kernel output.
2. **Clamp total force magnitude.** Add `force = normalize(force) * min(length(force), MAX_FORCE)` before integration. A reasonable MAX_FORCE is 10-50x the gravity magnitude.
3. **Use adaptive timestep or substeps.** If `max_acceleration * dt > threshold`, subdivide the step.
4. **Separate SPH parameter tuning from rendering scale.** SPH works well when `h` is ~2-4x the mean inter-particle spacing. Compute mean spacing first, then derive `h`.

**Warning signs:**
- Particles visibly accelerating each frame without bound
- Velocity magnitudes growing exponentially (add a debug readback: if `max(|vel|) > 100`, something is wrong)
- Simulation looks fine for 0.5s then suddenly explodes
- Reducing particle count makes the problem worse (fewer particles = higher density per neighbor = larger forces)

**Phase to address:**
Phase 1 (Physics Fix) — this is THE blocker. Nothing else matters if particles explode.

---

### Pitfall 2: Stale Spatial Hash Causes Ghost Forces and Missed Collisions

**What goes wrong:**
The spatial hash grid used for neighbor lookups becomes incorrect as particles move, causing forces to be computed against wrong neighbors or missing nearby particles entirely. This produces erratic, chaotic motion even when force magnitudes are correct.

**Why it happens:**
In the current codebase, `build_spatial_hash()` in `buffers.py` runs only at `initialize()` and `restart()` — not per-frame. After the first simulation step, particles have moved but the spatial hash still reflects their initial positions. The forces shader queries neighbors based on stale cell assignments:

```
# buffers.py line 146-148:
# "Only needs to run at simulation start/restart, not per-frame."
# This comment documents the bug — it DOES need to run per-frame.
```

This means:
- Particle A moves into Particle B's space, but the hash says they are in different cells — no repulsion fires
- Two particles that have moved apart still show as neighbors — attraction forces pull on phantoms
- The further simulation progresses from init, the more wrong the hash becomes

**How to avoid:**
1. **Rebuild spatial hash on GPU every frame.** Move the hash construction into a compute shader pass (prefix sum on GPU). This is standard for GPU particle sims.
2. **Use a GPU-friendly hash like counting sort.** Steps: (a) compute cell hash per particle, (b) count particles per cell (atomic add), (c) prefix sum for offsets, (d) scatter particles to sorted array. All can be done in 3-4 compute dispatches.
3. **Alternative: skip spatial hash and use a simpler radius-based check** for < 100K particles, or use a BVH for larger counts.

**Warning signs:**
- Forces seem "sticky" — particles that should repel keep clumping
- Motion becomes increasingly chaotic over time (diverges from first few seconds)
- Restarting sim (which rebuilds hash) temporarily fixes the behavior

**Phase to address:**
Phase 1 (Physics Fix) — must be solved alongside the kernel coefficient issue.

---

### Pitfall 3: Force Accumulation Without Clamping Creates Feedback Loops

**What goes wrong:**
Multiple force systems (flow field, external forces, SPH pressure, SPH viscosity, gravity, wind, attraction, repulsion) all accumulate into a single force vector with no maximum cap. When several forces align, particles receive catastrophically large accelerations.

**Why it happens:**
In `integrate.wgsl` line 258: `let total_force = force + ext_force + sph_f;` — this is a raw sum with no magnitude limit. The forces pass and SPH pass each write unbounded values, and the integration pass sums them all. With the SPH kernel issue (Pitfall 1), this sum can easily reach 1e6+.

Furthermore, `forces.wgsl` loops over all neighbors in 27 cells accumulating attraction/repulsion. In a dense region with 100+ neighbors, even small per-neighbor forces sum to large totals. There is no per-neighbor or per-cell force budget.

**How to avoid:**
1. **Clamp force magnitude before integration.** After summing all forces: `total_force = total_force * min(1.0, MAX_FORCE / length(total_force))`
2. **Clamp velocity after integration.** `vel = vel * min(1.0, MAX_VELOCITY / length(vel))`
3. **Budget force contributions.** Limit each force system's contribution: flow field max N, SPH max M, attraction max P.
4. **Use velocity Verlet instead of symplectic Euler** for better energy conservation.

**Warning signs:**
- Adding a new force type makes previously stable sim explode
- Particles hit boundary constantly (forces launching them to the edge)
- Sim works with 1 force type, breaks when multiple are active

**Phase to address:**
Phase 1 (Physics Fix) — implement force clamping as part of the integration rework.

---

### Pitfall 4: AMD RDNA 4 / WebGPU Compute Gotchas

**What goes wrong:**
Compute shaders that work on NVIDIA or older AMD cards fail silently, produce wrong results, or trigger TDR (Timeout Detection and Recovery) on RDNA 4. The app hangs for 2-3 seconds then the GPU resets, killing all state.

**Why it happens:**
Several AMD-specific issues:
1. **TDR timeout.** Windows kills GPU commands taking > 2 seconds. The current chunked dispatch (`_CHUNK_SIZE = 256K`) may not be granular enough for complex SPH with 27-cell neighbor search on 1M+ particles.
2. **wgpu-native on AMD.** The wgpu library has historically had more testing on NVIDIA/Vulkan. AMD Vulkan driver behavior can differ in edge cases (buffer alignment, workgroup limits, shared memory).
3. **No CUDA fallback.** CUDA-dependent libraries (cuSPH, NVIDIA Flex, etc.) are not available. Must use WebGPU/Vulkan compute or CPU fallback.
4. **RDNA 4 is new hardware.** Driver maturity for compute workloads on RX 9060 XT may lag behind gaming drivers. Compute-specific bugs are more likely in early driver revisions.

**How to avoid:**
1. **Profile dispatch timing.** Measure wall-clock time per compute submission. If approaching 500ms, reduce chunk size.
2. **Test on target hardware early and often.** Do not develop on NVIDIA and assume AMD will work.
3. **Implement GPU error recovery.** Catch device-lost events and reinitialize gracefully instead of crashing.
4. **Use wgpu limits queries.** Check `device.limits` for max workgroup sizes, max storage buffer size, etc. Do not hardcode NVIDIA-favorable values.
5. **Keep compute shaders simple.** Avoid complex control flow, deeply nested loops, and excessive register pressure. RDNA 4 wavefront size is 32 (vs 64 on older AMD). Verify workgroup size assumptions.

**Warning signs:**
- Application freezes for 2+ seconds then recovers (TDR)
- Compute results are NaN or zero on AMD but correct on other hardware
- GPU utilization is very low despite heavy workload (driver bottleneck)
- `wgpu` logs show device lost or validation errors

**Phase to address:**
Phase 1 (Physics Fix) — validate on AMD hardware immediately after rebuilding the physics pipeline. Do NOT wait until later phases.

---

### Pitfall 5: UI Rework Scope Creep — Rewriting Everything Instead of Restructuring

**What goes wrong:**
What starts as "clean up the layout and make it polished" becomes a full rewrite of every panel, widget, and signal connection. The UI rework takes 3x longer than estimated and introduces new bugs in features that already worked.

**Why it happens:**
The current `main_window.py` is 1700+ lines with deeply interleaved concerns: layout, wiring, business logic, worker management. Touching one thing breaks another. The temptation is to "do it right this time" and rewrite from scratch.

Looking at the current codebase: 21 files across `gui/`, `gui/panels/`, and `gui/widgets/`. Many have complex signal chains. A "clean slate" rewrite means re-implementing and re-testing all of these interactions.

Additionally, the user wants a white viewport background and polished controls — aesthetic changes that seem small but require touching theme.py, viewport.py, every panel's stylesheet, and potentially the rendering pipeline's clear color.

**How to avoid:**
1. **Restructure, don't rewrite.** Extract logic from `main_window.py` into a controller layer. Move layout to a separate module. Keep working widget code.
2. **Set a fixed scope.** Define exactly which panels change layout, which get visual polish, and which stay as-is. Write it down before starting.
3. **Theme changes first, layout second.** Changing colors/fonts/spacing is safe and gives visible progress. Layout changes are where breakage happens.
4. **Preserve all existing signal connections.** Map them before refactoring. Every `connect()` call must survive the rework.
5. **Test each panel independently** after the rework, not just "it launches."

**Warning signs:**
- "While I'm in here, I should also fix..." — scope is expanding
- Features that worked before the rework are now broken
- UI rework taking longer than the physics fix
- Creating new widget classes for things that already exist

**Phase to address:**
Phase 2 or 3 (UI Rework) — define scope boundaries before starting. Physics must be fixed first so you know the UI controls actually do something.

---

### Pitfall 6: LLM Latency in the Real-Time Render Loop

**What goes wrong:**
Claude API calls take 1-5 seconds. If parameter updates from Claude are awaited synchronously in the render loop, the viewport freezes. If they are fire-and-forget, parameters change abruptly between frames, causing visual popping.

**Why it happens:**
The current `EnrichmentService` makes synchronous API calls. The `EnrichmentWorker` runs in a background thread with Qt signals, which is correct — but the integration into the simulation parameter pipeline has a latency mismatch:

- Render loop runs at 60fps (16ms per frame)
- Claude API response: 1000-5000ms
- Network jitter: variable additional delay
- User sees 60-300 frames between when they request "Claude, drive this" and when parameters change

If parameters jump instantly when the response arrives, you get a visual discontinuity. If you try to interpolate, you need a parameter animation system that blends current values to target values over time.

**How to avoid:**
1. **Never block the render loop on API calls.** Always use background threads or async. The current `EnrichmentWorker` pattern is correct — keep it.
2. **Implement parameter lerping.** When Claude suggests new parameters, don't apply them instantly. Animate from current to target over 0.5-2 seconds using smooth interpolation.
3. **Queue parameter changes.** If multiple Claude responses arrive while one is still animating, queue them and apply sequentially.
4. **Show feedback during wait.** A subtle UI indicator that Claude is "thinking" prevents the user from wondering if the click did nothing.
5. **Cache Claude responses.** For similar photo sets, cache parameter suggestions to avoid redundant API calls.
6. **Design for graceful degradation.** If Claude is slow or unavailable, manual controls must work perfectly. Claude is additive, not required.

**Warning signs:**
- Viewport stutters when Claude panel is active
- Parameters "snap" between values instead of transitioning
- No visible feedback between clicking "Claude, drive" and seeing results
- App feels broken when offline (Claude features fail ungracefully)

**Phase to address:**
Phase 3 (Claude Integration) — build the parameter animation system during physics fix (Phase 1), then wire Claude into it.

---

### Pitfall 7: Depth Map Quality — Using Raw Model Output Without Post-Processing

**What goes wrong:**
Depth maps from Depth Anything V2 look washed out, low-contrast, and unsaturated. The resulting point clouds are flat-looking or have minimal depth variation. The user described this as "unsaturated/low quality."

**Why it happens:**
Neural depth estimation models output relative depth (not metric depth). The raw output is often:
- Normalized to [0, 1] but using only a narrow range (e.g., 0.3-0.7)
- Linear when perception is logarithmic — nearby objects get too much depth range, distant objects compress
- Missing fine detail at edges (the model trades boundary precision for smoothness)

The current code uploads depth maps as `r32float` textures without histogram equalization, contrast stretching, or any post-processing.

**How to avoid:**
1. **Apply histogram equalization** to spread depth values across the full [0, 1] range.
2. **Use CLAHE** (Contrast Limited Adaptive Histogram Equalization) for local contrast enhancement without over-amplifying noise.
3. **Apply edge-aware sharpening.** Use the edge map to preserve depth discontinuities at object boundaries while smoothing flat regions.
4. **Remap depth curve.** Apply a power curve or sigmoid to redistribute depth values for better perceptual spread.
5. **Optionally combine multiple depth models** or multi-scale inference for higher quality.

**Warning signs:**
- Point cloud looks like a flat disc instead of a 3D surface
- `np.histogram(depth_map)` shows values clustered in a narrow band
- Depth transitions between foreground/background are mushy, not crisp

**Phase to address:**
Phase 1 or 2 — depth quality improvement is independent of physics and can be done in parallel.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| CPU-side spatial hash (current) | Simpler code, no GPU prefix sum | Must transfer data GPU->CPU->GPU every frame, kills performance at 1M+ particles | Never for production — replace with GPU hash in Phase 1 |
| All params as "visual" (hot-reload) | No restart needed for any change | Some param changes need restart for stability (e.g., changing smoothing_radius invalidates density cache). No physics restart = accumulated numerical errors | Only during prototyping — classify params properly in Phase 1 |
| 1700-line main_window.py | Everything in one file, easy to find | Cannot test panels independently, every change risks breaking unrelated features, merge conflicts | Never — extract before adding v2.0 features |
| Hardcoded boundary (50 units) | Simple boundary containment | Does not scale with different point cloud sizes. A small portrait and a 1000-photo collection need different boundaries | Phase 1 — derive boundary from point cloud bounding box |
| Force clearing via CPU zero buffer | Simple, correct | Transfers N*16 bytes of zeros from CPU to GPU every frame. For 1M particles = 16MB/frame of bus traffic | Replace with a compute shader that writes zeros, or use buffer mapping |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude API | Sending full-resolution images in API calls (expensive, slow) | Resize to 512px max dimension before base64 encoding. Use `detail: low` in vision requests |
| Claude API | Parsing natural language responses as structured data | Use structured output / tool_use responses. Request JSON with a schema |
| ONNX Runtime (Depth Anything V2) | Loading model on every inference call | Load model once at startup, reuse session. Model loading is 2-5 seconds |
| wgpu device | Assuming device creation always succeeds | Handle adapter not found, device lost, and out-of-memory. Especially on AMD where Vulkan support varies by driver version |
| PySide6 + GPU rendering | Updating UI from worker threads directly | Always use signals/slots or `QMetaObject.invokeMethod` to cross thread boundaries. Direct widget access from worker threads causes crashes |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| CPU spatial hash rebuild | FPS drops linearly with particle count | GPU-side prefix sum spatial hash | > 100K particles |
| Per-frame CPU buffer clear (zeros upload) | Bus bandwidth saturated, GPU stalls waiting for transfer | GPU compute shader to clear buffers | > 500K particles |
| 128^3 spatial hash grid (2M cells, 8MB) | Memory waste for sparse particle distributions | Compact hash table (hash map) instead of dense grid | Always wasteful, but functional until memory pressure matters |
| SPH 27-cell neighbor search | O(N * k) where k = neighbors. With high density k can be 200+ per particle | Cap neighbor count per particle (e.g., max 64). Use spatial hierarchy | > 200K particles in a small volume |
| GPU readback for position data | Stalls GPU pipeline, adds 1+ frame of latency | Use GPU-GPU buffer copies, avoid readback except for export | Any real-time use (already avoided in render path, but `read_positions()` exists for export) |
| Rebuilding all bind groups every frame | CPU overhead for bind group creation | Only rebuild when buffer swap occurs (every step, but skip if paused) | > 3 compute passes per frame (currently 4) |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Physics params require knowledge of SPH to tune | User has no idea what "gas constant" or "rest density" mean | Provide artist-friendly presets ("flowing water", "thick honey", "smoke") with underlying physics params hidden. Expose "viscosity" and "turbulence" as intuitive sliders |
| Parameter change restarts sim, losing interesting state | User found a beautiful configuration, tweaked one thing, everything resets | Hot-reload all possible params. For params that truly need restart, warn first and offer "snapshot current state" |
| No undo for parameter changes | User cannot experiment safely | Parameter history with undo/redo (QUndoStack exists but needs wiring to sim params) |
| White viewport background with no gradient or environment | Particles look flat and disconnected from space | Subtle gradient background, optional ground plane shadow, ambient occlusion in post-fx |
| Simulation controls buried in separate panel | User must switch panels to start/stop/restart sim | Persistent sim controls (play/pause/restart) in toolbar or viewport overlay |
| No visual feedback for force fields | User adjusts "wind" but cannot see where wind flows | Optional debug visualization: draw flow field as streamlines, show attractor positions as glowing spheres |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **SPH simulation:** Looks like it runs (particles move) but forces are wrong — verify kernel coefficients produce reasonable density values (should be near rest_density, not 1e6+)
- [ ] **Spatial hash:** Code exists and compiles but only runs at init — verify hash is rebuilt every frame
- [ ] **Depth maps:** Texture uploads successfully but values are compressed — verify histogram spans [0, 1] with reasonable distribution
- [ ] **Claude integration:** API calls succeed and return text — verify response is parsed into actual parameter values and applied with interpolation
- [ ] **UI rework:** Layout looks clean in screenshot — verify all signal connections still work (load photo -> extract -> build point cloud -> simulate flow still functions end-to-end)
- [ ] **AMD compatibility:** App launches and renders on AMD — verify compute shaders produce correct results (compare output against known-good reference)
- [ ] **Force clamping:** Forces are capped — verify the cap is applied BEFORE integration, not after (clamping velocity after the fact does not prevent position jumps)
- [ ] **Damping:** Velocity damps each frame — verify damping works correctly with symplectic Euler (damping should be applied to velocity, not acceleration)
- [ ] **Double buffering:** Buffers swap correctly — verify bind groups are rebuilt after swap (stale bind group = reading/writing wrong buffer = corruption)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Particles explode | LOW | Add force clamping (single shader change). Set MAX_FORCE = 10 * gravity magnitude. Add velocity clamping. Takes 1-2 hours |
| Stale spatial hash | MEDIUM | Implement GPU prefix-sum hash. Requires new compute shaders (hash, count, scan, scatter). Takes 2-3 days |
| UI rework broke features | MEDIUM | Git revert to last working commit, apply visual changes incrementally with testing between each change |
| AMD TDR crashes | LOW-MEDIUM | Reduce chunk size. Add timing instrumentation. If persistent, switch to CPU fallback for that compute pass |
| LLM latency freezes viewport | LOW | Verify all Claude calls are on background thread. Add a 5-second timeout. Queue responses |
| Depth maps low quality | LOW | Add numpy post-processing (histogram equalization). 20 lines of code, immediate improvement |
| SPH params produce NaN | MEDIUM | Add NaN guards in shader (`if isnan(force) { force = vec3(0.0); }`). Investigate which kernel/param combination causes the NaN. Usually division by zero in density |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SPH kernel explosion | Phase 1 (Physics Fix) | Log max density per frame. Should be within 2x of rest_density for a stable sim |
| Stale spatial hash | Phase 1 (Physics Fix) | After 100 frames, spatial hash cell assignments should match actual particle positions (sample 100 random particles, verify cell) |
| Force accumulation overflow | Phase 1 (Physics Fix) | Log max force magnitude. Should never exceed MAX_FORCE constant |
| AMD TDR timeout | Phase 1 (Physics Fix) | Run 1M particle sim for 5 minutes on RX 9060 XT without device lost event |
| UI scope creep | Phase 2 (UI Rework) | Written scope document listing exactly which files change. Review at midpoint: if scope has grown > 20%, stop and reassess |
| LLM latency in render loop | Phase 3 (Claude Integration) | Measure frame time with Claude panel active vs inactive. Difference should be < 1ms |
| Depth map quality | Phase 1 or 2 (parallel) | Histogram of output depth values should use > 80% of [0, 1] range |
| Parameter animation | Phase 1 (Physics Fix) | Parameter changes animate smoothly over 0.5s. No visual popping when changing any slider |
| NaN propagation | Phase 1 (Physics Fix) | Run sim for 1000 frames, readback positions, assert no NaN/Inf values |

## Sources

- Direct analysis of `apollo7/simulation/shaders/sph.wgsl` — kernel coefficient math
- Direct analysis of `apollo7/simulation/shaders/forces.wgsl` — unbounded attraction force
- Direct analysis of `apollo7/simulation/shaders/integrate.wgsl` — force accumulation without clamping
- Direct analysis of `apollo7/simulation/buffers.py` lines 146-148 — spatial hash only built at init
- Direct analysis of `apollo7/simulation/parameters.py` — default parameter values
- Direct analysis of `apollo7/gui/main_window.py` — 1700+ line monolith with interleaved concerns
- SPH kernel mathematics: Muller et al., "Particle-Based Fluid Simulation for Interactive Applications" (2003) — standard kernel formulas
- AMD TDR behavior: Windows WDDM timeout detection documentation
- General particle simulation stability: Bridson, "Fluid Simulation for Computer Graphics" — CFL condition, force clamping

---
*Pitfalls research for: Apollo 7 v2.0 — fluid particle simulation, UI rework, LLM integration, AMD GPU compute*
*Researched: 2026-03-15*
