# Phase 3: Discovery and Intelligence - Research

**Researched:** 2026-03-14
**Domain:** Semantic extraction (CLIP/BLIP ONNX), collection analysis, discovery UX, node editor, preset interpolation, Claude API integration
**Confidence:** MEDIUM

## Summary

Phase 3 transforms Apollo 7 from a visual tool into a creative collaborator by adding semantic understanding (CLIP/BLIP), collection-level pattern analysis, a discovery mode with abstract sliders, a node-wire feature-to-visual mapping editor, preset interpolation, and optional Claude API enrichment. The phase spans six distinct technical domains that must integrate with the existing extraction pipeline, simulation engine, and PySide6 GUI.

The primary technical challenge is CLIP/BLIP ONNX inference without PyTorch dependencies, matching the existing DepthExtractor pattern. The project already uses onnxruntime-directml for depth estimation, so the same lazy-load + DirectML/CPU fallback pattern applies directly. For collection analysis, scikit-learn (already installed at 1.8.0) provides DBSCAN clustering, and umap-learn needs to be added for 3D embedding projection. The node editor should be built as a custom QGraphicsScene widget rather than pulling in a third-party library, keeping the dependency footprint small and the look/feel consistent with the DAW-style aesthetic.

**Primary recommendation:** Build CLIP and BLIP as separate BaseExtractor subclasses using raw ONNX models in models/, use scikit-learn DBSCAN for clustering and umap-learn for 3D projection, build the node editor as a custom QGraphicsScene, and implement preset interpolation as simple dict-level lerp on the existing PresetManager.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Rich multi-layer extraction: scene-level mood (serene, chaotic, melancholic), object detection (tree, car, person), and dense embedding vector for similarity
- Bundled ONNX models shipped in models/ directory (like Depth Anything V2) -- works offline immediately
- Automatic in pipeline: runs after depth extraction as part of the standard extraction flow, not a separate manual step
- Tags displayed as colored pills/badges with confidence scores (e.g., "serene 0.87", "forest 0.72") in a new collapsible section in the feature viewer
- 3D embedding cloud rendered IN the viewport -- each photo is a point in embedding space alongside the sculpture
- Collection patterns feed into sculpture via both spatial seeding AND continuous force attractors
- Click-to-isolate: clicking a cluster isolates those photos' particles (others dim/hide) for focused sculpting of thematic subsets
- Outlier photos treated equally -- no special visual treatment, no judgment about which photos are "normal"
- Random walk with constraints: randomize parameters within sensible ranges derived from photo features
- Feedback via 3-4 abstract dimensional sliders: Energy (calm-chaotic), Density (sparse-dense), Flow (rigid-fluid), Structure (organic-geometric)
- Visual history strip: horizontal strip of thumbnail snapshots showing recent proposals
- Node-wire patch bay: feature outputs on the left, parameter inputs on the right, drag wires to connect
- Dedicated full overlay panel: opens as a large overlay/modal, toggled via button or shortcut
- Each connection has a strength/scale control
- Crossfade slider: select two presets, drag a slider from A to B -- all parameters lerp smoothly in real-time
- Enrichment badge: subtle "Enhance with AI" toggle in settings
- When enabled: semantic tags get richer descriptions, node editor suggests creative mappings
- When disabled: everything still works, just less descriptive
- Offline-first guarantee: no core feature depends on API availability

