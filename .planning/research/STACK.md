# Stack Research: v2.0 Additions

**Domain:** Fluid physics, organic motion, UI rework, Claude-driven creative direction
**Researched:** 2026-03-15
**Confidence:** MEDIUM — fluid physics on AMD consumer GPUs has limited precedent; UI and Claude integration are HIGH confidence

## Executive Summary

The v1.0 stack (Python 3.12, PySide6, pygfx/wgpu, ONNX+DirectML, custom WGSL shaders) is fundamentally sound and should be **kept, not replaced**. The v2.0 question is not "replace the stack" but "what do we add for fluid physics and how do we improve what exists."

For fluid physics: **stay with custom WGSL compute shaders via wgpu-py**. The project already has a working SPH implementation (`sph.wgsl`) with spatial hashing, poly6/spiky kernels, and pressure/viscosity forces. The problem in v1.0 was not the technology -- it was the physics tuning (broken forces, missing surface tension, no coherent form shaping). Taichi Lang is tempting but introduces a transpiler layer that cannot share GPU buffers with pygfx/wgpu, forcing expensive CPU roundtrips. NVIDIA Warp is CUDA-only and dead on arrival for AMD.

For UI: **keep PySide6, add qt-material for Material Design theming**. The framework is correct; the v1.0 problem was layout and polish, not toolkit choice.

For Claude integration: **anthropic SDK v0.84.0 with structured outputs and tool use**. Define parameter schemas as tools, let Claude "call" them to set simulation parameters.

## Keep vs Replace Verdict

| Current Component | Verdict | Rationale |
|-------------------|---------|-----------|
| Python 3.12 | **KEEP** | ROCm pinned to 3.12, everything supports it |
| PySide6 6.8+ | **KEEP** | Best Qt bindings, LGPL, proven pygfx integration |
| pygfx 0.16.0 | **KEEP** | No viable alternative for AMD-compatible 3D Python rendering |
| wgpu-py 0.31.0 | **KEEP** | Foundation for compute shaders AND rendering, actively maintained |
| rendercanvas 2.6+ | **KEEP** | Bridges pygfx to Qt, no alternative needed |
| ONNX+DirectML | **KEEP** | Lightweight GPU inference, works on any DX12 GPU |
| Custom WGSL shaders | **KEEP + EXPAND** | Already have SPH foundation, needs tuning not replacement |
| extcolors | **KEEP** | Simple, works |
| OpenCV | **KEEP** | Standard image processing |

## New Stack Additions for v2.0

### Fluid Physics & Organic Motion

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Custom WGSL SPH (expand existing) | N/A | Coherent fluid simulation | Already have `sph.wgsl` with spatial hashing, poly6/spiky kernels. Needs: surface tension implementation, vorticity confinement, form-shaping attractors, parameter tuning. Zero new dependencies. Runs on AMD via Vulkan/DX12. | HIGH |
| noise.py (or inline WGSL) | N/A | Organic curl noise fields | Already have `noise.wgsl` and `flow_field.wgsl`. Expand with 3D curl noise for organic flowing motion. No new dependency. | HIGH |
| scipy.spatial | 1.14+ (existing) | CPU-side spatial queries | Already a dependency. Use for offline point cloud analysis, Voronoi, Delaunay for mesh-like organic forms. | HIGH |

### UI Rework

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| qt-material | 2.17 | Material Design theming | Instant professional look. Supports PySide6 natively. Dark/light themes, custom accent colors, runtime theme switching. One-line application: `apply_stylesheet(app, theme='dark_teal.xml')`. | HIGH |
| PySide6 QSS | built-in | Custom widget styling | For fine-tuning beyond qt-material defaults. White viewport background, clean panel borders, slider styling. | HIGH |

### Claude-Driven Creative Direction

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| anthropic | 0.84.0 | Claude API client | Official SDK. Supports structured outputs (beta: `structured-outputs-2025-11-13`), tool use for parameter control. | HIGH |
| pydantic | 2.x | Parameter schema definition | Define simulation parameter schemas that Claude returns as structured output. Type-safe, validates Claude responses automatically. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| noise (perlin-noise) | 1.2.2 | CPU-side noise generation | For pre-computing noise textures to upload to GPU. Alternative to pure WGSL noise if CPU path needed. | MEDIUM |
| scikit-learn | 1.5+ | Clustering for sculpture forms | K-means/DBSCAN to find natural groupings in point clouds before fluid sim. Optional, CPU-only. | LOW |

