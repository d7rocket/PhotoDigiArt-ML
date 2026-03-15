# Phase 4: Stable Physics - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current SPH-based simulation with a PBF (Position Based Fluids) solver that keeps particles in coherent, organic, living shapes indefinitely. Add home position attraction, GPU spatial hash rebuild, force/velocity clamping, CFL-adaptive timestep, curl noise flow fields, vortex confinement, breathing modulation, and solver iterations as a creative control. Rendering quality and UI polish are separate phases (5 and 6).

</domain>

<decisions>
## Implementation Decisions

### Home Position Feel
- Elastic tether model: particles always feel a spring-like pull back to their photo-derived home positions
- Home strength is feature-modulated: global slider sets baseline, but particles on edges/high-detail areas hold tighter while particles in flat/sky regions drift more freely (using existing edge_map and depth_map feature textures)
- At rest, particles exhibit visible flow -- slow currents around home positions, clearly alive like embers in a gentle breeze, shape always recognizable but never static
- At maximum home_strength, particles still exhibit micro-motion from noise/breathing -- never fully static, always alive, just very tightly held

### Organic Motion Character
- Primary aesthetic: ocean currents -- slow, sweeping flows with long graceful arcs (Refik Anadol "Machine Hallucinations" reference)
- Curl noise at low frequency, high amplitude for the base flow
- Vortex confinement as subtle accent: small eddies within larger currents, noticeable on close inspection but not dominating
- Breathing modulation: slow inhale/exhale ~4-6 second cycle, sine wave on home_strength and noise_amplitude, calm and meditative
- Motion is photo-influenced: busy/complex photos get slightly more turbulent flow, simple photos get calmer motion (edge density and color variance modulate noise parameters)

### Default Solver Feel
- Default solver iterations: 2 (balanced fluid -- visible structure, not rigid, enough to see ocean-current motion while reading photo shape)
- Iteration range: 1-6 (1=wispy gas, 2=default fluid, 4=dense liquid, 6=near-solid)
- Iteration changes crossfade smoothly over ~0.5s -- particles gradually tighten or loosen
- Slider labeled with creative terminology (e.g., "Cohesion" with "Ethereal" to "Liquid" spectrum), not "Solver Iterations"

### Stability vs Dynamism
- Home attraction is the dominant force at defaults -- form is always stable, curl noise and vortices add motion within the shape
- Silent clamping: force and velocity clamping happens invisibly, no error messages, no slider restrictions, sim just caps at maximum intensity
- CFL-adaptive timestep is purely internal -- user never sees dt values, just experiences consistent smooth motion
- Zero CPU readback in simulation loop -- entire sim stays on GPU (hash build, PBF solve, forces, integration) for 500K+ particles at 60fps

### Claude's Discretion
- PBF solver implementation details (relaxation parameter, constraint formulation)
- Exact clamping thresholds for force/velocity bounds
- CFL coefficient tuning
- GPU spatial hash implementation strategy (counting sort vs bitonic sort)
- Curl noise epsilon and sampling strategy refinements
- Breathing waveform shape (pure sine vs asymmetric)
- Feature modulation mapping functions (linear, sigmoid, etc.)

</decisions>

<specifics>
## Specific Ideas

- Ocean currents aesthetic inspired by Refik Anadol's "Machine Hallucinations" -- slow, sweeping, graceful
- "Alive formula" from v2.0 research: home attraction + curl noise + vortex confinement + velocity-dependent damping
- Elastic tether metaphor: like a jellyfish in current -- stretches with force, snaps back when calm
- Photo features (edge_map, depth_map) should drive both shape tightness AND motion intensity -- the data shapes the behavior, not just the form
- Creative slider labeling: "Cohesion" not "Solver Iterations", "Ethereal" to "Liquid" spectrum

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SimulationEngine` (engine.py): Orchestrates compute pipelines, already has chunked dispatch for AMD TDR prevention -- will be heavily modified but structure is sound
- `ParticleBuffer` (buffers.py): Double-buffered GPU storage with forces/densities/spatial hash buffers already allocated -- needs home_position buffer added
- `SimulationParams` (parameters.py): WGSL-aligned uniform packing with hot-reload support -- needs new params (home_strength, breathing_rate, solver_iterations, etc.)
- `integrate.wgsl`: Perlin noise + FBM + approximate curl noise already implemented -- can be refined for proper curl noise
- `forces.wgsl`: Spatial hash neighbor search working -- pattern reusable for PBF constraint evaluation
- `sph.wgsl`: SPH kernels (poly6, spiky, viscosity) -- will be replaced by PBF but kernel math is reference material
- Feature textures (edge_map, depth_map) already uploaded to GPU in engine.py -- available for feature-modulated home strength

### Established Patterns
- Multi-pass compute pipeline: separate command encoder submissions per pass for synchronization
- Spatial hash: 128^3 grid with cell_counts/cell_offsets/sorted_indices buffers
- Uniform buffer packing: vec4-aligned, 16-byte boundaries
- Chunked dispatch: 256K particles per dispatch, workgroup size 256
- Buffer ping-pong: swap() for double-buffering without GPU copy

### Integration Points
- `SimulationEngine.step()` -- main entry point, currently runs forces -> SPH -> integrate -> swap
- `ParticleBuffer.build_spatial_hash()` -- currently CPU-only, needs GPU compute replacement
- `SimulationParams.to_uniform_bytes()` -- needs new fields for PBF/home/breathing params
- `viewport.py` reads `get_positions_buffer()` and `get_colors_buffer()` for rendering -- zero-copy interface must be preserved
- GUI parameter panels bind to `update_visual_param()` / `update_physics_param()` -- new params need registration

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 04-stable-physics*
*Context gathered: 2026-03-15*
