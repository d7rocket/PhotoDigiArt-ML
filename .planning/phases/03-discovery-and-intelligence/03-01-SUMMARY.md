---
phase: 03-discovery-and-intelligence
plan: 01
subsystem: extraction
tags: [clip, onnx, semantic-extraction, zero-shot, bpe-tokenizer, embeddings]

# Dependency graph
requires:
  - phase: 01-pipeline-foundation
    provides: "BaseExtractor interface, ExtractionPipeline, FeatureViewerPanel"
provides:
  - "ClipExtractor producing mood tags, object tags, and 512-dim embeddings"
  - "CLIPTokenizer for BPE text encoding (pure Python/numpy)"
  - "Semantic Tags section in feature viewer with colored pill widgets"
  - "Flow layout for wrapping tag pills"
affects: [03-discovery-and-intelligence, collection-analysis, discovery-mode]

# Tech tracking
tech-stack:
  added: [clip-vit-b32-onnx, bpe-tokenizer]
  patterns: [zero-shot-classification, text-embedding-caching, flow-layout-widget]

key-files:
  created:
    - apollo7/extraction/clip.py
    - apollo7/extraction/clip_tokenizer.py
    - tests/test_clip_extractor.py
    - models/README.md
  modified:
    - apollo7/extraction/__init__.py
    - apollo7/extraction/pipeline.py
    - apollo7/gui/main_window.py
    - apollo7/gui/panels/feature_viewer.py
    - tests/test_feature_viewer.py

key-decisions:
  - "CLIP ViT-B/32 via ONNX for semantic extraction (DirectML/CPU)"
  - "Pure Python/numpy BPE tokenizer (no torch dependency)"
  - "Text embeddings cached after first classification run"
  - "Prompt templates for zero-shot: 'a photo with a {} mood' and 'a photo of a {}'"
  - "Logit scale 100.0 with softmax for zero-shot probabilities"

patterns-established:
  - "Dual ONNX session pattern: separate visual + text encoder sessions"
  - "Flow layout for wrapping tag pill widgets in feature viewer"
  - "TagPillWidget with QPainter rendering and confidence-modulated opacity"

requirements-completed: [EXTRACT-04]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 3 Plan 01: CLIP Semantic Extraction Summary

**CLIP ViT-B/32 zero-shot classification producing mood/object tags and 512-dim embeddings, displayed as colored pills in feature viewer**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T04:51:15Z
- **Completed:** 2026-03-15T04:56:31Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- ClipExtractor with lazy dual ONNX session loading (visual + text encoders)
- Zero-shot classification for 8 mood labels and 10 object labels with confidence scores
- Pure Python/numpy BPE tokenizer for CLIP text encoding (no torch)
- Semantic Tags section in feature viewer with colored pill widgets and flow layout
- Full test suite: 248 passed (5 new CLIP tests + 1 new semantic viewer test)

## Task Commits

Each task was committed atomically:

1. **Task 1: CLIP extractor with tokenizer and tests (TDD RED)** - `409297e` (test)
2. **Task 1: CLIP extractor with tokenizer and tests (TDD GREEN)** - `2c3ebed` (feat)
3. **Task 2: Pipeline integration and feature viewer semantic section** - `8e09f3c` (feat)

_TDD task 1 had separate RED and GREEN commits._

## Files Created/Modified
- `apollo7/extraction/clip.py` - ClipExtractor with lazy ONNX loading, preprocessing, zero-shot classification
- `apollo7/extraction/clip_tokenizer.py` - Pure Python BPE tokenizer for CLIP text encoder input
- `tests/test_clip_extractor.py` - 5 tests with mocked ONNX sessions
- `models/README.md` - Download instructions for CLIP ONNX models and BPE vocabulary
- `apollo7/extraction/__init__.py` - Added ClipExtractor export
- `apollo7/gui/main_window.py` - Added ClipExtractor to pipeline extractor list
- `apollo7/gui/panels/feature_viewer.py` - Added semantic section, TagPillWidget, FlowLayout
- `tests/test_feature_viewer.py` - Updated section counts (3->4), added semantic test

## Decisions Made
- CLIP ViT-B/32 via ONNX with DirectML preferred, CPU fallback (matches DepthExtractor pattern)
- Pure Python/numpy BPE tokenizer avoids torch dependency for text encoding
- Text embeddings cached after first computation since labels don't change between photos
- Prompt templates ("a photo with a {} mood", "a photo of a {}") improve zero-shot accuracy
- Logit scale 100.0 matching CLIP's original temperature for softmax probabilities
- Mood colors mapped by category (serene=blue, chaotic=red, joyful=yellow, etc.)
- Object tags all use teal/green palette for visual distinction from mood tags

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cv2.INTER_BICUBIC -> cv2.INTER_CUBIC**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** cv2 module does not have INTER_BICUBIC attribute (correct name is INTER_CUBIC)
- **Fix:** Changed cv2.INTER_BICUBIC to cv2.INTER_CUBIC in preprocess_clip()
- **Files modified:** apollo7/extraction/clip.py
- **Verification:** Tests pass
- **Committed in:** 2c3ebed (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Fixed regex \p{L}/\p{N} unicode property escapes**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Python re module doesn't support \p{L}/\p{N} unicode property escapes (that's PCRE/regex module syntax)
- **Fix:** Replaced with standard character classes [a-zA-Z] and [0-9]
- **Files modified:** apollo7/extraction/clip_tokenizer.py
- **Verification:** Tokenizer instantiates without error
- **Committed in:** 2c3ebed (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both were minor API naming/syntax issues. No scope creep.

## Issues Encountered
None beyond the auto-fixed bugs above.

## User Setup Required

CLIP ONNX models must be downloaded before semantic extraction will work at runtime:
- `clip_vit_b32_visual.onnx` - Visual encoder from HuggingFace
- `clip_vit_b32_text.onnx` - Text encoder from HuggingFace
- `bpe_simple_vocab_16e6.txt.gz` - BPE vocabulary from OpenAI CLIP repo

See `models/README.md` for download URLs and instructions. Code handles FileNotFoundError gracefully with clear error messages.

## Next Phase Readiness
- 512-dim CLIP embeddings ready for collection analysis (similarity search, clustering)
- Mood/object tags ready for discovery mode filtering
- Text embedding pipeline ready for Claude enrichment integration
- Feature viewer semantic section ready for additional tag types

---
*Phase: 03-discovery-and-intelligence*
*Completed: 2026-03-15*