## Detailed Technology Analysis

### Why NOT Taichi Lang

**Taichi Lang v1.7.4** is a productive GPU compute framework with a Vulkan backend that theoretically works on AMD consumer GPUs. It excels at particle simulations -- the taichi_elements project simulates 1 billion MPM particles. However, for Apollo 7 it is the wrong choice:

1. **No GPU buffer interop with wgpu/pygfx.** Taichi allocates its own GPU memory via its own Vulkan instance. pygfx uses a separate wgpu Vulkan/DX12 instance. There is no shared buffer API between them. Data must roundtrip: Taichi GPU -> CPU (numpy) -> wgpu GPU. At 500K+ particles per frame, this CPU bounce kills real-time performance.

2. **Redundant abstraction.** Apollo 7 already writes WGSL compute shaders that run on the same wgpu device as the renderer. Adding Taichi means maintaining two GPU compute systems doing the same thing.

3. **Version stability concerns.** Taichi v1.7.4 (July 2025) is the latest stable release. The Vulkan backend works but is less battle-tested than CUDA on consumer AMD RDNA 4 hardware. No RDNA 4-specific testing evidence found.

4. **Build complexity.** Taichi's pip package is 100MB+ and brings its own LLVM-based compiler. Heavy dependency for a feature achievable with existing WGSL shaders.

**Verdict: Do not add Taichi.** Improve the existing WGSL SPH shaders instead.

