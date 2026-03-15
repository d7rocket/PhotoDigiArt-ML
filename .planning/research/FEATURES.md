# Feature Landscape

**Domain:** Data-driven generative art -- photo-to-sculpture pipeline with living particle physics
**Researched:** 2026-03-15
**Focus:** v2.0 "Make It Alive" upgrade -- organic fluid motion, polished UI, Claude creative direction

## Table Stakes

Features required for a generative art tool that claims to produce "living" data sculptures. Missing any of these means the output still looks like exploding pixels rather than coherent organic forms.

| Feature | Why Expected | Complexity | Existing? | Notes |
|---------|-------------|------------|-----------|-------|
| **Per-particle home position attraction** | THE critical missing piece. Every professional particle sculpture system (Houdini POP Attract, TouchDesigner attractor TOPs) anchors particles to target positions while allowing perturbation. Without home attraction, forces inevitably disperse particles into chaos. This is the #1 difference between Anadol-style sculptures and random explosions. | Medium | Partial -- attractors exist from collection analysis but NOT per-particle homes | Add `home_positions` storage buffer (copy of initial positions). Add `home_strength` param (0.0-2.0). Force: `(home_pos - pos) * home_strength`. Every particle gently pulled back toward its data-derived location. |
| **Curl noise flow field (tuned)** | The signature of organic motion. Current integrate.wgsl implements curl via finite differences on fbm3d -- the approach is mathematically correct. Problem is force balance: competing SPH/attraction/repulsion forces likely overwhelm the flow field, or parameter ranges are wrong. | Low (tuning) | Yes -- integrate.wgsl lines 177-197 | The curl implementation looks correct. Fix is parameter tuning + ensuring curl noise amplitude is proportional to other forces. Current `noise_amplitude` default of 1.0 may need to be 0.1-0.3 when other forces are active. |
| **Velocity-dependent damping** | Uniform damping (current: 0.99) treats slow and fast particles identically. Fast-moving particles should experience more drag, preventing runaways while allowing slow orbital motion. This creates the "viscous fluid" feel. | Low | Partial -- uniform damping exists | Change from `vel *= damping` to `vel *= damping - drag_coefficient * length(vel)`. Or use `vel *= damping / (1.0 + drag * length(vel))` to prevent negative damping. |
| **Force balance presets** | 18+ parameters with no guidance on good combinations is unusable for most artists. Curated presets that demonstrate what "alive" looks like are table stakes for any parametric creative tool. Current presets are described as "whacky." | Low | Preset system exists but quality is poor | Create 6-8 curated presets: "Gentle Flow" (low noise, moderate home), "Ocean Current" (high curl, low home), "Breathing" (modulated amplitude), "Vortex" (high turbulence, strong curl), "Crystalline" (high home, low noise), "Dissolution" (zero home, high curl). |
| **Smooth parameter interpolation** | Jumping between parameter values causes jarring visual discontinuities that break the "living" illusion. Every parameter change must lerp over 0.3-1.0 seconds. TouchDesigner does this automatically; Houdini has ramped keyframes. | Low | Crossfade widget exists for preset transitions | Wire crossfade/lerp to ALL parameter changes, not just preset transitions. On slider release, animate from old to new value over ~0.5 seconds. |
| **Round soft-edged points** | Hard square points (GPU default) look like a debug visualization, not art. Round points with gaussian falloff are the baseline for any point cloud art tool. Additive blending creates glow at density concentrations. | Medium | Unknown -- needs render pipeline check | Fragment shader: `let d = length(point_coord - 0.5); if d > 0.5 { discard; } alpha *= smoothstep(0.5, 0.3, d);`. Enable additive blending for luminous effect. |
| **Background color control** | Anadol uses pure black for dramatic contrast. Gallery displays use white. Artists need at minimum black/white/custom toggle. The viewport background IS part of the artwork. | Low | Theme system exists, viewport bg unclear | Color picker or at minimum black/white/dark-gray toggle for viewport background. |
| **Consistent 60fps at 500K+ particles** | Any stutter destroys the "living" illusion. The human eye is extremely sensitive to motion discontinuity. Performance mode (SPH bypass) already exists, which is good. | Medium | Performance mode exists, TDR chunking exists | Profile at 500K particles with all forces active. If sub-60fps, tune SPH neighbor search radius and workgroup dispatch. The spatial hash grid (128^3) may be oversized. |

