# Stack Research

**Domain:** Data-driven generative art pipeline (local, AMD GPU, Windows 11)
**Researched:** 2026-03-14
**Overall Confidence:** MEDIUM — ROCm on Windows is real but young; rendering stack is proven but niche

## Executive Summary

The AMD GPU constraint on Windows is the single biggest stack driver. As of early 2026, AMD has delivered on its ROCm-on-Windows promise: PyTorch 2.9.1 runs natively on RX 9060 XT via ROCm 7.2 with Python 3.12. For ML inference where PyTorch is overkill, ONNX Runtime + DirectML provides a lighter-weight GPU-accelerated path that works on any DirectX 12 GPU without driver-specific installs.

For 3D rendering, pygfx (built on wgpu/WebGPU) is the clear choice over Open3D or raw OpenGL. It renders via Vulkan/DX12 natively, has first-class point cloud and particle support, embeds cleanly into Qt via rendercanvas, and is actively maintained (v0.16.0, March 2026). This is the only Python 3D rendering library that is both GPU-vendor-agnostic and designed for real-time interactive scenes.

For the GUI shell, PySide6 (Qt 6) is the right choice. pygfx has official Qt integration examples, rendercanvas provides a Qt backend, and Qt gives you dockable panels, sliders, and professional desktop UX out of the box. DearPyGui is tempting but has no proven pygfx integration path.

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12 | Runtime | Required by ROCm 7.2 Windows wheels. No choice here. | HIGH |
| PyTorch + ROCm | 2.9.1 + ROCm 7.2 | GPU-accelerated ML inference | Official AMD support for RX 9060 XT on Windows. Runs depth estimation, semantic models on GPU. | HIGH |
| ONNX Runtime + DirectML | 1.21+ | Lightweight GPU inference | For models where PyTorch is unnecessary (CLIP embeddings, edge detection CNNs). Works on any DX12 GPU, no ROCm driver dependency. Fallback path. | HIGH |
| pygfx | 0.16.0 | 3D rendering engine | Built on wgpu (WebGPU). Renders via Vulkan/DX12. GPU-vendor-agnostic. Point clouds, particles, custom shaders. ThreeJS-inspired API. Actively maintained. | HIGH |
| wgpu-py | 0.31.0 | WebGPU bindings | Low-level GPU access for compute shaders (fluid sim, particle physics). Used by pygfx internally, exposed for custom compute pipelines. | HIGH |
| rendercanvas | 2.6.3 | Canvas abstraction | Bridges pygfx rendering to Qt widgets. Provides WgpuWidget for embedding 3D viewports in PySide6 layouts. | HIGH |
| PySide6 | 6.8+ | Desktop GUI framework | Official Qt 6 Python bindings. Dockable panels, sliders, menus. pygfx has official Qt integration examples. | HIGH |

### Image Processing & Feature Extraction

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| OpenCV (opencv-python-headless) | 4.10+ | Geometric feature extraction | Edge detection (Canny, Sobel), contour finding, shape analysis, histogram computation. Industry standard, CPU-based, fast enough for batch processing. | HIGH |
| scikit-image | 0.24+ | Advanced image analysis | Texture descriptors (LBP, GLCM), segmentation, morphological operations. Complements OpenCV for features OpenCV lacks. | HIGH |
| Pillow | 11+ | Image I/O and basic transforms | Loading, resizing, color space conversion. Lightweight dependency. | HIGH |
| Depth Anything V2/V3 | V2 or V3 | Monocular depth estimation | Extracts depth maps from single photos. Run via PyTorch+ROCm or export to ONNX+DirectML. V2 is proven; V3 (Nov 2025) is better but verify ONNX export stability. | MEDIUM |
| CLIP (OpenAI) | ViT-B/32 | Semantic image understanding | Extracts semantic embeddings from photos. Use ONNX-exported version via DirectML for GPU acceleration without PyTorch overhead. | MEDIUM |
| colorthief / extcolors | latest | Color palette extraction | Dominant color extraction from images. Pure Python, fast. | HIGH |

### Compute & Simulation

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| wgpu-py compute shaders | 0.31.0 | GPU particle physics, fluid sim | Write WGSL compute shaders for particle dynamics, force fields, fluid-like behaviors. Runs on Vulkan/DX12 — no CUDA needed. This is how you get real-time particle animation on AMD. | MEDIUM |
| NumPy | 2.1+ | Array operations | Foundation for all numerical work. Point cloud manipulation, feature vector math. | HIGH |
| SciPy | 1.14+ | Spatial algorithms | KD-trees for point cloud queries, interpolation for smooth field generation, clustering. | HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management | Fast, modern Python package manager. Handles the complex ROCm wheel URLs better than pip. |
| conda (miniconda) | Environment isolation | Alternative to uv if ROCm wheel resolution causes issues. AMD docs recommend conda for Python 3.12 env setup. |
| pytest | Testing | Standard. |
| ruff | Linting + formatting | Fast, replaces flake8 + black + isort. |
| pyinstaller | Distribution (future) | Package as standalone .exe if needed later. |

