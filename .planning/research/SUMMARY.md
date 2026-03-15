# Project Research Summary

**Project:** Apollo 7 v2.0 -- "Make It Alive"
**Domain:** Real-time generative art -- photo-to-sculpture pipeline with living particle physics
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

Apollo 7 v2.0 transforms a working photo-to-point-cloud pipeline into a living data sculpture engine. The v1.0 foundation (Python 3.12, PySide6, pygfx/wgpu, ONNX+DirectML) is sound and should be kept entirely -- the problems are in physics implementation, not technology choices. The single most critical finding across all research is that **particles explode because of structural simulation bugs** (stale spatial hash, double-counted gravity, unbounded kernel coefficients, no force clamping), not because of wrong parameter values. All four research files converge on this: fix the physics first, everything else is downstream.

The recommended approach is threefold. First, replace the current SPH force-based solver with Position Based Fluids (PBF), which is unconditionally stable and purpose-built for real-time GPU particle art. Add per-particle home position attraction to create coherent forms. Second, add Claude as a creative director using structured outputs with Pydantic schemas to generate validated simulation parameters from photo analysis. Third, polish the UI with qt-material theming and a tiered parameter interface. The stack additions are minimal: only `anthropic`, `pydantic`, and `qt-material` as new dependencies. All fluid physics work uses existing WGSL compute shaders on the same wgpu device -- no second GPU compute framework.

The key risks are AMD RDNA 4 driver maturity for compute workloads (mitigate by testing on target hardware immediately after physics rebuild), UI rework scope creep (mitigate by defining fixed scope before starting), and LLM latency disrupting the real-time feel (mitigate by always running Claude calls asynchronously with parameter crossfade on apply). The "alive" formula distilled from Anadol studio research, Houdini workflows, and Bridson's curl-noise paper is four forces in dynamic equilibrium: home attraction (cohesion), curl noise (flow), vortex confinement (persistent swirls), and velocity-dependent damping (stability).

## Key Findings

### Recommended Stack

The entire v1.0 stack is kept. Only three new packages are needed for v2.0: `anthropic` (Claude API), `pydantic` (parameter schemas), and `qt-material` (UI theming). The most important stack decision is **not adding a second GPU compute framework**. Taichi Lang, NVIDIA Warp, PySPH, and pySPlisHSPlasH were all evaluated and rejected -- Taichi has no GPU buffer interop with wgpu/pygfx (forcing CPU roundtrips), Warp is CUDA-only (dead on AMD), and PySPH is scientific-focused with no real-time rendering integration. The right approach is expanding existing WGSL compute shaders that share GPU buffers with the pygfx renderer at zero copy cost.

**Core technologies (kept):**
- **pygfx 0.16.0 + wgpu-py 0.31.0:** Unified GPU compute + rendering on AMD via Vulkan/DX12
- **PySide6 6.8+:** Desktop GUI, proven pygfx integration via rendercanvas
- **ONNX + DirectML:** Lightweight GPU inference for Depth Anything V2

**New additions:**
- **anthropic 0.84.0:** Claude API with structured outputs and tool use for creative direction
- **pydantic 2.x:** Parameter schema validation, guarantees Claude returns valid simulation params
- **qt-material 2.17:** Material Design theming for instant professional polish

### Expected Features

**Must have (table stakes -- without these, particles still look like exploding pixels):**
- Per-particle home position attraction (THE critical missing piece for coherent forms)
- Velocity-dependent damping (prevents runaway particles, creates viscous-fluid feel)
- Force balance presets (6-8 curated sets proving the physics work)
- Breathing/pulse modulation (sine-wave modulation of home_strength and noise_amplitude)
- Round soft-edged points with additive blending (art quality, not debug quality)
- Smooth parameter interpolation (all changes lerp over 0.3-1.0 seconds)
- Consistent 60fps at 500K+ particles