## Differentiators

Features that elevate Apollo 7 from "competent particle tool" to "artistic instrument that produces gallery-quality living sculptures."

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| **Multi-octave time evolution** | Current fbm3d uses static octave frequencies. In reality, large-scale motion should evolve slowly while small-scale detail flickers rapidly. Adding per-octave time multipliers creates "breathing" -- the unmistakable signature of living systems vs mechanical repetition. | Medium | Existing curl noise | Modify fbm3d: `pos = p * frequency + vec3(time * 0.05 * pow(2.0, float(i)))`. Large octaves evolve slowly, small octaves evolve fast. This single change transforms static swirls into organic undulation. |
| **Vortex confinement force** | Amplifies existing rotational motion, preventing it from dissipating due to numerical damping. Used in every professional fluid sim (Houdini, Fedkiw et al.). Adds persistent swirling without adding net energy. The "wow" factor in fluid-like particle motion. | Medium | Existing force pipeline + neighbor velocity access | Compute vorticity `omega = curl(velocity_field)` at each particle (sample neighbor velocities). Apply force: `f_conf = epsilon * (normalize(gradient(|omega|)) cross omega) * h`. Requires accessing neighbor velocities in the forces pass. |
| **Breathing / pulse modulation** | Periodic sine-wave modulation of noise_amplitude and home_strength. Creates the "organism" effect: sculpture expands on "inhale" (weaker home, stronger noise), contracts on "exhale" (stronger home, weaker noise). Trivial to implement, massive visual impact. | Low | Home position attraction | Add `breathing_rate` (0.1-2.0 Hz) and `breathing_depth` (0.0-1.0) params. In shader: `let breath = sin(time * rate * 6.28) * depth; effective_home_strength = home_strength * (1.0 - breath * 0.5); effective_noise_amp = noise_amplitude * (1.0 + breath * 0.3);` |
| **Shape morphing between targets** | Smoothly morph particle cloud between different source configurations: depth-projected portrait, feature-clustered abstract, embedding cloud, or between different photos. Lerp home positions over configurable duration. Signature Anadol "data morphism" effect. | High | Per-particle home positions + multiple target position sets | Store N target position buffers. Animate: `current_home = lerp(target_A, target_B, smooth_t)` where `smooth_t` uses ease-in-out curve. Need UI for selecting morph targets and duration. |
| **Claude creative director** | Claude analyzes source photos (via thumbnails + CLIP descriptions), understands content/mood, and suggests complete parameter sets with artistic rationale. "This portrait has dramatic chiaroscuro lighting -- suggesting strong vertical flow with high contrast between dense and sparse regions to echo the shadow geometry." | High | Existing Claude API + home position system | Send: photo thumbnail (resized), CLIP embedding summary, current parameter values. Receive: JSON parameter set + natural language explanation. Display rationale alongside "Apply Direction" button. The explanation is as valuable as the parameters -- it teaches the artist. |
| **Particle trails (temporal accumulation)** | Short motion trails behind each particle showing recent trajectory. Creates the "data stream" aesthetic central to Anadol's work. Two approaches: per-particle history ring buffer (expensive memory) or frame accumulation buffer (cheap, slightly different look). | Medium | Trail length param exists in PostFX panel | Frame accumulation: render current frame, blend with previous frame at 80-95% opacity. Effectively free performance-wise. Per-particle trails: store last 4-8 positions per particle, render as line strips. More control but 4-8x position buffer memory. |
| **Depth-aware point sizing** | Points closer to camera render larger, creating natural perspective depth cue. Combined with DOF blur (exists in PostFX), produces cinematic spatial depth without expensive raytracing. | Low | DOF exists in PostFX system | Vertex shader: `point_size = base_size / (distance_to_camera * perspective_scale + 1.0)`. Already standard in point cloud renderers. |
| **Color field evolution** | Particle colors shift slowly over time based on their position within the flow field. Sample noise at particle position, use as hue/saturation offset. Colors "flow through" the sculpture creating iridescent, oil-on-water shimmer. | Medium | Color buffer + noise functions | Sample `perlin3d(pos * color_freq + time * color_speed)` and map to hue rotation. Very striking visually, relatively cheap computationally since noise is already sampled for flow field. |
| **Tiered parameter UI** | Split parameters into Essential (5-7 sliders visible by default) and Advanced (collapsed). Essential: speed, home_strength, flow_intensity, breathing_rate, point_size. Advanced: all SPH params, noise octaves, vortex, individual force weights. Inspired by UJI's minimal slider approach and TouchDesigner's parameter panel hierarchy. | Medium | Existing simulation panel | Reduces visual overwhelm from 22+ sliders to ~6 primary controls. Advanced section available for power users. Claude creative director navigates the full parameter space, so most users never need advanced controls. |
| **Claude-generated preset names** | When user saves a preset, optionally ask Claude to generate a poetic name and one-sentence description based on parameter values and source material. Makes preset library feel curated rather than "Preset_23." | Low | Preset system + Claude API | Low-stakes API call. Falls back gracefully to user naming if Claude unavailable. Delightful touch that costs almost nothing to implement. |