## Installation

```bash
# Create environment (conda approach, recommended by AMD)
conda create -n apollo7 python=3.12
conda activate apollo7

# --- ROCm SDK + PyTorch (AMD GPU ML inference) ---
pip install --no-cache-dir ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_core-7.2.0.dev0-py3-none-win_amd64.whl ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_devel-7.2.0.dev0-py3-none-win_amd64.whl ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_libraries_custom-7.2.0.dev0-py3-none-win_amd64.whl ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm-7.2.0.dev0.tar.gz

pip install --no-cache-dir ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/torch-2.9.1%2Brocmsdk20260116-cp312-cp312-win_amd64.whl ^
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/torchvision-0.24.1%2Brocmsdk20260116-cp312-cp312-win_amd64.whl

# --- ONNX Runtime + DirectML (lightweight GPU inference) ---
pip install onnxruntime-directml

# --- 3D Rendering ---
pip install pygfx rendercanvas

# --- GUI ---
pip install PySide6

# --- Image Processing ---
pip install opencv-python-headless scikit-image Pillow

# --- Utilities ---
pip install numpy scipy

# --- Color extraction ---
pip install extcolors

# --- Dev tools ---
pip install pytest ruff
```

**CRITICAL: AMD driver requirement.** Install the 26.1.1 (or later) AMD graphics driver BEFORE installing ROCm wheels. Without this driver, PyTorch will silently fall back to CPU.

**CRITICAL: pip gotcha.** Use `--no-cache-dir` for ROCm wheels. pip's dependency resolver can silently overwrite the ROCm PyTorch wheel with the CPU-only PyPI version. Consider also using `--no-deps` and installing dependencies separately.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| 3D Rendering | pygfx + wgpu | Open3D | Open3D's GPU acceleration is CUDA/SYCL-focused. AMD support is limited to Mesa OpenGL drivers. No compute shader pipeline. Not designed for artistic rendering. |
| 3D Rendering | pygfx + wgpu | Panda3D | Game engine, heavy. Overkill for data sculpture rendering. Python bindings are second-class. |
| 3D Rendering | pygfx + wgpu | vispy | OpenGL-based, aging. pygfx is its spiritual successor with modern GPU API. |
| 3D Rendering | pygfx + wgpu | Three.js (via web) | Would require Electron/browser runtime. Adds complexity. pygfx gives similar API natively in Python. |
| GUI | PySide6 | DearPyGui | No proven integration path with pygfx/wgpu. GPU-rendered UI looks different from native OS. Great for tools, wrong for a creative application that needs professional feel. |
| GUI | PySide6 | Tkinter | No modern widget set. No docking. Poor for complex creative tools. |
| GUI | PySide6 | PyQt6 | Essentially identical to PySide6 but GPL-licensed (PySide6 is LGPL). LGPL is more permissive. |
| ML Inference | PyTorch ROCm | TensorFlow | ROCm TensorFlow on Windows is less mature than PyTorch. AMD's investment is clearly PyTorch-first. |
| ML Inference (light) | ONNX+DirectML | ONNX+ROCm EP | ROCm Execution Provider for ONNX Runtime is Linux-only. DirectML is the Windows path. |
| ML Inference (light) | ONNX+DirectML | WinML | WinML is the official successor to DirectML but requires Windows 11 25H2+. If on 24H2, DirectML is safer. Revisit when WinML stabilizes. |
| Depth Estimation | Depth Anything V2 | MiDaS | Depth Anything V2/V3 surpasses MiDaS in quality. MiDaS is older. |
| Depth Estimation | Depth Anything V2 | Depth Anything V3 | V3 (Nov 2025) is better but newer. Verify ONNX export works before committing. Start with V2, upgrade to V3. |
| Package Mgmt | conda + pip | uv only | ROCm wheels use non-standard URLs. uv handles them but conda's env isolation is more battle-tested for ML stacks. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| CUDA / cuDNN | Does not work on AMD GPUs. Period. | ROCm (PyTorch) or DirectML (ONNX Runtime) |
| TensorRT | NVIDIA-only inference optimizer | ONNX Runtime + DirectML |
| OpenGL (raw) | Deprecated path. No compute shaders. Vendor-inconsistent. | wgpu (WebGPU) via pygfx — wraps Vulkan/DX12 |
| vispy | Legacy OpenGL renderer. Unmaintained relative to pygfx. | pygfx |
| matplotlib 3D | Not real-time. Not interactive. Not GPU-accelerated. | pygfx |
| Stable Diffusion / DALL-E | This project is data transformation, not text-to-image generation. Out of scope per PROJECT.md. | Feature extraction models (Depth Anything, CLIP) |
| PyOpenCL / PyCUDA | CUDA is out. OpenCL is possible but wgpu compute shaders are more modern and vendor-agnostic. | wgpu-py compute shaders (WGSL) |
| Taichi Lang | Interesting GPU compute framework but adds a transpiler dependency. wgpu compute shaders are lower-level but more predictable. | wgpu-py compute shaders |