**Should have (differentiators -- elevate from "tool" to "artistic instrument"):**
- Multi-octave time evolution (large-scale slow motion, small-scale fast flicker)
- Vortex confinement force (persistent swirling without added energy)
- Claude creative director (photo analysis to parameter suggestion with artistic rationale)
- Tiered parameter UI (6 essential sliders visible, advanced collapsed)
- Depth-aware point sizing (cinematic perspective)
- Color field evolution (iridescent shimmer as colors flow through the sculpture)

**Defer to v2.5+:**
- Shape morphing between targets (needs stable home positions proven first)
- Particle trails (rendering complexity vs. impact unclear -- prototype first)
- Audio reactivity (entire separate domain, defer to v3.0)

**Anti-features (explicitly do NOT build):**
- Full Navier-Stokes solver, mesh reconstruction, node-based editor, real-time video export

### Architecture Approach

Replace SPH with Position Based Fluids (PBF) as the simulation backbone. PBF is unconditionally stable because it solves positional constraints directly rather than accumulating forces that can explode. The compute pipeline becomes 5 GPU dispatches per frame: predict positions, build spatial hash (GPU, every frame), compute density constraints, apply position corrections, finalize velocities with vorticity confinement and XSPH viscosity. Eliminate the CPU readback bottleneck by sharing GPU buffers directly between compute and render. Add a Claude Parameter Pipeline as a new top-level module using structured outputs with Pydantic schemas.

**Major components (new/modified):**
1. **PBFSolver** (NEW) -- Orchestrate 5 compute passes per frame, unconditionally stable fluid solver
2. **ClaudeDirector** (NEW) -- Generate creative parameters via Claude structured outputs, always async
3. **ParameterSchema** (NEW) -- Pydantic models with bounded ranges for guaranteed valid Claude output
4. **ClaudePanel** (NEW) -- UI for creative direction interaction with apply/crossfade controls
5. **SimulationEngine** (MODIFIED) -- Delegate to PBFSolver, remove broken SPH/forces pipeline
6. **ViewportWidget** (MODIFIED) -- Eliminate CPU readback, share GPU buffers with pygfx

### Critical Pitfalls

1. **SPH kernel coefficients blow up at small smoothing radii** -- poly6 denominator `h^9 = 1e-9` produces astronomical kernel values. Solution: replace SPH with PBF which is unconditionally stable, or normalize kernels to spatial scale and clamp forces.

2. **Stale spatial hash causes ghost forces** -- `build_spatial_hash()` runs only at init, not per-frame. After frame 1, neighbor lookups are wrong and forces become erratic. Solution: GPU-side prefix-sum spatial hash rebuilt every frame.

3. **Force accumulation without clamping** -- Multiple force systems sum to unbounded totals. A single near-coincident pair produces near-infinite repulsion that cascades. Solution: clamp total force magnitude before integration; budget per-system contributions.

4. **AMD RDNA 4 compute gotchas** -- TDR timeouts (Windows kills GPU commands > 2 seconds), RDNA 4 driver immaturity for compute workloads, no CUDA fallback. Solution: profile dispatch timing, test on target hardware early, implement GPU error recovery.

5. **UI rework scope creep** -- 1700-line main_window.py with interleaved concerns tempts full rewrite. Solution: restructure (extract logic to controller), don't rewrite. Theme changes first, layout second. Fixed written scope before starting.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Fix the Physics (PBF Solver + Core Forces)
**Rationale:** All four research files identify broken physics as THE blocker. Nothing else matters if particles explode. Architecture research provides a detailed PBF implementation plan. This phase has clear success criteria: particles form coherent shapes and stay alive indefinitely.
**Delivers:** Stable, unconditionally-stable particle simulation with coherent organic motion.
**Addresses:** Per-particle home positions, velocity-dependent damping, force balance presets, breathing modulation, per-frame GPU spatial hash, force clamping, double-gravity fix.
**Avoids:** SPH kernel explosion (Pitfall 1), stale spatial hash (Pitfall 2), force accumulation overflow (Pitfall 3).
**Stack:** Existing wgpu-py compute shaders only. No new dependencies.
**Verification:** Particles stay coherent for 1000+ frames. Max force magnitude never exceeds MAX_FORCE. No NaN/Inf values. 60fps at 500K particles on RX 9060 XT without TDR.

