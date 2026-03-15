---
phase: 03-discovery-and-intelligence
verified: 2026-03-15T10:30:00Z
status: gaps_found
score: 9/11 must-haves verified
re_verification: false
gaps:
  - truth: "Collection clusters act as force attractors in the simulation"
    status: failed
    reason: "main_window._on_batch_extraction_complete reads embedding from result.data.get('embedding') but ClipExtractor stores the 512-dim vector in result.arrays['embedding']. Collection analysis is never triggered because embeddings dict always stays empty (< 2 entries), so the entire COLL-01/02/03 flow silently degrades at runtime."
    artifacts:
      - path: "apollo7/gui/main_window.py"
        issue: "Line 695: result.data.get('embedding') should be result.arrays.get('embedding')"
      - path: "apollo7/extraction/clip.py"
        issue: "Line 265: embedding correctly stored in arrays={} but main_window reads data={}"
    missing:
      - "Fix line 695 in main_window.py: change result.data.get('embedding') to result.arrays.get('embedding')"

  - truth: "Animation bindings can be configured and applied via the mapping editor"
    status: failed
    reason: "main_window._on_animation_tick accesses self._animator.bindings (line 1124) but ParameterAnimator exposes no public 'bindings' attribute — only private _bindings and the is_active property. This AttributeError fires every animation tick when a simulation is running."
    artifacts:
      - path: "apollo7/gui/main_window.py"
        issue: "Line 1124: self._animator.bindings does not exist on ParameterAnimator"
      - path: "apollo7/animation/animator.py"
        issue: "ParameterAnimator only has _bindings (private) and is_active property; no public bindings"
    missing:
      - "Fix line 1124 in main_window.py: change self._animator.bindings to self._animator.is_active"
---

# Phase 3: Discovery and Intelligence Verification Report

**Phase Goal:** Discovery and Intelligence — Semantic extraction (CLIP/BLIP), feature-to-visual mapping editor, discovery mode (system-proposed compositions), and optional Claude API integration.
**Verified:** 2026-03-15T10:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline extracts semantic tags (mood + objects) with confidence scores | VERIFIED | ClipExtractor.extract() returns ExtractionResult with mood_tags/object_tags lists of (label, conf) tuples; ClipExtractor registered in ExtractionPipeline at main_window.py line 214 |
| 2 | Semantic tags appear as colored pills in the feature viewer | VERIFIED | _TagPillWidget and _FlowLayout defined in feature_viewer.py; _build_semantic_section() renders them at lines 581-629 |
| 3 | 512-dim CLIP embedding produced for each photo | VERIFIED | ClipExtractor stores embedding in ExtractionResult.arrays["embedding"] — substantive implementation confirmed |
| 4 | LFO/noise/envelope generators produce correct time-varying float values | VERIFIED | lfo.py implements all four LFO waveforms, NoiseGenerator (hash+smoothstep), Envelope (attack/sustain/release) |
| 5 | Parameter animator applies LFO outputs to simulation params | VERIFIED (with gap) | animator.py ParameterAnimator.tick() calls with_update(); but main_window.py accesses non-existent .bindings attribute at line 1124 — AttributeError at runtime |
| 6 | User can select two presets and crossfade between them | VERIFIED | CrossfadeWidget in crossfade.py; wired into PresetPanel via crossfade_changed signal at preset_panel.py line 139 |
| 7 | User can drag wires from feature outputs to parameter inputs in node editor | VERIFIED | PatchBayEditor in node_editor.py with QGraphicsScene, Port/NodeItem/Wire hierarchy, Bezier wires; MappingConnection created on drag |
| 8 | Mapping engine evaluates connections and produces parameter updates | VERIFIED | MappingEngine.evaluate() returns dict of param updates; wired in main_window._evaluate_mapping_graph() |
| 9 | Pipeline clusters photo embeddings and identifies collection patterns | FAILED | CollectionAnalyzer exists and is substantive; _CollectionAnalysisWorker in main_window.py exists — but _on_batch_extraction_complete looks up embeddings via result.data.get("embedding") while ClipExtractor stores them in result.arrays["embedding"]. Embeddings dict stays empty; analysis is never triggered. |
| 10 | Discovery mode proposes random parameter combinations | VERIFIED | RandomWalk.propose(), DimensionalMapper, ProposalHistory all implemented; DiscoveryPanel UI wired to main_window signals |
| 11 | All core functionality works fully offline; Claude API is additive only | VERIFIED | EnrichmentService defaults to disabled (ENRICHMENT_ENABLED=False); all methods return None/empty when key missing; DISC-04 satisfied |