## Anti-Features

Features to explicitly NOT build. These are common traps that waste months of development or dilute the product identity.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full Navier-Stokes fluid solver** | Requires pressure projection, divergence-free velocity solve, implicit time stepping. Months of work for a marginal visual improvement over tuned curl noise + SPH + vortex confinement. These three together produce 90% of the "fluid" look at 10% of the computational cost. The goal is aesthetic fluid motion, not physically accurate fluid dynamics. | Tune existing SPH + add curl noise balance + add vortex confinement. Professional generative artists (including Anadol's studio) use curl noise, not Navier-Stokes, for real-time work. |
| **Mesh reconstruction from particles** | Marching cubes / Poisson reconstruction changes the aesthetic from "flowing point cloud" to "3D model." Entirely different visual language. Also adds enormous computational cost and geometric artifacts. Not the Anadol look. | Keep particles as points. Invest in point rendering quality (round, soft, glowing, trails). The point cloud IS the medium. |
| **Node-based visual programming** | TouchDesigner already does this brilliantly. Building a node editor is 6+ months of UI work that recreates what exists. Apollo 7's identity is "drop photos in, get sculpture out" -- not "wire nodes to build a pipeline." The node_editor.py file exists but should remain a simple mapping tool, not a full programming environment. | Keep slider-based parametric UI. Claude creative director serves as the "intelligent node graph" -- it understands artistic intent and maps to parameters without the user needing to understand signal flow. |
| **Audio reactivity** | Requires audio capture, FFT analysis, beat detection, onset detection, frequency band isolation, and parameter mapping. An entire separate feature domain that would take 3-4 weeks minimum. | The breathing/pulse modulation system provides similar rhythmic motion without audio complexity. Defer to v3.0 if ever requested. |
| **Real-time video export** | Screen recording at 60fps while maintaining simulation performance is hard. Video encoding adds significant GPU load. H.264/H.265 encoding on AMD requires AMF SDK integration. | Keep PNG sequence export. Add a "Render Sequence" mode that pauses real-time display and renders N frames at full quality. Users assemble with ffmpeg. Much simpler, better quality. |
| **Physics-accurate collision** | Particle-mesh or particle-particle hard collision detection is expensive and unnecessary. Sculptures don't interact with solid geometry. The "soft" behavior of overlapping particles IS the aesthetic. | Use soft boundary clamping (exists) and home position attraction for confinement. SPH pressure forces provide soft collision-like behavior. |
| **Multi-user collaboration** | Networking, state sync, conflict resolution, presence indicators. Massive scope for near-zero value in a single-artist creative tool. | Single-user tool. Share work via preset files and project exports. |

## Feature Dependencies

```
                    Per-Particle Home Positions
                    /           |            \
                   v            v             v
        Force Balance     Breathing/Pulse   Shape Morphing
         Presets           Animation        Between Targets
            |                  |
            v                  v
     Claude Creative      Smooth Parameter
      Director             Interpolation
            |
            v
     Claude Preset Names


     Curl Noise (existing, needs tuning)
            |
            v
     Multi-Octave Time Evolution
            |
            v
     Vortex Confinement (independent but synergistic)


     Point Rendering Quality (round, soft)
            |
            +--> Depth-Aware Point Sizing
            |
            +--> Particle Trails
            |
            +--> Color Field Evolution


     Tiered Parameter UI (depends on knowing which params are "essential"
                          -- informed by force balance preset work)
```

## MVP Recommendation for v2.0

The minimum set of features to transform "exploding pixels" into "living sculpture."

### Phase 1: Make It Coherent (fix the physics)

Priority: These MUST ship. Without them, nothing else matters.

1. **Per-particle home position attraction** -- Add `home_positions` storage buffer copied from initial positions. Add `home_strength` uniform parameter (default 0.3). Compute `force += (home_pos - pos) * home_strength` in forces shader. This single feature prevents particle dispersion and creates coherent forms.
2. **Velocity-dependent damping** -- Replace `vel *= 0.99` with `vel *= damping / (1.0 + drag * length(vel))`. Prevents fast-moving particles from escaping while allowing slow orbital motion. Natural viscous-fluid feel.
3. **Force balance presets** -- Create 6-8 curated parameter sets using the new home_strength param. These are the proof that the physics work. Each preset should look distinctly "alive" in different ways.
4. **Breathing modulation** -- Add `breathing_rate` and `breathing_depth` params. Modulate home_strength and noise_amplitude with sine wave. Instant "alive" feel at near-zero implementation cost.

### Phase 2: Make It Beautiful (rendering + motion quality)

5. **Round soft-edged points with additive blending** -- Transform the rendering from debug-quality to art-quality.
6. **Smooth parameter interpolation** -- All parameter changes lerp over time. No more jarring jumps.
7. **Multi-octave time evolution** -- Per-octave time scaling in noise. Organic evolution instead of mechanical repetition.
8. **Vortex confinement** -- Persistent swirling that resists numerical damping.
9. **Tiered parameter UI** -- Essential (6 sliders) + Advanced (collapsed). Reduce visual overwhelm.

### Phase 3: Make It Intelligent (Claude-driven)

10. **Claude creative director** -- Photo analysis to parameter suggestion with artistic rationale.
11. **Claude preset naming** -- Poetic names for saved presets.
12. **Depth-aware point sizing** -- Cinematic depth from camera perspective.

### Defer to v2.5+

- Shape morphing between targets (needs stable home positions first)
- Color field evolution (nice-to-have, not essential for "alive")
- Particle trails (rendering complexity vs. impact unclear -- prototype first)

## The "Alive" Formula

Based on research into Refik Anadol's studio work, TouchDesigner particle systems, Houdini POP networks, and Bridson et al.'s curl-noise paper, the recipe for organic particle motion is **four competing forces in dynamic equilibrium**:

1. **Cohesion force** (home position attraction): Pulls particles toward their intended form. Strength: moderate. Purpose: shape preservation.
2. **Flow force** (curl noise): Pushes particles along smooth, divergence-free paths. Strength: proportional to cohesion. Purpose: organic motion.
3. **Confinement force** (vortex confinement): Amplifies existing rotation, preventing dissipation from numerical damping. Strength: subtle. Purpose: persistent swirls.
4. **Drag force** (velocity-dependent damping): Prevents explosion by penalizing high velocity. Strength: proportional to speed. Purpose: stability.

When these four balance, particles orbit their home positions in flowing, undulating paths. They look "alive" because they exist in a stable dynamic system -- not decaying, not exploding, but continuously moving in equilibrium.

The current codebase has force 2 (curl noise, implemented correctly) and force 4 (uniform damping, needs velocity-dependence). Forces 1 (per-particle homes) and 3 (vortex confinement) are missing. Adding them and tuning the balance is the core v2.0 work.

### New Shader Parameters

```wgsl
// Add to SimParams uniform (4 new floats = 1 new vec4):
home_strength: f32,      // 0.0-2.0, soft attraction to initial position
breathing_rate: f32,     // 0.1-2.0 Hz, pulse frequency
breathing_depth: f32,    // 0.0-1.0, modulation amplitude
vortex_strength: f32,    // 0.0-1.0, vortex confinement intensity

// New storage buffer:
@group(0) @binding(N) var<storage, read> home_positions: array<vec4<f32>>;
```

This adds one vec4 to the uniform (112 -> 128 bytes, still vec4-aligned) and one new storage buffer (same size as positions buffer, set once at init).

## Sources

- [Bridson et al. - Curl-Noise for Procedural Fluid Flow (2007)](https://www.researchgate.net/publication/216813629_Curl-noise_for_procedural_fluid_flow) -- HIGH confidence, foundational paper for divergence-free procedural flow
- [SideFX POP Attract Documentation](https://www.sidefx.com/docs/houdini/nodes/dop/popattract.html) -- HIGH confidence, reference implementation of shape target attraction
- [SideFX Curl Noise Flow Tutorial](https://www.sidefx.com/tutorials/curl-noise-flow/) -- MEDIUM confidence, professional technique walkthrough
- [Emil Dziewanowski - Curl Noise](https://emildziewanowski.com/curl-noise/) -- MEDIUM confidence, practical implementation guide
- [Refik Anadol - Works](https://refikanadol.com/works/) -- HIGH confidence, primary aesthetic reference
- [NVIDIA AI Art Gallery - Refik Anadol](https://www.nvidia.com/en-us/research/ai-art-gallery/artists/refik-anadol/) -- HIGH confidence, technical description of Anadol's GPU workflow
- [WeTransfer - Anadol Data Sculptures](https://wepresent.wetransfer.com/stories/refik-anadol-on-quantum-memories-and-data-sculptures) -- MEDIUM confidence, process description
- [Wicked Engine - GPU Fluid Simulation](https://wickedengine.net/2018/05/scalabe-gpu-fluid-simulation/) -- MEDIUM confidence, GPU SPH implementation reference
- [Point Cloud Morphing in UE4](https://www.gamedeveloper.com/game-platforms/point-clouds-morphing-fx-with-unreal-engine-4-) -- MEDIUM confidence, morph target implementation
- [AllTouchDesigner - Particle Attractors](https://alltd.org/touchdesigner-particles-system-on-tops-part-1-sources-attractor-and-forces/) -- MEDIUM confidence, attractor system patterns
- [UJI Generative Art Tool](https://excessivelyadequate.com/posts/uji.html) -- MEDIUM confidence, minimal generative art UI reference
- [Charlotte Dann - Magical Vector Fields](https://charlottedann.com/article/magical-vector-fields) -- MEDIUM confidence, flow field techniques
- [Three.js Galaxy Simulation with WebGPU Compute](https://threejsroadmap.com/blog/galaxy-simulation-webgpu-compute-shaders) -- MEDIUM confidence, WebGPU compute patterns
- [GPU Particle Attractors - Experiments with Google](https://experiments.withgoogle.com/gpu-particle-attractors) -- MEDIUM confidence, attractor-based particle aesthetics