## Stack Patterns by Variant

### If ML models run poorly on ROCm (fallback)
Export all models to ONNX format and run via `onnxruntime-directml`. DirectML works on any DX12 GPU without driver-specific installs. Slower than native ROCm but universally compatible.

### If point cloud counts exceed pygfx limits
For scenes with >5M points, write custom wgpu compute shaders for LOD (level-of-detail) decimation. Render subsets with pygfx, swap LOD levels based on camera distance.

### If fluid simulation is too complex in WGSL
Fall back to CPU-based simulation (NumPy/SciPy) at lower particle counts. Pre-compute frames, replay as animation in pygfx. Real-time fluid on GPU via wgpu compute is achievable but requires significant shader development.

### If PySide6 + pygfx integration has issues
The rendercanvas library also supports GLFW backend. Worst case: render in a standalone GLFW window alongside a PySide6 control panel. Not ideal but functional.

## Version Compatibility Matrix

| Component | Version | Python | Windows | AMD Driver | Notes |
|-----------|---------|--------|---------|------------|-------|
| PyTorch ROCm | 2.9.1 | 3.12 only | 11 | 26.1.1+ | Wheels are cp312 only |
| ONNX Runtime DirectML | 1.21+ | 3.9-3.12 | 10/11 | Any DX12 | More flexible than ROCm |
| pygfx | 0.16.0 | 3.10+ | 10/11 | Any Vulkan/DX12 | GPU-vendor-agnostic |
| wgpu-py | 0.31.0 | 3.10+ | 10/11 | Any Vulkan/DX12 | GPU-vendor-agnostic |
| rendercanvas | 2.6.3 | 3.10+ | 10/11 | N/A | Canvas abstraction |
| PySide6 | 6.8+ | 3.9-3.12 | 10/11 | N/A | Qt 6 |
| OpenCV | 4.10+ | 3.8-3.12 | 10/11 | N/A | CPU-only (fine for feature extraction) |

**Key constraint:** Python 3.12 is mandatory because ROCm wheels only ship cp312. Everything else supports 3.12, so this is not a conflict — just a hard pin.

## Dual-Path GPU Strategy

This stack uses two independent GPU acceleration paths:

1. **ROCm (PyTorch)** — For heavy ML models (Depth Anything, semantic segmentation). Requires AMD-specific driver and SDK. Higher performance for large models.

2. **DirectML (ONNX Runtime)** — For lighter ML models (CLIP embeddings, small CNNs). Works on any DX12 GPU. No AMD-specific setup. Good fallback if ROCm has issues.

3. **wgpu/Vulkan (pygfx)** — For all 3D rendering and GPU compute. Completely independent of ML stack. Uses Vulkan or DX12 backend. No vendor-specific code.

These three paths are independent. If ROCm breaks, rendering still works. If a model fails on ROCm, try ONNX+DirectML. This redundancy is deliberate given the relative youth of AMD's ML-on-Windows story.

## Sources

### Official Documentation (HIGH confidence)
- [ROCm on Radeon/Ryzen — PyTorch Windows Installation](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html)
- [ROCm Compatibility Matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
- [AMD ROCm 7.0.2 with RX 9060 Support](https://www.phoronix.com/news/AMD-ROCm-7.0.2-Released)
- [ONNX Runtime DirectML Execution Provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [AMD GPUOpen — ONNX DirectML Guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/)
- [pygfx GitHub](https://github.com/pygfx/pygfx)
- [pygfx Documentation — Qt Integration](https://docs.pygfx.org/v0.13.0/_gallery/other/integration_qt.html)
- [wgpu-py GitHub](https://github.com/pygfx/wgpu-py)
- [rendercanvas GitHub](https://github.com/pygfx/rendercanvas)
- [Depth Anything V2 GitHub](https://github.com/DepthAnything/Depth-Anything-V2)
- [Depth Anything V3 GitHub](https://github.com/ByteDance-Seed/Depth-Anything-3)
- [CLIP-ONNX GitHub](https://github.com/Lednik7/CLIP-ONNX)
- [DirectML GitHub (maintenance mode notice)](https://github.com/microsoft/DirectML)

### Industry Sources (MEDIUM confidence)
- [AMD Blog — Road to ROCm on Radeon](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html)
- [VideoCardz — AMD ROCm 7.0.2 with RX 9060](https://videocardz.com/newz/amd-releases-rocm-7-0-2-with-radeon-rx-9060-support)
- [WCCFTech — ROCm 6.4.4 PyTorch Windows](https://wccftech.com/amd-rocm-6-4-4-pytorch-support-windows-radeon-9000-radeon-7000-gpus-ryzen-ai-apus/)
- [Codrops — WebGPU Fluid Simulations](https://tympanus.net/codrops/2025/02/26/webgpu-fluid-simulations-high-performance-real-time-rendering/)