### Claude's Discretion
- CLIP vs BLIP model selection and specific ONNX variants
- Clustering algorithm for collection analysis (DBSCAN, k-means, etc.)
- t-SNE vs UMAP for embedding projection to 3D
- Node editor visual design and interaction patterns
- Parameter animation implementation (LFOs, noise functions, envelopes for RENDER-07)
- Discovery mode constraint derivation logic (how features map to parameter ranges)
- How the enrichment badge communicates with Claude API (SDK, HTTP, etc.)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXTRACT-04 | Pipeline extracts semantic features (objects, scenes, mood) via local CLIP/BLIP models | ClipExtractor + BlipExtractor as BaseExtractor subclasses, ONNX models in models/, zero-shot classification with mood/object label sets |
| COLL-01 | Pipeline identifies patterns across photo collections (clustering, trends, outliers) | DBSCAN on CLIP embeddings via scikit-learn, automatic cluster count |
| COLL-02 | User can visualize collection-level patterns (e.g., t-SNE/UMAP embedding space) | UMAP n_components=3 projection rendered as pygfx Points in viewport |
| COLL-03 | Collection patterns feed into sculpture generation as compositional signals | Cluster centroids as force attractors in simulation, spatial seeding from UMAP positions |
| RENDER-07 | Parameter animation via LFOs, noise functions, and envelopes mapped to any visual parameter | LFO/noise/envelope classes producing float values over time, routed through mapping editor |
| CTRL-02 | Feature-to-visual mapping editor -- user can route extracted features to visual parameters | Custom QGraphicsScene node-wire editor in full overlay panel |
| CTRL-07 | Preset interpolation -- smoothly blend between saved presets | Dict-level lerp between two preset dicts, applied to SimulationParams + PostFX |
| DISC-01 | Local discovery mode -- randomized but constrained parameter exploration with feedback loop | Random walk within feature-derived ranges, dimensional sliders steer constraints |
| DISC-02 | Optional Claude API integration for semantic photo annotation | anthropic SDK messages.create() with image content, guarded by settings toggle |
| DISC-03 | Optional Claude API creative direction (suggest feature-to-visual mappings) | Structured JSON response from Claude suggesting mapping connections |
| DISC-04 | All core functionality works fully offline -- Claude API is additive enrichment only | API calls wrapped in try/except with graceful fallback, feature gating in settings |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| onnxruntime-directml | 1.24.3 (installed) | CLIP/BLIP ONNX inference with AMD GPU | Already used for depth extraction, DirectML for RDNA GPUs |
| scikit-learn | 1.8.0 (installed) | DBSCAN clustering on embeddings | Already installed, mature clustering API |
| umap-learn | 0.5.x | 3D embedding projection | Best-in-class for preserving global+local structure, faster than t-SNE at scale |
| anthropic | 0.84.0 (installed) | Claude API for enrichment | Already installed, official SDK |
| numpy | 2.1+ (installed) | CLIP preprocessing, embedding math | Already core dependency |
| scipy | 1.17.0 (installed) | Cosine distance for similarity | Already installed |
| Pillow | 11+ (installed) | Image preprocessing for CLIP | Already core dependency |
| PySide6 | 6.8+ (installed) | Node editor UI (QGraphicsScene) | Already core GUI framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| opencv-python-headless | 4.10+ (installed) | Image resize for CLIP preprocessing | Already used for depth/edge preprocessing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| UMAP | t-SNE | t-SNE slower, worse global structure preservation, no transform for new points |
| DBSCAN | k-means | k-means requires specifying k upfront; DBSCAN finds natural cluster count |
| Custom node editor | NodeGraphQt-PySide6 | External dep adds maintenance risk; custom QGraphicsScene gives exact DAW aesthetic control |
| Raw ONNX CLIP | onnx_clip library | onnx_clip is archived (Feb 2026), bundles ViT-B/32 only; raw ONNX gives model flexibility |

**Installation:**
```bash
pip install umap-learn
```

Note: All other dependencies are already installed. The only new dependency is umap-learn.

## Architecture Patterns

### Recommended Project Structure
```
apollo7/
  extraction/
    clip.py              # ClipExtractor (BaseExtractor subclass)
    blip.py              # BlipExtractor (BaseExtractor subclass)
  collection/
    __init__.py
    analyzer.py          # CollectionAnalyzer (clustering + UMAP)
    embedding_cloud.py   # 3D embedding cloud renderer
  discovery/
    __init__.py
    random_walk.py       # Discovery mode random walk engine
    dimensional.py       # Abstract dimension sliders (Energy, Density, Flow, Structure)
    history.py           # Visual history strip state management
  mapping/
    __init__.py
    engine.py            # Feature-to-visual mapping evaluation
    connections.py       # Connection data model (source, target, strength)
  animation/
    __init__.py
    lfo.py               # LFO, noise, envelope generators
    animator.py          # Parameter animator (applies LFO outputs to params)
  gui/
    panels/
      semantic_viewer.py # Semantic tags section (pills/badges)
      discovery_panel.py # Discovery mode panel with dimensional sliders
      history_strip.py   # Visual history strip widget
    widgets/
      node_editor.py     # QGraphicsScene-based patch bay editor
      crossfade.py       # Preset crossfade slider widget
  api/
    __init__.py
    enrichment.py        # Claude API enrichment service
models/
  clip_vit_b32_visual.onnx   # CLIP vision encoder (~340MB)
  clip_vit_b32_text.onnx     # CLIP text encoder (~65MB)
```

