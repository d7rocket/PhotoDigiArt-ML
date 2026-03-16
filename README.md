# PhotoDigiArt-ML

**Transform photographs into living 3D data sculptures.**

PhotoDigiArt-ML (Apollo 7) is a local-first generative art pipeline that treats photos as datasets, not prompts. It extracts geometric structure, color signals, and depth from source images, then transforms them into interactive particle sculptures — flowing point clouds with fluid physics — inspired by Refik Anadol's data sculptures.

https://github.com/user-attachments/assets/placeholder

---

## Features

### Data-Driven Art Pipeline
- **Photo ingestion** — single images or entire folders (JPEG, PNG, TIFF, RAW)
- **Feature extraction** — edges, contours, depth maps (Depth Anything V2), color palettes, CLIP semantics
- **Point cloud generation** — depth-projected or feature-clustered 3D layouts
- **Real-time viewport** — 60fps interactive 3D exploration via pygfx/wgpu

### Position Based Fluids (PBF) Physics
- **GPU-accelerated solver** — 7 WGSL compute shaders running entirely on the GPU
- **Organic motion** — curl noise flow fields, vortex confinement, breathing modulation
- **Creative control** — "Cohesion" slider morphs sculptures from ethereal gas to dense liquid
- **Stable indefinitely** — CFL-adaptive timestep, velocity clamping, no explosions

### Claude AI Creative Direction
- **Photo analysis** — Claude examines your photo and suggests sculpture parameters with artistic rationale
- **One-click apply** — suggestions crossfade smoothly into the viewport (~400ms ease-out)
- **Iterative refinement** — "More Fluid", "More Structured", "More Vibrant", "More Subtle" direction buttons
- **Fully async** — viewport never freezes during API calls; works completely offline without Claude

### Gallery-Quality Rendering
- **Luminous particles** — soft Gaussian blobs with additive blending, rich color saturation
- **White gallery background** — warm off-white (#F8F6F3) like fine art paper
- **Smooth transitions** — all parameter changes crossfade via cubic ease-out engine
- **CLAHE-enhanced depth** — full contrast depth maps for continuous 3D volumes, not flat layers

### Polished Desktop Application
- **Material dark theme** — qt-material with electric blue accent (#0078FF)
- **Tabbed interface** — Create (sculpt) / Explore (AI + presets) / Export
- **6 essential sliders** — Cohesion, Home Strength, Flow, Breathing, Point Size, Opacity
- **Preset grid** — gradient thumbnail cards for 6 built-in presets, click to crossfade
- **Save/load projects** — full project persistence with PNG export up to 15K resolution

---

## Quick Start

### Requirements
- **Python 3.12+**
- **GPU** — any Vulkan-capable GPU (developed on AMD RDNA 4 / RX 9060 XT)
- **OS** — Windows 11 (primary), should work on Linux/macOS with compatible GPU drivers

### Install

```bash
git clone https://github.com/d7rocket/PhotoDigiArt-ML.git
cd PhotoDigiArt-ML

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Linux/macOS

# Install
pip install -e .

# Install optional AI features
pip install anthropic qt-material
```

### Download Models

Download the Depth Anything V2 ONNX model (~25MB):

```bash
# See models/README.md for full instructions
# Place the model at: models/depth_anything_v2_vits.onnx
```

CLIP model (optional, for semantic extraction):
```bash
# Place at: models/clip_vit_b32_visual.onnx
```

### Run

```bash
python -m apollo7
```

1. **Load photos** — File > Open Photo or drag a folder
2. **Extract features** — click "Extract" in the Create tab
3. **Simulate** — click "Simulate" in the toolbar
4. **Explore presets** — switch to Explore tab, click preset cards
5. **AI direction** — add your Anthropic API key in Settings, click "Analyze with Claude"

---

## Architecture

```
apollo7/
├── api/              # Claude API integration (enrichment, structured params)
├── animation/        # CrossfadeEngine, ParameterAnimator
├── collection/       # Multi-photo collection analysis
├── config/           # Settings, defaults, ranges
├── discovery/        # Discovery mode, random walk, dimensional mapper
├── extraction/       # Feature extractors (color, edge, depth, CLIP)
├── gui/
│   ├── panels/       # Controls, Simulation, PostFX, Presets, Claude, Discovery
│   ├── widgets/      # Viewport, CrossfadeWidget, PresetCard, ToolbarStrip
│   ├── main_window.py
│   └── theme.py      # qt-material setup + custom overrides
├── ingestion/        # Photo loading, thumbnailing, metadata
├── mapping/          # Feature-to-parameter mapping engine
├── pointcloud/       # Point cloud generation from depth/features
├── postfx/           # Bloom, DOF, SSAO, motion trails
├── project/          # Save/load, presets, export
├── rendering/        # Renderer, point materials, camera
├── simulation/       # PBF solver, WGSL shaders, sim engine
│   └── shaders/      # 7 WGSL compute shaders for GPU physics
└── workers/          # Background thread workers
```

### Tech Stack
| Layer | Technology |
|-------|-----------|
| GUI Framework | PySide6 + qt-material |
| 3D Rendering | pygfx (WebGPU-based) |
| GPU Compute | wgpu + WGSL shaders |
| Physics | Position Based Fluids (PBF) |
| Depth Estimation | Depth Anything V2 (ONNX) |
| Semantic Analysis | CLIP ViT-B/32 (ONNX) |
| AI Integration | Anthropic Claude API |
| Image Processing | OpenCV, Pillow, NumPy |

---

## GPU Compatibility

PhotoDigiArt-ML uses **WebGPU/Vulkan** for both rendering and compute, making it GPU-vendor agnostic:

| GPU | Status |
|-----|--------|
| AMD RDNA 4 (RX 9060 XT) | Developed and tested on this |
| AMD RDNA 1-3 | Should work (Vulkan support) |
| NVIDIA GTX/RTX | Should work (Vulkan support) |
| Intel Arc | Should work (Vulkan support) |
| Integrated GPUs | May work with reduced particle counts |

No CUDA dependency. No ROCm dependency. Pure Vulkan/WebGPU.

---

## Claude AI Integration

Claude integration is **entirely optional** — the full pipeline works offline. When enabled:

1. Add your Anthropic API key in **Settings > Preferences**
2. Load a photo and go to the **Explore** tab
3. Click **"Analyze with Claude"** — Claude sees your photo and suggests parameters
4. Review the artistic rationale and click **"Apply to Sculpture"**
5. Refine with direction buttons or click **"Start Over"** for a fresh suggestion

All API calls run in background threads. The viewport never freezes.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -q

# Lint
ruff check apollo7/
```

---

## Inspiration

This project draws creative inspiration from [Refik Anadol](https://refikanadol.com/)'s data sculptures — massive datasets rendered as flowing, organic 3D forms. PhotoDigiArt-ML brings that aesthetic to desktop hardware, letting anyone transform their photos into living data art.

---

## License

MIT

---

*Built with PySide6, pygfx, wgpu, and Claude.*