**Score: 9/11 truths verified** (2 gaps due to runtime wiring bugs)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apollo7/extraction/clip.py` | ClipExtractor with lazy ONNX loading | VERIFIED | 268 lines; dual ONNX sessions, zero-shot classification, 512-dim embedding |
| `apollo7/extraction/clip_tokenizer.py` | CLIP BPE tokenizer, pure numpy | VERIFIED | 207 lines; gzip vocab load, BPE encoding, tokenize_batch() |
| `apollo7/animation/lfo.py` | LFO, NoiseGenerator, Envelope | VERIFIED | All three classes implemented with evaluate(time)->float |
| `apollo7/animation/animator.py` | ParameterAnimator routing to sim params | VERIFIED | tick() uses with_update(); public interface has is_active, add_binding, remove_binding |
| `apollo7/mapping/connections.py` | MappingConnection, MappingGraph with JSON serialization | VERIFIED | Full to_dict/from_dict round-trip; get_connections() method |
| `apollo7/mapping/engine.py` | MappingEngine evaluation with additive blending | VERIFIED | evaluate() returns dict; FEATURE_SOURCES and TARGET_PARAMS registries |
| `apollo7/gui/widgets/node_editor.py` | PatchBayEditor QGraphicsScene patch bay | VERIFIED | Bezier wires, port hover, strength editor, signal-based change notification |
| `apollo7/gui/widgets/crossfade.py` | CrossfadeWidget with A/B preset + slider | VERIFIED | Vertical layout, crossfade_changed signal, lerp_presets call |
| `apollo7/collection/analyzer.py` | CollectionAnalyzer with DBSCAN + UMAP 3D | VERIFIED | CollectionResult dataclass; _cluster() with DBSCAN cosine metric; _project_3d() with UMAP |
| `apollo7/collection/embedding_cloud.py` | EmbeddingCloudManager, create_embedding_cloud | VERIFIED | CLUSTER_PALETTE defined; pygfx Points creation; update/toggle/isolate lifecycle |
| `apollo7/discovery/random_walk.py` | RandomWalk engine | VERIFIED | propose() with constraints dict; gaussian perturbation; SimulationParams.with_update() |
| `apollo7/discovery/dimensional.py` | DimensionalMapper with DIMENSION_MAPPINGS | VERIFIED | 4 dimensions (energy/density/flow/structure); exponential smoothing alpha=0.3; 40% window |
| `apollo7/discovery/history.py` | ProposalHistory ring buffer | VERIFIED | Ring buffer max 50; Proposal dataclass with thumbnail support |
| `apollo7/gui/panels/discovery_panel.py` | DiscoveryPanel with 4 dimensional sliders | VERIFIED | Substantive UI; signals: proposal_requested, proposal_applied, dimension_changed |
| `apollo7/gui/widgets/history_strip.py` | HistoryStripWidget horizontal scrollable | VERIFIED | Card strip with active highlighting |
| `apollo7/api/enrichment.py` | EnrichmentService with offline fallback | VERIFIED | Lazy Anthropic client; returns None when key missing/disabled; EnrichmentWorker QRunnable |
| `apollo7/gui/main_window.py` | Full Phase 3 signal wiring hub | PARTIAL | DiscoveryPanel, PatchBayEditor, EnrichmentService, MappingEngine all properly wired; TWO runtime bugs (embedding lookup wrong key, animator.bindings missing) |
| `tests/test_clip_extractor.py` | 5 tests with mocked ONNX sessions | VERIFIED | File exists |
| `tests/test_animation.py` | 12 LFO/noise/envelope/animator tests | VERIFIED | File exists |
| `tests/test_preset_interpolation.py` | 7 lerp tests | VERIFIED | File exists |
| `tests/test_mapping.py` | 12 connection model + engine tests | VERIFIED | File exists |
| `tests/test_collection_analyzer.py` | 8 clustering/projection tests | VERIFIED | File exists |
| `tests/test_discovery.py` | 13 walk/mapping/history tests | VERIFIED | File exists |
| `tests/test_enrichment.py` | 9 enrichment + offline fallback tests | VERIFIED | File exists |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `clip.py` | `pipeline.py` | ClipExtractor in ExtractionPipeline extractors list | WIRED | main_window.py line 214: `ExtractionPipeline([ColorExtractor(), EdgeExtractor(), DepthExtractor(), ClipExtractor()])` |
| `clip.py` | `feature_viewer.py` | ExtractionResult semantic key -> update_features -> _build_semantic_section | WIRED | feature_viewer.py line 373-391 reads `features.get("semantic")` and passes to _build_semantic_section |
| `animator.py` | `simulation/parameters.py` | ParameterAnimator.tick() calls SimulationParams.with_update() | WIRED | animator.py line 136: `return params.with_update(**updates)` |
| `main_window.py` | `animator.py` | _on_animation_tick accesses self._animator | BROKEN | Line 1124 accesses `self._animator.bindings` — no such attribute; should be `self._animator.is_active` |
| `crossfade.py` | `presets.py` | CrossfadeWidget calls lerp_presets via PresetManager | WIRED | crossfade.py imports `lerp_presets` from apollo7.project.presets; called in _on_slider_moved |
| `node_editor.py` | `connections.py` | Wire drag creates MappingConnection, PatchBayEditor reflects MappingGraph | WIRED | node_editor.py line 43-44 imports MappingConnection, MappingGraph |
| `engine.py` | `simulation/parameters.py` | MappingEngine.evaluate() output fed to SimulationParams.with_update() | WIRED | main_window.py line 1068: `updates = self._mapping_engine.evaluate(...)`; fed to sim engine |
| `collection/analyzer.py` | `clip.py` | CollectionAnalyzer consumes 512-dim embeddings from ClipExtractor | BROKEN | main_window._on_batch_extraction_complete line 695: reads `result.data.get("embedding")` but ClipExtractor stores in `result.arrays["embedding"]` — embeddings always empty, analysis never runs |
| `embedding_cloud.py` | `viewport_widget.py` | pygfx Points added to viewport scene | WIRED | viewport_widget.py line 509: update_embedding_cloud() accepts CollectionResult |
| `collection/analyzer.py` | `simulation/engine.py` | Cluster centroids as force attractor positions | WIRED (blocked) | main_window.py line 721-725 calls set_attractors(); blocked because collection analysis never triggers due to embedding lookup bug |
| `main_window.py` | `discovery_panel.py` | DiscoveryPanel docked in sidebar, signals connected | WIRED | Lines 265, 273, 464-466: panel created, added to layout, signals connected |
| `main_window.py` | `node_editor.py` | PatchBayEditor shown as overlay via Ctrl+M | WIRED | Lines 293-294, 469-471: editor created, mapping_changed signal connected |
| `extraction_worker.py` | `collection/analyzer.py` | batch_complete signal triggers CollectionAnalyzer | PARTIAL | batch_complete wired (lines 595, 630); but embedding lookup bug prevents it from functioning |
| `enrichment.py` | `feature_viewer.py` | Enriched descriptions displayed in feature viewer | WIRED | feature_viewer.py: enrichment_requested signal connected; set_enrichment slot exists |
| `enrichment.py` | `mapping/connections.py` | Suggested mappings returned as MappingConnection candidates | WIRED | enrichment.py returns mapping_suggestions in EnrichmentResult; MappingConnection imported |
| `save_load.py` | mapping+discovery | mapping_graph and discovery_dimensions persisted in project | WIRED | save_load.py lines 43-44, 111-112: mapping_graph and discovery_dimensions in ProjectState |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EXTRACT-04 | 03-01, 03-07 | Pipeline extracts semantic features via local CLIP | SATISFIED | ClipExtractor implements zero-shot classification; registered in pipeline |
| COLL-01 | 03-04, 03-07 | Pipeline identifies patterns across collections | PARTIAL | CollectionAnalyzer and DBSCAN/UMAP implemented; wiring bug prevents runtime execution |
| COLL-02 | 03-04, 03-07 | User can visualize collection-level patterns | PARTIAL | EmbeddingCloudManager and viewport methods exist; blocked by COLL-01 bug |
| COLL-03 | 03-04, 03-07 | Collection patterns feed into sculpture generation | PARTIAL | set_attractors() implemented in sim engine; blocked by COLL-01 bug |
| RENDER-07 | 03-02, 03-07 | Parameter animation via LFOs, noise, envelopes | PARTIAL | LFO/NoiseGenerator/Envelope and ParameterAnimator all implemented; blocked by .bindings AttributeError |
| CTRL-02 | 03-03, 03-07 | Feature-to-visual mapping editor | SATISFIED | PatchBayEditor with Bezier wires; MappingEngine evaluation wired to simulation |
| CTRL-07 | 03-02, 03-07 | Preset interpolation — smoothly blend between presets | SATISFIED | lerp_presets(), CrossfadeWidget, preset_panel wiring all verified |
| DISC-01 | 03-05, 03-07 | Local discovery mode — randomized constrained exploration | SATISFIED | RandomWalk, DimensionalMapper, DiscoveryPanel, HistoryStrip all wired |
| DISC-02 | 03-06, 03-07 | Optional Claude API for semantic annotation | SATISFIED | EnrichmentService with offline fallback; feature viewer toggle |
| DISC-03 | 03-06, 03-07 | Optional Claude API creative direction | SATISFIED | suggest_mappings() returning MappingConnection candidates |
| DISC-04 | 03-06, 03-07 | All core functionality works fully offline | SATISFIED | ENRICHMENT_ENABLED defaults False; all offline paths verified |

**Requirements with implementation gaps (code exists but runtime broken):** COLL-01, COLL-02, COLL-03, RENDER-07

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apollo7/gui/main_window.py` | 695 | `result.data.get("embedding")` — wrong dict key (embedding is in result.arrays) | BLOCKER | Collection analysis never receives embeddings; COLL-01/02/03 silently fail at runtime |
| `apollo7/gui/main_window.py` | 1124 | `self._animator.bindings` — attribute does not exist on ParameterAnimator | BLOCKER | AttributeError thrown every animation tick when simulation runs; RENDER-07 broken |
| `apollo7/extraction/clip.py` | 168 | "placeholder" in docstring parameter description | INFO | False positive — it's a docstring about a format string placeholder, not a stub |

