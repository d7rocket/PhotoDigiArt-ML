# Phase 5: Visual Quality - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Gallery-quality rendering with luminous particle aesthetics, white viewport background, smooth parameter crossfades, GPU buffer sharing for 1M+ particle performance, and CLAHE-enhanced depth maps that produce smooth continuous 3D sculptures instead of flat layered planes. UI theming is Phase 6 scope.

</domain>

<decisions>
## Implementation Decisions

### Luminous Particle Look
- Subtle warmth glow at defaults: clusters brighten where particles overlap, individual particles remain distinct at edges. Gallery-like, refined -- distant city lights aesthetic
- Overlapping particles saturate and brighten their color (dense red -> vivid saturated red, NOT wash to white). Colors stay rich in dense regions
- Soft Gaussian falloff at particle edges -- keep existing PointsGaussianBlobMaterial shape, no change needed
- If alpha + bloom + Gaussian blob approximation doesn't achieve luminous cluster look, write custom WGSL fragment shader for true additive blending. Try approximation first, escalate to custom shader if needed

### White Background
- Warm off-white background (~#F8F6F3 range) -- reads as white but gentler on eyes, like high-quality art paper
- White only, no dark/light toggle. All rendering and bloom tuning optimized for one background
- Bloom creates subtle colored halos around particle clusters (not white glow which would be invisible on white bg). Warm color spread from particle colors, like light diffusing through fog
- GUI panels stay dark themed (Phase 6 handles UI theming) -- dark panels frame white viewport like a picture frame

### Parameter Crossfade
- All visual parameters crossfade smoothly: point size, opacity, bloom strength, flow intensity, breathing rate, home strength, etc.
- Only discrete params snap instantly (solver_iterations -- already decided in Phase 4)
- Smooth chase behavior: value follows slider with ease-out lag (~0.3-0.5s behind). Feels like iOS animations. Settles to final value on release
- Unified crossfade system: one engine handles both individual slider changes AND A/B preset CrossfadeWidget transitions. Consistent feel everywhere
- Ease-out curve: fast initial response, smooth deceleration to target

### Depth Map Richness
- Photo-derived color palette: depth values map to colors from the source photo itself. Every sculpture's palette is unique to its source image. Data-driven
- Per-pixel color sampling: each particle gets color from exact pixel location in source photo. Maximum fidelity -- sculpture IS the photo in 3D
- Full contrast CLAHE on depth map: maximize local contrast so subtle depth differences become visible. Fixes the "flat layers" problem where depth splits into 2-3 pancake planes instead of smooth continuous volume
- CLAHE applied to depth map only, not color extraction
- Vivid saturation boost: increase color saturation 20-40% beyond source photo levels, applied uniformly across all depth levels. Sculptures should feel more vibrant than original photo -- art, not reproduction
- Color mapping baked at extraction time (not dynamic render-time). Changing mapping requires re-extraction but that's fast

### Claude's Discretion
- Exact alpha value and bloom parameters for luminous cluster approximation
- Whether custom WGSL shader is needed (try approximation first)
- CLAHE parameters (clip limit, tile grid size) for optimal depth contrast
- Exact warm off-white hex value in the #F8F6F3 range
- GPU buffer sharing implementation strategy between compute and render
- Crossfade engine internals (timer mechanism, interpolation math)
- Saturation boost exact percentage within 20-40% range

</decisions>

<specifics>
## Specific Ideas

- Gallery white aesthetic: like high-quality art paper or canvas, not sterile hospital white
- Bloom on white: colored halos, not white glow. Light diffusing through fog reference
- Smooth chase on sliders: iOS-like polish, value chases the slider with ease-out deceleration
- Depth fix priority: the current "flat layers" effect (foreground on one wall, main feature on another wall) is a key problem. CLAHE full contrast stretch is the fix
- Saturation makes sculptures more vibrant than source photo -- the transformation enhances, not just preserves
- Per-pixel fidelity: the sculpture IS the photo in 3D

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PointsGaussianBlobMaterial`: Already provides soft round particles with Gaussian falloff -- no shape change needed
- `BloomController` (postfx/bloom.py): Wraps pygfx PhysicalBasedBloomPass, has strength/enable control -- needs retuning for white background
- `CrossfadeWidget` (widgets/crossfade.py): A/B preset interpolation via `lerp_presets` -- feed into unified crossfade engine
- `DepthExtractor` (extraction/depth.py): Depth Anything V2 ONNX, basic min-max normalization -- add CLAHE before normalization
- `ColorExtractor` (extraction/color.py): Palette extraction -- can supply photo-derived colors for depth mapping

### Established Patterns
- Post-fx passes added via `renderer.effect_passes` list -- bloom already uses this
- Material updates via `update_point_material()` -- iterates all point objects, updates geometry buffers
- Sim engine uses `renderer.device` for wgpu access -- same device available for buffer sharing
- Settings constants in `config/settings.py` -- BG_COLOR_TOP/BOTTOM need updating to white

### Integration Points
- `_update_points_from_sim()` in viewport_widget.py (line 489): Current CPU readback bottleneck -- replace with GPU buffer sharing
- `BG_COLOR_TOP`/`BG_COLOR_BOTTOM` in settings.py: Change to warm off-white
- `_BLEND_ALPHA = 0.7` in viewport_widget.py: Tune for luminous cluster effect
- `BLOOM_STRENGTH_DEFAULT = 0.04`: Likely needs increase for visible colored halos on white
- `DepthExtractor.extract()`: Insert CLAHE step before min-max normalization

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-visual-quality*
*Context gathered: 2026-03-15*