### Phase 2: Rendering Quality + Performance
**Rationale:** With stable physics, make it look like art, not a debug visualization. Eliminate the CPU readback bottleneck that caps scalability. These are rendering concerns that build on stable simulation.
**Delivers:** Gallery-quality point rendering, smooth parameter transitions, 60fps at 1M+ particles.
**Addresses:** Round soft-edged points with additive blending, smooth parameter interpolation (crossfade system), multi-octave time evolution, vortex confinement, depth-aware point sizing, GPU buffer sharing (eliminate CPU readback).
**Avoids:** Performance traps at scale (CPU readback is 4ms at 1M particles, 20ms at 5M).
**Stack:** Existing wgpu-py + pygfx. No new dependencies.

### Phase 3: UI Rework
**Rationale:** Physics works and looks good -- now make the controls match. Must come after physics is stable so controls actually do something meaningful. Scope creep risk is high; define boundaries before starting.
**Delivers:** Professional-looking interface with tiered parameter controls, qt-material theming, white viewport background option.
**Addresses:** Tiered parameter UI (6 essential sliders), background color control, collapsible panels, consistent spacing.
**Avoids:** UI scope creep (Pitfall 5). Theme changes first, layout second. Preserve all existing signal connections.
**Stack:** qt-material 2.17 (new dependency).

### Phase 4: Claude Creative Director
**Rationale:** The "intelligent" layer that sits on top of working physics, good rendering, and polished UI. Requires the parameter crossfade system from Phase 2 to avoid visual popping. Requires the tiered UI from Phase 3 to display Claude's rationale elegantly.
**Delivers:** Photo-aware AI creative direction with validated parameter generation and smooth application.
**Addresses:** ClaudeDirector module, ParameterSchema (Pydantic), ClaudePanel UI, Claude preset naming, direction variations.
**Avoids:** LLM latency in render loop (Pitfall 6 from PITFALLS.md). All API calls async via existing EnrichmentWorker pattern. Parameter crossfade prevents visual discontinuity.
**Stack:** anthropic 0.84.0, pydantic 2.x (new dependencies).

### Phase 5: Polish and Depth Quality
**Rationale:** Final quality pass. Depth map post-processing improves the raw material that feeds everything. Can partially run in parallel with earlier phases.
**Delivers:** Better depth maps (histogram equalization, CLAHE), color field evolution, remaining differentiators.
**Avoids:** Depth map quality issues (Pitfall 7 from PITFALLS.md).

### Phase Ordering Rationale

- **Phase 1 must come first** because all research converges: broken physics blocks everything. Architecture research provides a complete PBF implementation plan with 5 compute shader passes. Pitfalls research identifies 3 critical bugs (stale hash, kernel explosion, force overflow) all fixed by this phase.
- **Phase 2 before Phase 3** because rendering quality validates physics work visually, and the parameter crossfade system built here is needed by both UI (Phase 3) and Claude (Phase 4).
- **Phase 3 before Phase 4** because Claude's creative direction needs the tiered UI and Claude panel integrated into a clean layout.
- **Phases 3 and 4 could partially overlap** since Claude integration is architecturally independent (new modules, not modifications to existing UI code).
- **Phase 5 is flexible** -- depth map quality work can happen any time, and color field evolution is a nice-to-have.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (PBF Solver):** GPU prefix-sum implementation on AMD/wgpu needs validation. PBF algorithm is well-documented (Macklin & Muller 2013, 1000+ citations) but the specific wgpu-py compute shader integration for 5-pass pipeline needs prototyping. RDNA 4 wavefront size (32 vs 64 on older AMD) may affect workgroup size choices.
- **Phase 2 (GPU Buffer Sharing):** pygfx custom shader API for reading from compute storage buffers has MEDIUM confidence. The exact wgpu buffer interop mechanism needs validation. Fallback (in-place buffer update) is known-good but slower.

