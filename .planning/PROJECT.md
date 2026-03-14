# Apollo 7

## What This Is

A local data-driven generative art pipeline that treats photographs as datasets, not prompts. It extracts geometric structure, color/texture signals, and semantic meaning from one to thousands of source photos and transforms those signals into interactive 3D data sculptures — flowing point clouds, particle systems, and fluid-like data morphologies in the spirit of Refik Anadol's work. The entire pipeline runs locally on desktop hardware, with optional Claude API integration for semantic annotation and creative direction.

## Core Value

The transformation process — photos become data, data becomes art. The pipeline must faithfully extract meaningful signals from source images and render them as explorable 3D sculptures that visually embody the input data.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Ingest single photos or bulk collections (1 to thousands)
- [ ] Extract geometric features: edges, shapes, depth maps, spatial relationships
- [ ] Extract color/texture features: palettes, gradients, surface qualities, visual rhythm
- [ ] Extract semantic meaning: objects, scenes, mood, narrative (local models + optional Claude)
- [ ] Transform extracted features into 3D point clouds and particle systems
- [ ] Render interactive 3D data sculptures in a real-time viewport (orbit, zoom, explore)
- [ ] Desktop GUI with controls, sliders, and live preview
- [ ] High-control mode: user maps features to visuals, tunes every parameter
- [ ] Discovery mode: system proposes compositions from data, user refines
- [ ] Full local GPU/CPU/RAM utilization (generation can take hours if needed)
- [ ] Optional Claude API integration for photo annotation and artistic mapping suggestions

### Out of Scope

- Prompt-based image generation (Stable Diffusion / DALL-E style) — this is data transformation, not text-to-image
- Cloud rendering — all heavy computation stays local
- Mobile app — desktop only
- Video input processing — photos only for v1
- Real-time camera feed — batch processing only for v1

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
*Last updated: 2026-03-14 after initialization*