---

## Human Verification Required

The following items pass automated checks but require human confirmation:

### 1. Node Editor Drag-to-Connect Interaction

**Test:** Load a photo with semantic extraction results, open the mapping editor (Ctrl+M), attempt to drag from a feature port (left column) to a parameter port (right column).
**Expected:** A Bezier wire appears; right-click on it shows a strength spinner; the wire registers in MappingGraph.
**Why human:** Qt drag interaction in QGraphicsScene cannot be verified programmatically without running the application.

### 2. Discovery Mode Proposal Visual Flow

**Test:** Load multiple photos, run extraction, open discovery panel, toggle ON, click Propose.
**Expected:** New SimulationParams applied to viewport; a thumbnail card appears in the history strip.
**Why human:** Thumbnail generation from viewport requires the full Qt application stack running.

### 3. Embedding Cloud Visual Display (blocked — fix bug first)

**Test:** After fixing the embedding lookup bug, load 3+ photos with CLIP models present, run extraction, verify embedding cloud appears in viewport (Ctrl+E toggle).
**Expected:** Colored points appear in the 3D viewport, color-coded by cluster assignment.
**Why human:** Requires CLIP ONNX models present and viewport rendering stack active.

---

## Gaps Summary

Two runtime wiring bugs block two requirement groups despite complete underlying implementations:

