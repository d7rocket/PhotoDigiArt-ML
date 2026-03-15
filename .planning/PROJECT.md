# Apollo 7

## What This Is

A local data-driven generative art pipeline that treats photographs as datasets, not prompts. It extracts geometric structure, color/texture signals, and semantic meaning from one to thousands of source photos and transforms those signals into interactive 3D data sculptures — flowing point clouds, particle systems, and fluid-like data morphologies in the spirit of Refik Anadol's work. The entire pipeline runs locally on desktop hardware, with optional Claude API integration for semantic annotation and creative direction.

## Core Value

The transformation process — photos become data, data becomes art. The pipeline must faithfully extract meaningful signals from source images and render them as explorable 3D sculptures that visually embody the input data.

## Current Milestone: v2.0 — Make It Alive

**Goal:** Transform the rough v1.0 prototype into a product that produces organic, living data sculptures — fix physics, rework UI, let Claude drive creative direction.

**Target features:**
- Fix particle physics so forces create coherent, organic forms (waves, morphism, flow)
- Research and potentially adopt better fluid physics engine / tech stack
- Fix depth map extraction (saturation, color richness)
- Complete UI rework — clean, polished, white viewport, logical layout
- Claude-driven creative direction — Claude analyzes photos and sets parameters
- Make sculptures feel alive — flowing motion, organic morphing

## Requirements

### Validated

- ✓ Ingest single photos or bulk collections — v1.0
- ✓ Extract geometric features: edges, shapes, depth maps — v1.0 (depth quality needs fixing)
- ✓ Extract color/texture features: palettes, gradients — v1.0
- ✓ Extract semantic meaning via CLIP — v1.0
- ✓ Transform features into 3D point clouds — v1.0
- ✓ Basic real-time 3D viewport — v1.0
- ✓ Desktop GUI skeleton — v1.0 (needs rework)
- ✓ Basic GPU particle simulation — v1.0 (forces broken)
- ✓ Save/load projects, PNG export — v1.0
- ✓ Basic Claude API integration — v1.0

### Active

- [ ] Coherent particle physics — forces that shape into organic forms
- [ ] Fluid physics engine — research and adopt best option for AMD GPU
- [ ] Rich depth maps — saturated, full color range
- [ ] Complete UI rework — clean layout, white viewport, polished controls
- [ ] Claude-driven creative parameters — Claude suggests parameter sets
- [ ] Living sculptures — flowing motion, organic morphing, visual breathing
- [ ] Optimal tech stack — evaluate alternatives to pygfx/wgpu/PySide6

### Out of Scope

- Prompt-based image generation (Stable Diffusion / DALL-E style) — this is data transformation, not text-to-image
- Cloud rendering — all heavy computation stays local
- Mobile app — desktop only
- Video input processing — photos only
- Real-time camera feed — batch processing only

## Context

- **Hardware:** AMD PowerColor RX 9060 XT 16GB (RDNA 4). No CUDA — pipeline must use ROCm, Vulkan compute, or CPU fallbacks. 16GB VRAM is generous for point cloud rendering.
- **Inspiration:** Refik Anadol's data sculptures — massive datasets rendered as flowing, organic 3D forms. The aesthetic is emergent beauty from structured data.
- **Input flexibility:** Sometimes a single portrait analyzed in depth, sometimes an entire photo archive where patterns emerge from volume. The pipeline must handle both gracefully.
- **Dual interaction model:** Full manual control for when the artist knows what they want, and a guided discovery mode for when the data should lead.

## Constraints

- **GPU Compatibility**: Must work on AMD RDNA 4 (RX 9060 XT) — no CUDA-only dependencies
- **Local-first**: Core pipeline must function without internet. Claude integration is optional/additive
- **Platform**: Windows 11 desktop

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| AMD GPU target (no CUDA) | User's hardware is RX 9060 XT | — Pending |
| Real-time viewport over offline rendering | User wants interactive exploration | — Pending |
| Desktop GUI over CLI or node editor | User preference for visual controls | — Pending |
| Both control + discovery modes | Artist wants full control AND surprise | — Pending |

---
*Last updated: 2026-03-15 after v2.0 milestone start*