### Pattern 1: CLIP Extractor (follows DepthExtractor pattern exactly)
**What:** Lazy-loaded ONNX session for CLIP image embeddings + zero-shot classification
**When to use:** Every image extraction pipeline run
**Example:**
```python
# Source: existing DepthExtractor pattern in apollo7/extraction/depth.py
class ClipExtractor(BaseExtractor):
    def __init__(self, model_path: str = "models/clip_vit_b32_visual.onnx"):
        self._model_path = model_path
        self._session = None  # Lazy-loaded
        # Predefined label sets for zero-shot classification
        self._mood_labels = ["serene", "chaotic", "melancholic", "joyful", "dramatic", "mysterious"]
        self._object_labels = ["tree", "car", "person", "building", "water", "sky", "animal", "flower"]

    @property
    def name(self) -> str:
        return "semantic"

    def _ensure_session(self) -> None:
        if self._session is not None:
            return
        import onnxruntime as ort
        available = ort.get_available_providers()
        providers = []
        if "DmlExecutionProvider" in available:
            providers.append("DmlExecutionProvider")
        providers.append("CPUExecutionProvider")
        self._session = ort.InferenceSession(self._model_path, providers=providers)

    def extract(self, image: np.ndarray) -> ExtractionResult:
        self._ensure_session()
        # Preprocess: resize to 224x224, ImageNet normalize, NCHW
        embedding = self._get_embedding(image)  # 512-dim vector
        mood_scores = self._classify(embedding, self._mood_labels)
        object_scores = self._classify(embedding, self._object_labels)
        return ExtractionResult(
            extractor_name=self.name,
            data={
                "mood_tags": mood_scores,      # [("serene", 0.87), ...]
                "object_tags": object_scores,  # [("forest", 0.72), ...]
            },
            arrays={
                "embedding": embedding,  # (512,) float32
            },
        )
```

### Pattern 2: Collection Analyzer
**What:** Clusters CLIP embeddings and projects to 3D via UMAP
**When to use:** After all photos in a collection are extracted
**Example:**
```python
import numpy as np
from sklearn.cluster import DBSCAN
import umap

class CollectionAnalyzer:
    def analyze(self, embeddings: dict[str, np.ndarray]) -> CollectionResult:
        paths = list(embeddings.keys())
        X = np.stack([embeddings[p] for p in paths])  # (N, 512)

        # Cluster in embedding space
        clustering = DBSCAN(eps=0.3, min_samples=2, metric="cosine").fit(X)
        labels = clustering.labels_

        # Project to 3D for visualization
        reducer = umap.UMAP(n_components=3, n_neighbors=min(15, len(X)-1), min_dist=0.1)
        positions_3d = reducer.fit_transform(X)  # (N, 3)

        return CollectionResult(
            paths=paths,
            labels=labels,
            positions_3d=positions_3d,
            cluster_centroids=self._compute_centroids(X, labels),
        )
```

### Pattern 3: Preset Interpolation (lerp between two preset dicts)
**What:** Smoothly blend all parameters between preset A and preset B
**When to use:** Crossfade slider dragged by user
**Example:**
```python
def lerp_presets(preset_a: dict, preset_b: dict, t: float) -> dict:
    """Lerp between two preset parameter dicts at position t in [0, 1]."""
    result = {}
    for section in ("sim_params", "postfx_params"):
        a_params = preset_a.get(section, {})
        b_params = preset_b.get(section, {})
        all_keys = set(a_params) | set(b_params)
        result[section] = {}
        for key in all_keys:
            va = a_params.get(key, 0.0)
            vb = b_params.get(key, 0.0)
            if isinstance(va, (list, tuple)):
                result[section][key] = [a + (b - a) * t for a, b in zip(va, vb)]
            elif isinstance(va, (int, float)):
                result[section][key] = va + (vb - va) * t
            else:
                result[section][key] = va if t < 0.5 else vb
    return result
```

