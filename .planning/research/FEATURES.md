# Feature Research

**Domain:** Data-driven generative art pipeline (photo-to-data-sculpture)
**Researched:** 2026-03-14
**Confidence:** MEDIUM (established domain with clear patterns, but Apollo 7's specific niche -- desktop photo-to-sculpture pipeline -- has few direct comparators)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any data-driven generative art tool must have. Missing any of these makes the product feel broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Image ingestion (single + batch)** | Fundamental input. Every tool from TouchDesigner to Processing handles media import | Low | Must handle common formats (JPEG, PNG, TIFF, RAW). Batch = folder scanning with progress feedback |
| **Real-time 3D viewport** | Users expect to orbit, zoom, pan through their sculpture. Anadol's work is inherently spatial | High | GPU-accelerated rendering. Must maintain 30+ FPS with 100K+ points. Camera controls must feel native (orbit, dolly, pan) |
| **Point cloud rendering** | The core visual output. TouchDesigner, openFrameworks, and every 3D data-viz tool renders point clouds | Medium | Point size, color mapping, opacity. Additive blending for density visualization |
| **Color/palette extraction** | Extracting dominant colors, gradients, and color distributions from source images | Low | k-means clustering or median cut. Well-solved problem |
| **Edge/geometry detection** | Extracting structural features (edges, contours, shapes) from images | Medium | Canny, Sobel, or learned edge detection. Depth maps from monocular estimation (Depth Anything V2) |
| **Parameter controls (sliders, knobs)** | Artists expect direct manipulation. Every creative tool from Photoshop to TouchDesigner has parameter panels | Medium | Sliders, color pickers, dropdowns, numeric inputs. Must update viewport in real-time |
| **Save/load projects** | Users will close the app and return. Losing work is unacceptable | Medium | Serialize all parameters, feature data, and sculpture state. JSON or binary format |
| **Export still images** | Users need to capture their sculptures as high-res images for portfolios, prints, social media | Low | Screenshot at viewport resolution + high-res render (2x, 4x) with transparent background option |
| **Basic particle system** | Points that move, flow, react. Static point clouds feel dead compared to Anadol's flowing forms | High | GPU compute for particle physics. Noise-driven motion, attraction/repulsion forces |
| **Undo/redo** | Any creative tool without undo is hostile. Artists experiment constantly | Medium | Command pattern on parameter changes. At minimum, parameter-level undo (not pixel-level) |

### Differentiators (Competitive Advantage)

Features that set Apollo 7 apart from using TouchDesigner, Processing, or openFrameworks directly. These are the reasons someone would choose this tool specifically.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Discovery mode (AI-guided composition)** | The killer feature. System analyzes extracted data and proposes sculpture compositions. Artist refines rather than builds from scratch. No existing desktop tool does this well | Very High | Requires mapping feature-space to aesthetic-space. Start simple: randomized but constrained parameter exploration with "more like this / less like this" feedback loop |
| **Semantic feature extraction** | Understanding WHAT is in photos (objects, scenes, mood), not just pixel-level features. Photos of forests vs. cities should produce fundamentally different sculptures | High | Local models (CLIP, BLIP-2) for object/scene recognition. Optional Claude API for richer narrative annotation. This bridges data and meaning |
| **Photo-to-sculpture pipeline as single workflow** | TouchDesigner requires node programming. Processing requires coding. openFrameworks requires C++. Apollo 7 is: drop photos in, get sculpture out, refine | Medium | The integration IS the product. Each competitor can do pieces; none offer the end-to-end GUI workflow for non-programmers |
| **Feature-to-visual mapping editor** | Explicit, visible connections between extracted data (e.g., "warm colors" -> "upward particle velocity") that the artist can rewire | High | Visual mapping interface. Source features on left, visual parameters on right, drag to connect. Inspired by audio routing matrices |
| **Multi-photo pattern emergence** | When processing thousands of photos, patterns emerge that single-photo analysis misses. Clustering, trends, outliers become sculptural elements | High | Statistical analysis across the collection. t-SNE or UMAP for dimensionality reduction. Cluster visualization |
| **Claude API creative direction** | Ask Claude to interpret the data and suggest artistic directions. "These 500 sunset photos feel melancholic -- try dispersing warm particles downward with slow decay" | Medium | API integration is straightforward. The value is in prompt engineering and translating Claude's text into parameter adjustments |
| **Preset library with interpolation** | Save named presets ("Crystalline", "Organic Flow", "Data Storm") and smoothly interpolate between them. Blending presets creates new aesthetics | Medium | Parameter serialization + lerp between saved states. Keyframe timeline for animated transitions |
| **Live parameter animation** | Parameters that change over time -- sculptures that evolve, breathe, pulse. Not just static renders but living data forms | Medium | Timeline or LFO-based parameter modulation. Sine waves, noise, envelope followers mapped to any parameter |

### Anti-Features (Commonly Requested, Often Problematic)

Features to deliberately NOT build. These seem appealing but would dilute the product, add massive complexity, or conflict with the core vision.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Text-to-image / prompt-based generation** | This is Stable Diffusion / DALL-E territory. Apollo 7 transforms DATA, not prompts. Adding generation confuses the identity and competes with tools that do it better | Keep the pipeline data-driven. Claude suggests parameters, not pixels |
| **Node-based visual programming** | TouchDesigner already does this brilliantly. Building a node editor is 6+ months of work that recreates what exists. The whole point is to NOT require programming | Use a simpler mapping editor (source -> target). If users want nodes, they should use TouchDesigner |
| **Plugin/extension system** | Premature abstraction. Building a stable plugin API before the core is solid creates backward-compatibility debt that constrains future changes | Hardcode features in v1. Consider plugins only after the core pipeline is validated and stable (v2+) |
| **Video input processing** | Video frames multiply the data by 24-60x. Processing pipelines, memory management, and temporal coherence are entire research domains | Photos only for v1. Video is a future milestone after the photo pipeline is proven |
| **Real-time camera feed** | Requires low-latency capture, processing, and rendering pipeline. Completely different architecture from batch processing | Batch processing only. The Anadol aesthetic comes from large dataset processing, not live feeds |
| **Cloud rendering** | Adds server infrastructure, authentication, billing, latency concerns. Contradicts local-first philosophy | All computation stays local. The RX 9060 XT with 16GB VRAM is more than capable |
| **Social sharing / gallery features** | Scope creep into social platform territory. Export an image; let users share however they want | Export high-res images and videos. Users choose their own sharing platform |
| **Mesh generation / 3D printing export** | Converting point clouds to manifold meshes is a deep rabbit hole (marching cubes, Poisson reconstruction, mesh cleanup). Entirely different output domain | Stay in point cloud / particle territory. If users need meshes, they can export point clouds to Blender/MeshLab |
| **Multi-user collaboration** | Networking, conflict resolution, presence indicators. Massive complexity for a desktop creative tool | Single-user desktop application. Artists work solo with their data |

## Feature Dependencies

```
Image Ingestion -----> Color Extraction -----> Point Cloud Generation -----> Real-time Viewport
                  |                        |
                  +--> Edge Detection -----+
                  |                        |
                  +--> Depth Estimation ---+
                  |
                  +--> Semantic Extraction (CLIP/BLIP) ---> Discovery Mode
                                                       |
                                      Claude API ------+

Point Cloud Generation ---> Particle System ---> Live Parameter Animation
                       |
                       +--> Feature-to-Visual Mapping Editor

Parameter Controls ---> Preset System ---> Preset Interpolation
                   |
                   +--> Undo/Redo

Save/Load Projects (depends on everything being serializable)

Export Images (depends on Real-time Viewport)

Multi-Photo Pattern Emergence (depends on batch Image Ingestion + all extraction features)
```

**Critical path:** Image Ingestion -> Feature Extraction -> Point Cloud Generation -> Real-time Viewport. Everything else builds on this spine.

## MVP Definition

The MVP must prove the core thesis: photos become data, data becomes explorable 3D sculpture.

**Prioritize (MVP):**

1. Single-image ingestion with color + edge extraction (table stakes, proves the pipeline)
2. Point cloud generation from extracted features (the core transformation)
3. Real-time 3D viewport with orbit/zoom/pan (the experience)
4. Basic parameter controls (point size, color mapping, density) (the creative control)
5. Save/load project state (minimum viable persistence)
6. Export screenshot (minimum viable output)

**Phase 2 (Core Experience):**

7. Batch image ingestion (unlock the "thousands of photos" use case)
8. Depth estimation via monocular model (richer geometry)
9. Particle system with noise-driven motion (sculptures that live)
10. Preset save/load (creative workflow acceleration)
11. Undo/redo (creative safety net)

**Phase 3 (Differentiators):**

12. Semantic feature extraction (CLIP/BLIP local models)
13. Feature-to-visual mapping editor (the rewiring interface)
14. Discovery mode (AI-guided composition proposals)
15. Claude API integration (semantic annotation + creative direction)
16. Multi-photo pattern emergence (collection-level analysis)
17. Preset interpolation + live parameter animation (temporal dimension)

**Defer indefinitely:** Node editor, video input, camera feed, cloud rendering, plugin system, mesh export.

## Feature Prioritization Matrix

| Feature | User Value | Technical Risk | Dependency Weight | Priority |
|---------|-----------|---------------|-------------------|----------|
| Image ingestion | Critical | Low | Blocks everything | P0 |
| Color extraction | High | Low | Feeds point cloud | P0 |
| Edge/geometry detection | High | Medium | Feeds point cloud | P0 |
| Point cloud generation | Critical | Medium | Core transform | P0 |
| Real-time 3D viewport | Critical | High | Core experience | P0 |
| Parameter controls | Critical | Medium | Core interaction | P0 |
| Save/load projects | High | Medium | None (builds on serialization) | P0 |
| Export images | High | Low | Depends on viewport | P1 |
| Batch ingestion | High | Medium | Extends ingestion | P1 |
| Depth estimation | High | High (AMD compat) | Enriches point cloud | P1 |
| Particle system | High | High | Depends on point cloud | P1 |
| Undo/redo | High | Medium | Depends on param controls | P1 |
| Preset system | Medium | Low | Depends on param controls | P1 |
| Semantic extraction | High | High (model loading) | Enables discovery mode | P2 |
| Feature-to-visual mapping | High | High | Depends on extraction + rendering | P2 |
| Discovery mode | Very High | Very High | Depends on semantic + mapping | P2 |
| Claude API integration | Medium | Medium | Depends on semantic extraction | P2 |
| Multi-photo patterns | High | High | Depends on batch + all extraction | P2 |
| Preset interpolation | Medium | Low | Depends on preset system | P2 |
| Parameter animation | Medium | Medium | Depends on param controls | P2 |

## Competitor Feature Analysis

### TouchDesigner (Derivative)

**What it does well:**
- Industry-standard for real-time generative visuals and installations
- Node-based programming allows unlimited flexibility
- Excellent point cloud support (SOP -> CHOP -> TOP pipeline)
- GPU-accelerated rendering with GLSL shader support
- Massive community with shared components (tox files)
- Real-time performance with millions of particles

**What it lacks for Apollo 7's use case:**
- No photo feature extraction pipeline built-in (you build it yourself with nodes)
- Requires programming/node-wiring knowledge -- not a "drop photos, get sculpture" tool
- No semantic understanding of image content
- No discovery/suggestion mode
- CUDA-focused GPU compute (poor AMD support for compute shaders)
- Commercial license ($600+/year for commercial use)

**Apollo 7's advantage:** End-to-end photo-to-sculpture workflow without programming. Semantic understanding. Discovery mode.

### Processing / p5.js

**What it does well:**
- Excellent for learning and prototyping generative art
- Huge community, extensive tutorials and examples
- Simple API for 2D and basic 3D
- Cross-platform, free and open source

**What it lacks for Apollo 7's use case:**
- Performance ceiling for large point clouds (Java/JS runtime)
- No GPU compute for particle physics
- Requires writing code for every variation
- No built-in image analysis pipeline
- 3D support is basic compared to native GPU rendering

**Apollo 7's advantage:** GPU-accelerated rendering of massive point clouds. GUI-based workflow. Feature extraction pipeline.

### openFrameworks

**What it does well:**
- C++ performance for demanding real-time graphics
- Excellent addon ecosystem (ofxCV for computer vision, ofxGui for controls)
- Direct OpenGL access for custom rendering
- Cross-platform, free and open source
- Strong point cloud and mesh support (ofMesh)

**What it lacks for Apollo 7's use case:**
- Requires C++ programming for everything
- No pre-built photo-to-sculpture pipeline
- GUI construction is manual and basic (ofxGui is minimal)
- No semantic understanding or AI integration
- No discovery/suggestion mode

**Apollo 7's advantage:** No coding required. Integrated extraction-to-rendering pipeline. AI-assisted creative direction.

### Houdini (SideFX)

**What it does well:**
- Most powerful procedural 3D system in existence
- Excellent particle and fluid simulation
- VEX scripting for custom behavior
- Industry-standard for VFX

**What it lacks for Apollo 7's use case:**
- Extremely steep learning curve (months to years)
- Expensive ($2,000+/year for commercial, free Apprentice is watermarked)
- Overkill for the specific photo-to-sculpture workflow
- No built-in photo feature extraction
- Offline rendering focus (Karma/Mantra), not real-time exploration

**Apollo 7's advantage:** Purpose-built for one thing: transforming photos into data sculptures. Accessible to non-programmers.

### Anadol-Style Custom Pipelines

**What studios like RAS do:**
- Custom code (Python + C++ + GLSL) stitching together ML models, data processing, and rendering
- NVIDIA A100 clusters for training and inference
- Teams of 15+ (AI engineers, data scientists, designers)
- Proprietary diffusion models trained on curated datasets
- 42+ 50K projectors for installation output

**What Apollo 7 democratizes:**
- Single desktop machine instead of GPU cluster
- One person instead of a team
- GUI instead of custom code
- Open-source ML models instead of proprietary training
- Screen/monitor output instead of massive projections
- The aesthetic language of data sculpture, accessible to individual artists

## Sources

- [TouchDesigner Point Clouds](https://interactiveimmersive.io/blog/touchdesigner-3d/3d-point-clouds-in-touchdesigner/) -- TouchDesigner point cloud workflow
- [TouchDesigner Generative Art](https://interactiveimmersive.io/blog/touchdesigner-operators-tricks/ways-to-create-generative-art-with-touchdesigner/) -- TouchDesigner generative art approaches
- [Comparing Generative Art Tools](https://visualalchemyx.wordpress.com/2024/08/31/comparing-top-generative-art-tools-processing-openframeworks-p5-js-and-more/) -- Processing vs openFrameworks comparison
- [openFrameworks 3D](https://openframeworks.cc/documentation/3d/) -- openFrameworks 3D capabilities
- [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) -- Monocular depth estimation model
- [DepthFM](https://github.com/CompVis/depth-fm) -- Fast monocular depth estimation
- [Refik Anadol - NVIDIA AI Art](https://www.nvidia.com/en-us/research/ai-art-gallery/artists/refik-anadol/) -- Anadol's technical approach
- [Refik Anadol - Data Sculptures](https://wepresent.wetransfer.com/stories/refik-anadol-on-quantum-memories-and-data-sculptures) -- Anadol's workflow description
- [WIPO - Anadol Process](https://www.wipo.int/en/web/wipo-magazine/articles/painting-with-data-how-media-artist-refik-anadol-creates-art-using-generative-ai-67301) -- Anadol studio composition and process
- [AI Geometry Feature Extraction Survey](https://link.springer.com/article/10.1007/s10462-024-11051-3) -- Feature extraction in artistic images
- [Point Cloud Rendering Techniques](https://medium.com/realities-io/point-cloud-rendering-7bd83c6220c8) -- GPU point cloud rendering approaches
- [Dreamsheets - Prompting for Discovery](https://dl.acm.org/doi/10.1145/3613904.3642858) -- Discovery mode UX research
- [Variable.io - Generative and Data Art](https://variable.io/generative-and-data-art/) -- Data-driven art practice overview