*Sources: [Taichi GitHub](https://github.com/taichi-dev/taichi), [Taichi Vulkan Docs](https://docs.taichi-lang.org/docs/taichi_vulkan), [Taichi ndarray interop](https://docs.taichi-lang.org/docs/master/ndarray), [PyPI taichi 1.7.4](https://pypi.org/project/taichi/)*

### Why NOT NVIDIA Warp

**NVIDIA Warp v1.12.0** (March 2026) is an excellent GPU simulation framework -- for NVIDIA GPUs. It is CUDA-only. The documentation explicitly states "GPU support requires a CUDA-capable NVIDIA GPU." There is no Vulkan, OpenCL, or DirectX backend. No AMD GPU support exists or is planned.

**Verdict: Completely incompatible with project hardware.** Do not consider.

*Source: [NVIDIA Warp GitHub](https://github.com/NVIDIA/warp), [Warp Docs](https://nvidia.github.io/warp/)*

### Why NOT PySPH / pySPlisHSPlasH

**PySPH** (pypr/pysph) supports OpenCL for GPU acceleration, which theoretically works on AMD GPUs. However:

1. **Scientific computing focus.** PySPH is designed for engineering SPH simulations (dam breaks, fluid in containers), not artistic data sculptures. The API is geared toward physically accurate results, not visually appealing ones.

2. **No real-time rendering integration.** PySPH outputs particle positions as numpy arrays. Getting those into pygfx requires the same CPU roundtrip problem as Taichi, but worse -- PySPH is not designed for interactive frame-by-frame stepping.

3. **OpenCL on Windows AMD.** AMD's OpenCL support on Windows works but is a legacy path. The future is Vulkan compute, which the project already uses via wgpu.

4. **pySPlisHSPlasH** has CUDA-only GPU acceleration. CPU mode only on AMD.

**Verdict: Overhead without benefit.** The existing WGSL SPH shaders are better suited to this use case.

*Sources: [PySPH GitHub](https://github.com/pypr/pysph), [pySPlisHSPlasH PyPI](https://pypi.org/project/pySPlisHSPlasH/)*

### Why EXPAND Custom WGSL Shaders (Recommended)

The existing `sph.wgsl` implements:
- Spatial hash grid (128x128x128) for O(N*k) neighbor search
- Poly6 kernel for density estimation
- Spiky kernel gradient for pressure forces
- Viscosity kernel laplacian for viscosity forces
- Workgroup size 256, efficient GPU utilization

What it is **missing** for v2.0 organic forms:
- **Surface tension** (currently a placeholder returning `vec3(0.0)`)
- **Vorticity confinement** (adds swirling, organic motion)
- **Curl noise integration** (combine flow_field.wgsl with SPH forces)
- **Form-shaping attractors** (guide particles toward organic shapes)
- **XSPH velocity smoothing** (smoother collective motion)
- **Boundary handling** (contain forms within sculpture volume)
- **Parameter presets** (tuned sets for waves, morphism, breathing)

All of these are WGSL shader enhancements -- no new library dependencies. The compute shaders run on the same wgpu device as the renderer, sharing GPU buffers with zero copy overhead.

### Claude-Driven Parameter Control Architecture

Use Claude's tool use API to let Claude "set" simulation parameters:

```python
# Define tools that map to simulation parameters
tools = [
    {
        "name": "set_fluid_parameters",
        "description": "Set SPH fluid simulation parameters for the data sculpture",
        "input_schema": {
            "type": "object",
            "properties": {
                "viscosity": {"type": "number", "minimum": 0, "maximum": 1},
                "pressure_strength": {"type": "number", "minimum": 0, "maximum": 10},
                "surface_tension": {"type": "number", "minimum": 0, "maximum": 1},
                "noise_amplitude": {"type": "number", "minimum": 0, "maximum": 5},
                "mood": {"type": "string", "enum": ["calm", "turbulent", "breathing", "morphing"]},
            },
            "required": ["mood"]
        }
    }
]
```

The `anthropic` SDK v0.84.0 supports structured outputs via `client.messages.parse()` with Pydantic models, and tool use via standard `client.messages.create()`. Both approaches work. Tool use is more natural for this case -- Claude "calls" parameter-setting functions based on its analysis of the source photos.

*Sources: [Anthropic Tool Use Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview), [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [anthropic PyPI](https://pypi.org/project/anthropic/)*

### UI Rework: qt-material

**qt-material v2.17** provides Material Design theming for PySide6 with minimal code:

```python
from qt_material import apply_stylesheet
apply_stylesheet(app, theme='dark_teal.xml', extra={'density_scale': '-1'})
```

Features relevant to Apollo 7:
- 20+ built-in dark/light themes
- Custom accent color via XML configuration
- Runtime theme switching
- Custom CSS overrides for fine-tuning
- Density scaling for compact/spacious layouts
- Compatible with PySide6 6.8+

For the white viewport background requested in PROJECT.md, override the viewport widget specifically via QSS while keeping the rest of the UI themed.

*Source: [qt-material PyPI](https://pypi.org/project/qt-material/), [qt-material docs](https://qt-material.readthedocs.io/)*

## Installation (v2.0 additions only)

```bash
# Claude API integration
pip install anthropic>=0.84.0 pydantic>=2.0

# UI theming
pip install qt-material>=2.17

# No other new dependencies required -- fluid physics uses existing wgpu-py compute shaders
```

## What NOT to Add

| Avoid | Why | Do Instead |
|-------|-----|------------|
| Taichi Lang | No GPU buffer sharing with wgpu/pygfx, redundant compute layer, heavy dependency | Expand existing WGSL compute shaders |
| NVIDIA Warp | CUDA-only, zero AMD support | Custom WGSL via wgpu-py |
| PySPH / pySPlisHSPlasH | Scientific focus, no real-time rendering integration, CPU roundtrip | Custom WGSL SPH (already implemented) |
| PyOpenCL | Legacy GPU compute path, AMD moving to Vulkan | wgpu compute shaders (WGSL) |
| DearPyGui | No pygfx integration, GPU-rendered UI looks non-native | Keep PySide6 + qt-material |
| Electron / web UI | Massive complexity increase for no benefit | Keep PySide6 |
| LangChain | Over-abstraction for simple tool-use pattern | Direct anthropic SDK |
| AutoGen / CrewAI | Multi-agent frameworks, total overkill | Single Claude API call with tool use |

## Version Compatibility Matrix (v2.0 additions)

| Package | Version | Python | Works With | Notes |
|---------|---------|--------|------------|-------|
| anthropic | 0.84.0 | >=3.9 | PySide6, any | Pure Python HTTP client, no GPU dependency |
| pydantic | 2.x | >=3.8 | anthropic SDK | Used internally by anthropic SDK already |
| qt-material | 2.17 | >=3.7 | PySide6 6.8+ | Verified PySide6 support |

**No new GPU dependencies.** All fluid physics work uses the existing wgpu-py 0.31.0 compute shader pipeline. This is deliberate -- adding a second GPU compute system would create buffer-sharing nightmares.

## Stack Patterns by Variant

**If WGSL SPH performance is insufficient at high particle counts (>500K):**
- Optimize spatial hash grid: increase GRID_SIZE, use bitonic sort on GPU for prefix sums
- Reduce neighbor search radius (smoothing_radius)
- Use LOD: simulate fewer particles, render more via instancing
- Last resort: consider Taichi with CPU roundtrip, accepting 30fps instead of 60fps

**If Claude parameter suggestions feel generic:**
- Pass more context: color palette extracted, depth map statistics, semantic CLIP embeddings
- Use multi-turn conversation: first analyze photos, then suggest parameters, then refine
- Store successful parameter sets as presets for future reference

**If qt-material styling conflicts with pygfx viewport:**
- Isolate the viewport widget from global stylesheet using QSS specificity
- Use `setStyleSheet("")` on the viewport container to reset inherited styles
- rendercanvas WgpuWidget renders independently of Qt styling (it is a native surface)

## Key Architecture Decision: Single GPU Compute Pipeline

The most important stack decision for v2.0 is **NOT adding a second GPU compute framework**. The existing architecture has a single wgpu device that:
1. Runs compute shaders (SPH, forces, noise, flow fields)
2. Renders the result (pygfx point clouds, particles)
3. Shares GPU buffers between compute and render with zero copy

Adding Taichi, PySPH, or any external GPU compute framework breaks this. Data would need to go GPU->CPU->GPU every frame. For a real-time data sculpture application running at 60fps with hundreds of thousands of particles, this is unacceptable.

The right approach is: **write better WGSL shaders, not more Python dependencies.**

## Sources

### Official Documentation (HIGH confidence)
- [pygfx 0.16.0 — PyPI](https://pypi.org/project/pygfx/) — latest version confirmed March 3, 2026
- [wgpu-py 0.31.0 — PyPI](https://pypi.org/project/wgpu/) — latest version confirmed March 2, 2026
- [anthropic 0.84.0 — PyPI](https://pypi.org/project/anthropic/) — latest version confirmed February 25, 2026
- [qt-material 2.17 — PyPI](https://pypi.org/project/qt-material/) — latest version confirmed April 21, 2025
- [Taichi 1.7.4 — PyPI](https://pypi.org/project/taichi/) — latest stable, July 31, 2025
- [NVIDIA Warp 1.12.0 — GitHub](https://github.com/NVIDIA/warp) — CUDA-only confirmed
- [Anthropic Tool Use Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Taichi Vulkan Backend](https://docs.taichi-lang.org/docs/taichi_vulkan)
- [Taichi ndarray Interop](https://docs.taichi-lang.org/docs/master/ndarray)

### Community Sources (MEDIUM confidence)
- [AMD ROCm Blog — Taichi on AMD GPUs](https://rocm.blogs.amd.com/artificial-intelligence/taichi/README.html) — AMD Instinct focus, not consumer RDNA
- [PySPH GitHub](https://github.com/pypr/pysph) — OpenCL support confirmed, scientific focus
- [Codrops — WebGPU Fluid Simulations](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/) — 100K particles on iGPU via WebGPU compute
- [PythonGUIs — GUI Framework Comparison 2026](https://www.pythonguis.com/faq/which-python-gui-library/) — PySide6 recommended for professional apps

---
*Stack research for: Apollo 7 v2.0 — fluid physics, organic motion, UI rework, Claude creative direction*
*Researched: 2026-03-15*