### Pattern 4: Parameter Animation (LFO)
**What:** Low-frequency oscillator producing time-varying float values for any parameter
**When to use:** RENDER-07 parameter animation
**Example:**
```python
import math

class LFO:
    """Low-frequency oscillator for parameter animation."""
    def __init__(self, frequency: float = 1.0, amplitude: float = 1.0,
                 offset: float = 0.0, waveform: str = "sine"):
        self.frequency = frequency
        self.amplitude = amplitude
        self.offset = offset
        self.waveform = waveform

    def evaluate(self, time: float) -> float:
        phase = time * self.frequency * 2 * math.pi
        if self.waveform == "sine":
            raw = math.sin(phase)
        elif self.waveform == "triangle":
            raw = 2 * abs(2 * (time * self.frequency % 1) - 1) - 1
        elif self.waveform == "square":
            raw = 1.0 if math.sin(phase) >= 0 else -1.0
        elif self.waveform == "noise":
            # Deterministic noise from time seed
            raw = (hash(int(time * self.frequency * 1000)) % 2000 - 1000) / 1000
        else:
            raw = 0.0
        return self.offset + raw * self.amplitude
```

### Pattern 5: Node Editor (QGraphicsScene-based)
**What:** Custom patch bay with feature output ports on left, parameter input ports on right
**When to use:** CTRL-02 feature-to-visual mapping editor
**Example:**
```python
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsItem
from PySide6.QtCore import QPointF

class Port(QGraphicsItem):
    """A connection port (input or output) on a node."""
    RADIUS = 6
    def __init__(self, name: str, is_output: bool, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_output = is_output
        self.connections = []

class NodeItem(QGraphicsItem):
    """A node in the patch bay (feature source or parameter target)."""
    def __init__(self, label: str, ports: list[Port]):
        super().__init__()
        self.label = label
        self.ports = ports
        self.setFlag(QGraphicsItem.ItemIsMovable, False)  # Fixed position

class Wire(QGraphicsItem):
    """A connection wire between two ports with strength control."""
    def __init__(self, source_port: Port, target_port: Port, strength: float = 1.0):
        super().__init__()
        self.source = source_port
        self.target = target_port
        self.strength = strength

class PatchBayScene(QGraphicsScene):
    """The main scene for the node-wire editor."""
    def __init__(self):
        super().__init__()
        # Feature outputs on left column
        self._feature_nodes = []  # mood, objects, embedding, color, depth, edge
        # Parameter inputs on right column
        self._param_nodes = []    # speed, turbulence, noise_freq, gravity, etc.
```

### Anti-Patterns to Avoid
- **Loading CLIP at import time:** The ONNX session is expensive (~2s). Always lazy-load on first extract() call, matching DepthExtractor pattern.
- **Running UMAP on every photo add:** UMAP should run once after batch extraction is complete, not incrementally per photo.
- **Storing embeddings as lists in JSON:** 512-dim float32 vectors should stay as numpy arrays in memory and be serialized to .npy files if persisted, not as JSON arrays.
- **Blocking UI during CLIP inference:** CLIP inference takes 0.5-2s per image. Must run in QRunnable worker thread like existing extraction.
- **Hardcoding label sets:** Mood and object label sets should be configurable lists, not embedded in the extractor. Store as module-level constants that can be extended.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Clustering embeddings | Custom nearest-neighbor grouping | sklearn.cluster.DBSCAN | Handles noise points, no k required, cosine metric support |
| 3D dimensionality reduction | Custom PCA or random projection | umap-learn UMAP(n_components=3) | Preserves manifold structure, fast, deterministic with random_state |
| CLIP image preprocessing | Custom resize+normalize pipeline | cv2.resize + numpy (matching DepthExtractor) | ImageNet normalization is standard: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225] |
| Text tokenization for CLIP | Custom tokenizer | Bundled tokenizer vocab file (BPE) | CLIP's BPE tokenizer is non-trivial; use the vocab.json + merges from HuggingFace |
| Cosine similarity | Manual dot product / norm | scipy.spatial.distance.cosine or sklearn.metrics.pairwise.cosine_similarity | Numerically stable, vectorized |
| JSON-based API calls | Raw httpx/requests | anthropic SDK client.messages.create() | Handles auth, retries, streaming, rate limits |