**Bug 1 — Embedding lookup wrong dict key (blocks COLL-01, COLL-02, COLL-03):**
`ClipExtractor.extract()` stores the 512-dim embedding vector in `ExtractionResult.arrays["embedding"]`. However, `main_window._on_batch_extraction_complete()` reads it from `result.data.get("embedding")`. Since `result.data` only contains `mood_tags` and `object_tags`, the embedding is never found. The `embeddings` dict stays empty after iterating all photos, and collection analysis is skipped with the log message "Not enough embeddings for collection analysis (0)." The entire COLL-01/02/03 feature path (DBSCAN clustering, UMAP 3D cloud, force attractors) silently does nothing at runtime. Fix: change line 695 to `result.arrays.get("embedding")`.

**Bug 2 — ParameterAnimator.bindings does not exist (blocks RENDER-07):**
`ParameterAnimator` exposes `is_active` (a `@property`) and `_bindings` (private list) but no public `bindings` attribute. The animation tick handler in `main_window._on_animation_tick()` guards with `if not self._animator.bindings:` which raises `AttributeError` on every call. This means the animation engine never applies LFO/noise/envelope values to simulation parameters. Fix: change line 1124 to `if not self._animator.is_active:`.

Both bugs are single-line fixes in `main_window.py`. The underlying implementations (CollectionAnalyzer, ParameterAnimator) are correct and complete.

---

_Verified: 2026-03-15T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