Phases with standard patterns (skip research-phase):
- **Phase 3 (UI Rework):** qt-material theming is one-line application. PySide6 layout restructuring is standard Qt development. Well-documented.
- **Phase 4 (Claude Integration):** Anthropic structured outputs are production-ready. Pydantic schema generation works directly with the API. The existing EnrichmentWorker pattern provides the async template.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All kept technologies are proven in v1.0. New additions (anthropic, pydantic, qt-material) are stable, well-documented packages with confirmed version compatibility. Taichi/Warp/PySPH rejection is well-reasoned with specific technical blockers. |
| Features | HIGH | Feature list derived from Anadol studio analysis, Houdini/TouchDesigner patterns, and Bridson's curl-noise paper. The "four forces in equilibrium" formula is grounded in both academic and professional practice. Anti-features are well-justified. |
| Architecture | HIGH | PBF algorithm is foundational (1000+ citations). Root cause analysis of explosion bugs is based on direct code review with specific line numbers. Component boundaries are clear. |
| Pitfalls | HIGH | Pitfalls derived from direct codebase analysis (specific files, line numbers, mathematical proof of kernel coefficient explosion). AMD-specific risks are the lowest confidence area but mitigation strategies are concrete. |

**Overall confidence:** HIGH

### Gaps to Address

- **GPU buffer sharing between wgpu compute and pygfx render:** MEDIUM confidence. The exact API for making pygfx read from a compute shader's output buffer needs prototyping. Fallback exists (in-place numpy update) but defeats the performance goal. Validate early in Phase 2.
- **RDNA 4 compute shader behavior:** No project-specific testing evidence. RDNA 4 is new hardware with potentially immature compute drivers. Validate PBF solver on target hardware immediately after Phase 1 implementation, not at the end.
- **PBF parameter tuning for artistic (not physical) results:** PBF is designed for physically plausible fluids. Tuning it for aesthetically pleasing data sculptures (where "physically wrong" may look better) requires experimentation. The `solver_iterations` parameter (1=gas, 4=liquid) provides the primary creative control, but rest_density and artificial pressure constants will need artistic tuning.
- **qt-material + pygfx viewport interaction:** qt-material applies global stylesheets that could interfere with the wgpu viewport surface. Stack research suggests isolating the viewport widget via QSS specificity, but this needs verification.

## Sources

### Primary (HIGH confidence)
- [Position Based Fluids -- Macklin & Muller 2013](https://mmacklin.com/pbf_sig_preprint.pdf) -- foundational PBF algorithm
- [pygfx 0.16.0 docs](https://docs.pygfx.org/stable/basics.html) -- rendering framework
- [wgpu-py 0.31.0](https://github.com/pygfx/wgpu-py) -- GPU compute + rendering
- [Anthropic Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) + [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- Claude API patterns
- [Bridson et al. -- Curl-Noise for Procedural Fluid Flow (2007)](https://www.researchgate.net/publication/216813629_Curl-noise_for_procedural_fluid_flow) -- flow field foundation
- Direct codebase analysis of `sph.wgsl`, `forces.wgsl`, `integrate.wgsl`, `buffers.py`, `main_window.py` -- bug identification
- [SideFX POP Attract Documentation](https://www.sidefx.com/docs/houdini/nodes/dop/popattract.html) -- home position attraction pattern

### Secondary (MEDIUM confidence)
- [WebGPU Fluid Simulations -- Codrops](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/) -- 100K particles on iGPU via WebGPU compute
- [Refik Anadol Works](https://refikanadol.com/works/) -- primary aesthetic reference
- [qt-material docs](https://qt-material.readthedocs.io/) -- theming integration
- [Emil Dziewanowski -- Curl Noise](https://emildziewanowski.com/curl-noise/) -- practical implementation
- [wgpu-py buffer mapping discussion](https://github.com/pygfx/wgpu-py/issues/114) -- GPU buffer sharing feasibility

### Tertiary (LOW confidence)
- AMD ROCm Blog on Taichi -- focused on Instinct (datacenter), not consumer RDNA
- RDNA 4 compute driver maturity -- inferred from hardware newness, no direct testing evidence

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