**Key insight:** The two expensive custom pieces are the node editor UI (QGraphicsScene -- must be custom for DAW aesthetic) and the discovery mode random walk logic (domain-specific to Apollo 7's parameter space). Everything else has mature library support already installed.

## Common Pitfalls

### Pitfall 1: CLIP Text Encoder Needs Separate ONNX Model
**What goes wrong:** Attempting to use only the vision encoder for zero-shot classification. CLIP requires both vision AND text encoders -- the text encoder creates embeddings for label strings that are compared against the image embedding.
**Why it happens:** Depth Anything uses a single model file. CLIP needs two.
**How to avoid:** Bundle both clip_vit_b32_visual.onnx AND clip_vit_b32_text.onnx in models/. The text encoder also needs the BPE tokenizer vocabulary.
**Warning signs:** Zero-shot classification returns random scores or the extractor can only produce raw embeddings but not tag scores.

### Pitfall 2: UMAP With Very Small Collections
**What goes wrong:** UMAP crashes or produces degenerate results with fewer than ~5 data points.
**Why it happens:** UMAP's n_neighbors parameter defaults to 15. If you have fewer points than n_neighbors, it fails.
**How to avoid:** Set n_neighbors = min(15, n_samples - 1). For collections under 3 photos, skip UMAP and place points on a simple line or triangle.
**Warning signs:** ValueError from UMAP about n_neighbors being too large.

### Pitfall 3: DBSCAN eps Sensitivity
**What goes wrong:** All points assigned to noise (label=-1) or all points in one cluster.
**Why it happens:** CLIP embeddings are L2-normalized, so cosine distance is always in [0, 2]. The eps threshold must be tuned for this range.
**How to avoid:** Use metric="cosine" with eps in range [0.2, 0.5]. Start with 0.3. Consider computing a distance histogram first to auto-tune eps.
**Warning signs:** All cluster labels are -1, or there's only one cluster.

### Pitfall 4: Node Editor Wire Routing Overlap
**What goes wrong:** Wires cross and overlap making the patch bay unreadable.
**Why it happens:** Naive straight-line wires between ports on left and right columns.
**How to avoid:** Use cubic Bezier curves (QPainterPath.cubicTo) with horizontal control points offset by ~1/3 of the distance. Color-code wires by feature type.
**Warning signs:** User can't tell which features connect to which parameters.

### Pitfall 5: Discovery Mode Feedback Loop Instability
**What goes wrong:** Dimensional sliders cause wild parameter jumps or the random walk converges to the same boring state.
**Why it happens:** Mapping abstract dimensions (Energy, Density) to concrete parameter ranges without proper scaling.
**How to avoid:** Define each abstract dimension as a weighted blend of normalized parameter ranges. Use exponential smoothing when applying slider changes -- don't jump instantly.
**Warning signs:** Moving one slider causes extreme visual changes, or moving sliders has no visible effect.

### Pitfall 6: Claude API Blocking the UI
**What goes wrong:** UI freezes for 2-5 seconds while waiting for Claude API response.
**Why it happens:** Calling the API synchronously in the main thread.
**How to avoid:** Always call the anthropic SDK from a QRunnable worker thread. Use signals to deliver results back to the main thread.
**Warning signs:** Application becomes unresponsive when "Enhance with AI" is enabled.

## Code Examples

### CLIP Image Preprocessing (numpy-only, no torch)
```python
# Source: matches existing DepthExtractor preprocessing pattern
import cv2
import numpy as np

_CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
_CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
_CLIP_SIZE = 224

def preprocess_clip(image: np.ndarray) -> np.ndarray:
    """Preprocess image for CLIP ViT-B/32.

    Args:
        image: H x W x 3 float32 [0, 1] RGB.

    Returns:
        (1, 3, 224, 224) float32 tensor.
    """
    # Center crop to square
    h, w = image.shape[:2]
    crop = min(h, w)
    top = (h - crop) // 2
    left = (w - crop) // 2
    image = image[top:top+crop, left:left+crop]

    # Resize to 224x224
    resized = cv2.resize(image, (_CLIP_SIZE, _CLIP_SIZE), interpolation=cv2.INTER_LANCZOS4)

    # Normalize with CLIP-specific mean/std
    normalized = (resized - _CLIP_MEAN) / _CLIP_STD

    # HWC -> NCHW
    return normalized.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)
```

### CLIP Zero-Shot Classification
```python
def zero_shot_classify(
    image_embedding: np.ndarray,
    text_embeddings: np.ndarray,
    labels: list[str],
    top_k: int = 5,
) -> list[tuple[str, float]]:
    """Classify image against text label embeddings.

    Args:
        image_embedding: (512,) L2-normalized image embedding.
        text_embeddings: (N, 512) L2-normalized text embeddings.
        labels: N label strings corresponding to text_embeddings rows.
        top_k: Number of top results to return.

    Returns:
        List of (label, confidence) tuples sorted by confidence.
    """
    # Cosine similarity = dot product of L2-normalized vectors
    similarities = image_embedding @ text_embeddings.T  # (N,)

    # Softmax with temperature
    temperature = 100.0  # CLIP default logit scale
    logits = similarities * temperature
    exp_logits = np.exp(logits - logits.max())
    probs = exp_logits / exp_logits.sum()

    # Sort by probability
    indices = np.argsort(probs)[::-1][:top_k]
    return [(labels[i], float(probs[i])) for i in indices]
```

### Collection Embedding Cloud in Viewport
```python
import pygfx

def create_embedding_cloud(positions_3d: np.ndarray, labels: np.ndarray) -> pygfx.Points:
    """Create a pygfx Points object from UMAP-projected embeddings.

    Args:
        positions_3d: (N, 3) float32 from UMAP.
        labels: (N,) int cluster labels from DBSCAN (-1 = noise).

    Returns:
        pygfx.Points object to add to the scene.
    """
    n = positions_3d.shape[0]
    # Color by cluster label
    unique_labels = set(labels)
    palette = _generate_cluster_palette(len(unique_labels))
    colors = np.zeros((n, 4), dtype=np.float32)
    for i, label in enumerate(labels):
        rgb = palette.get(label, (0.5, 0.5, 0.5))
        colors[i] = [*rgb, 0.8]

    geometry = pygfx.Geometry(
        positions=positions_3d.astype(np.float32),
        colors=colors,
        sizes=np.full(n, 8.0, dtype=np.float32),
    )
    material = pygfx.PointsMaterial(color_mode="vertex", size_mode="vertex")
    return pygfx.Points(geometry, material)
```

### Claude API Enrichment
```python
import anthropic

def enrich_tags(
    image_path: str,
    basic_tags: list[tuple[str, float]],
    api_key: str | None = None,
) -> dict | None:
    """Enrich basic semantic tags with Claude descriptions.

    Returns None if API unavailable or disabled.
    """
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                     "media_type": "image/jpeg", "data": image_data}},
                    {"type": "text", "text": (
                        f"These tags were detected: {basic_tags}. "
                        "Provide a 1-sentence artistic description of the mood "
                        "and 1-sentence suggestion for how to sculpt this photo. "
                        "Respond as JSON: {\"description\": \"...\", \"suggestion\": \"...\"}"
                    )}
                ],
            }],
        )
        import json
        return json.loads(response.content[0].text)
    except Exception:
        return None  # Graceful degradation
```

### Abstract Dimensional Slider Mapping
```python
# How abstract dimensions map to concrete simulation parameters
DIMENSION_MAPPINGS = {
    "energy": {
        # Energy: calm(0) <-> chaotic(1)
        "speed": (0.2, 3.0),
        "turbulence_scale": (0.5, 3.0),
        "noise_amplitude": (0.3, 2.5),
        "noise_octaves": (2, 8),
    },
    "density": {
        # Density: sparse(0) <-> dense(1)
        "attraction_strength": (0.1, 1.0),
        "repulsion_radius": (0.05, 0.2),
    },
    "flow": {
        # Flow: rigid(0) <-> fluid(1)
        "viscosity": (0.01, 0.5),
        "damping": (0.99, 0.9),
        "noise_frequency": (0.1, 2.0),
    },
    "structure": {
        # Structure: organic(0) <-> geometric(1)
        "noise_frequency": (0.1, 1.5),
        "repulsion_strength": (0.1, 0.8),
        "pressure_strength": (0.5, 2.0),
    },
}

def apply_dimension(dimension: str, value: float, params: SimulationParams) -> SimulationParams:
    """Map an abstract dimension slider value to concrete parameters."""
    mapping = DIMENSION_MAPPINGS.get(dimension, {})
    updates = {}
    for param, (lo, hi) in mapping.items():
        updates[param] = lo + (hi - lo) * value
    return params.with_update(**updates)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| torch-based CLIP | ONNX Runtime CLIP | 2023+ | No PyTorch dependency, 3x faster inference on CPU |
| t-SNE for embedding viz | UMAP | 2018+ | Faster, better global structure, supports transform of new points |
| Manual feature mapping | Node-based visual routing | Standard in DAWs | Artists understand this paradigm from music production |
| Static presets | Interpolated presets (crossfade) | Common in creative tools | Enables exploration between known-good states |

**Deprecated/outdated:**
- onnx_clip library: Archived February 2026. Use raw ONNX models directly.
- BLIP via transformers: Requires torch. Use ONNX export instead for consistency.

## Open Questions

1. **CLIP Text Tokenizer Without torch**
   - What we know: CLIP's BPE tokenizer can be reimplemented in pure numpy using vocab.json + merges.txt from HuggingFace.
   - What's unclear: Exact file format and whether the onnx_clip tokenizer implementation (MIT licensed, archived) can be extracted.
   - Recommendation: Extract the numpy tokenizer from onnx_clip source (MIT license allows this) or use the simple_tokenizer pattern from OpenAI's CLIP repo.

2. **BLIP ONNX Model Availability**
   - What we know: BLIP can be exported to ONNX (MNaseerSubhani/Blip-Image-Captioning-Large-ONNX on GitHub). However, BLIP is an auto-regressive model (generates text token by token), making ONNX export more complex than CLIP.
   - What's unclear: Whether a pre-exported BLIP-base ONNX model exists that works with onnxruntime-directml without modifications.
   - Recommendation: Start with CLIP only for Phase 3. CLIP's zero-shot classification already covers mood + object detection. If captioning is needed, use Claude API enrichment instead of local BLIP. This avoids the complexity of auto-regressive ONNX inference and keeps the ONNX story clean (single-pass models only).

3. **Optimal DBSCAN eps for CLIP Embeddings**
   - What we know: CLIP ViT-B/32 produces L2-normalized 512-dim embeddings. Cosine distances between same-class images are typically 0.1-0.3.
   - What's unclear: Best eps value depends on collection characteristics.
   - Recommendation: Start with eps=0.3, min_samples=2. Consider auto-tuning via k-distance graph (find the "elbow").

4. **Embedding Cloud Scale in Viewport**
   - What we know: UMAP output coordinates are arbitrary scale. The existing sculpture occupies roughly a [-3, 3] cube.
   - What's unclear: How to position the embedding cloud relative to the sculpture without occlusion.
   - Recommendation: Scale UMAP output to [-5, 5] range and offset along one axis. Provide a toggle to show/hide the cloud.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-timeout |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x --timeout=30` |
| Full suite command | `pytest tests/ --timeout=30` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTRACT-04 | CLIP produces embedding + mood/object tags | unit | `pytest tests/test_clip_extractor.py -x` | Wave 0 |
| COLL-01 | DBSCAN clusters embeddings into labeled groups | unit | `pytest tests/test_collection_analyzer.py -x` | Wave 0 |
| COLL-02 | UMAP projects embeddings to 3D positions | unit | `pytest tests/test_collection_analyzer.py::test_umap_projection -x` | Wave 0 |
| COLL-03 | Cluster centroids produce force attractor data | unit | `pytest tests/test_collection_analyzer.py::test_force_attractors -x` | Wave 0 |
| RENDER-07 | LFO/noise/envelope produce correct waveforms | unit | `pytest tests/test_animation.py -x` | Wave 0 |
| CTRL-02 | Mapping connections serialize/deserialize | unit | `pytest tests/test_mapping.py -x` | Wave 0 |
| CTRL-07 | Preset lerp produces correct intermediate values | unit | `pytest tests/test_preset_interpolation.py -x` | Wave 0 |
| DISC-01 | Random walk produces params within constrained ranges | unit | `pytest tests/test_discovery.py -x` | Wave 0 |
| DISC-02 | Claude API enrichment returns structured response (mock) | unit | `pytest tests/test_enrichment.py -x` | Wave 0 |
| DISC-03 | Claude API mapping suggestions parse correctly (mock) | unit | `pytest tests/test_enrichment.py::test_mapping_suggestions -x` | Wave 0 |
| DISC-04 | All features work when API key is None | unit | `pytest tests/test_enrichment.py::test_offline_fallback -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --timeout=30`
- **Per wave merge:** `pytest tests/ --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_clip_extractor.py` -- covers EXTRACT-04 (mock ONNX session, verify ExtractionResult structure)
- [ ] `tests/test_collection_analyzer.py` -- covers COLL-01, COLL-02, COLL-03
- [ ] `tests/test_animation.py` -- covers RENDER-07
- [ ] `tests/test_mapping.py` -- covers CTRL-02
- [ ] `tests/test_preset_interpolation.py` -- covers CTRL-07
- [ ] `tests/test_discovery.py` -- covers DISC-01
- [ ] `tests/test_enrichment.py` -- covers DISC-02, DISC-03, DISC-04

## Sources

### Primary (HIGH confidence)
- apollo7/extraction/depth.py -- verified ONNX lazy-load pattern with DirectML
- apollo7/extraction/base.py -- verified BaseExtractor + ExtractionResult interface
- apollo7/simulation/parameters.py -- verified SimulationParams dataclass with to_uniform_bytes()
- apollo7/project/presets.py -- verified PresetManager JSON format with sim_params + postfx_params
- apollo7/gui/panels/feature_viewer.py -- verified collapsible section pattern with _Section widget
- pyproject.toml -- verified all current dependencies

### Secondary (MEDIUM confidence)
- [onnx_clip GitHub](https://github.com/lakeraai/onnx_clip) -- API pattern for CLIP ONNX (archived Feb 2026)
- [umap-learn docs](https://umap-learn.readthedocs.io/) -- UMAP API with n_components=3
- [scikit-learn DBSCAN docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html) -- cosine metric support
- [anthropic SDK PyPI](https://pypi.org/project/anthropic/) -- v0.84.0 messages API
- [NodeGraphQt-PySide6](https://github.com/C3RV1/NodeGraphQt-PySide6) -- evaluated but rejected (custom QGraphicsScene preferred)
- [Qdrant/clip-ViT-B-32-vision](https://huggingface.co/Qdrant/clip-ViT-B-32-vision) -- pre-exported CLIP ONNX model
- [immich-app/ViT-B-32__openai](https://huggingface.co/immich-app/ViT-B-32__openai) -- CLIP ONNX exports by OpenCLIP

### Tertiary (LOW confidence)
- [BLIP ONNX conversion](https://github.com/MNaseerSubhani/Blip-Image-Captioning-Large-ONNX) -- auto-regressive ONNX export complexity not verified
- CLIP preprocessing constants (mean/std) -- from OpenAI CLIP repo, standard values but not independently verified against ONNX model inputs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries except umap-learn already installed; patterns proven in Phase 1-2
- Architecture: MEDIUM -- extraction pattern proven, but node editor and discovery mode are novel to this codebase
- Pitfalls: MEDIUM -- CLIP ONNX pitfalls based on documented patterns; UMAP edge cases from library docs
- BLIP feasibility: LOW -- auto-regressive ONNX inference is complex; recommend CLIP-only + Claude API instead

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable libraries, 30-day validity)
