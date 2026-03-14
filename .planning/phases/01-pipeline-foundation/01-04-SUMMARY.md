---
phase: 01-pipeline-foundation
plan: 04
subsystem: extraction, pointcloud, ui
tags: [onnx, directml, depth-anything-v2, point-cloud, lod, depth-projection, feature-clustering]

# Dependency graph
requires:
  - phase: 01-01
    provides: "PySide6 app skeleton, ViewportWidget, settings module"
  - phase: 01-02
    provides: "Photo ingestion pipeline (not directly used but prerequisite)"
  - phase: 01-03
    provides: "BaseExtractor ABC, ExtractionResult, ColorExtractor, EdgeExtractor, FeatureCache, FeatureStripPanel"
provides:
  - "DepthExtractor: Depth Anything V2 ONNX inference with DirectML/CPU fallback"
  - "ExtractionPipeline: sequential orchestrator with cache integration"
  - "generate_depth_projected_cloud: full pixel density relief sculpture layout"
  - "generate_feature_clustered_cloud: color-similarity abstract 3D grouping"
  - "decimate_points: grid-based LOD spatial decimation"
  - "PointCloudGenerator: facade with auto LOD when over point budget"
  - "DepthMapCard: blue-to-yellow heatmap thumbnail in feature strip"
affects: [01-05]

# Tech tracking
tech-stack:
  added: [onnxruntime-directml]
  patterns: [lazy ONNX session loading, grid-based spatial LOD decimation, numpy colormap without matplotlib, ExtractionPipeline cache-first orchestration]

key-files:
  created:
    - apollo7/extraction/depth.py
    - apollo7/extraction/pipeline.py
    - apollo7/pointcloud/__init__.py
    - apollo7/pointcloud/generator.py
    - apollo7/pointcloud/depth_projection.py
    - apollo7/pointcloud/feature_cluster.py
    - apollo7/pointcloud/lod.py
    - tests/test_depth_extractor.py
    - tests/test_pointcloud_generator.py
  modified:
    - apollo7/extraction/__init__.py
    - apollo7/gui/panels/feature_strip.py

key-decisions:
  - "Lazy ONNX session loading: session created on first extract() call, not at import time"
  - "DirectML warning on fallback: log warning but don't crash if GPU unavailable"
  - "Blue-to-yellow colormap for depth heatmap via pure numpy (no matplotlib dependency)"
  - "Grid-based LOD: divide space into cells, keep point closest to cell center"

patterns-established:
  - "Lazy model loading for GPU resources (don't block import)"
  - "ExtractionPipeline: cache-first, extract on miss, store after extract"
  - "Point cloud arrays: contiguous float32 for GPU buffer upload"
  - "LOD via grid-based spatial decimation with configurable factor"

requirements-completed: [EXTRACT-03, RENDER-01]

# Metrics
duration: ~3min
completed: 2026-03-14
---

# Phase 1 Plan 04: Depth Extraction and Point Cloud Generation Summary

**Depth Anything V2 ONNX depth extractor, extraction pipeline orchestrator, and point cloud generation in depth-projected and feature-clustered modes with grid-based LOD decimation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-14T15:13:56Z
- **Completed:** 2026-03-14T15:17:20Z
- **Tasks:** 2 (1 TDD + 1 auto)
- **Files created:** 9
- **Files modified:** 2

## Accomplishments
- DepthExtractor with lazy ONNX session loading, ImageNet preprocessing, bilinear depth resize, and [0,1] normalization
- ExtractionPipeline orchestrating extractors in sequence with cache-first strategy
- Depth-projected point cloud at full pixel density (100x100 image = 10,000 points) with configurable depth exaggeration and layer offset
- Feature-clustered point cloud grouping pixels by dominant color similarity into abstract 3D clusters
- Grid-based LOD decimation reducing point count while preserving spatial distribution
- PointCloudGenerator facade with auto LOD when exceeding 5M point budget
- Depth map heatmap card (blue-to-yellow gradient) in feature strip alongside color and edge cards

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for depth/pipeline/pointcloud** - `49dd217` (test)
2. **Task 1 GREEN: Depth extractor, pipeline, and point cloud generation** - `dff09c3` (feat)
3. **Task 2: Depth map heatmap card in feature strip** - `a8a390e` (feat)

## Files Created/Modified
- `apollo7/extraction/depth.py` - DepthExtractor with ONNX inference, DirectML/CPU fallback
- `apollo7/extraction/pipeline.py` - ExtractionPipeline sequential orchestrator with caching
- `apollo7/pointcloud/__init__.py` - Package init with public exports
- `apollo7/pointcloud/generator.py` - PointCloudGenerator facade with auto LOD
- `apollo7/pointcloud/depth_projection.py` - Depth-projected relief sculpture layout
- `apollo7/pointcloud/feature_cluster.py` - Color-similarity clustered abstract layout
- `apollo7/pointcloud/lod.py` - Grid-based spatial decimation for LOD
- `tests/test_depth_extractor.py` - 5 depth extractor + 2 pipeline tests (mocked ONNX)
- `tests/test_pointcloud_generator.py` - 4 depth-projected + 1 feature-clustered + 2 LOD tests
- `apollo7/extraction/__init__.py` - Updated: added DepthExtractor, ExtractionPipeline exports
- `apollo7/gui/panels/feature_strip.py` - Updated: DepthMapCard with blue-yellow heatmap

## Decisions Made
- Lazy ONNX session: created on first extract() call to avoid blocking import and startup
- DirectML fallback: log warning if DmlExecutionProvider unavailable, continue with CPU
- Blue-to-yellow colormap applied via pure numpy to avoid matplotlib dependency
- Grid-based LOD: divide space into cubic cells, keep the point closest to each cell center
- Feature clustering uses color-distance grouping with cluster centers from dominant colors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Note: the Depth Anything V2 ONNX model file must be downloaded separately and placed at `models/depth_anything_v2_vits.onnx` before running depth extraction on real images.

## Next Phase Readiness
- Complete extraction pipeline (color + edges + depth) ready for Plan 05 controls wiring
- Point cloud generation produces arrays ready for ViewportWidget.add_points()
- LOD system ready for performance management with multi-photo loading
- Feature strip shows all three extraction result cards

## Self-Check: PASSED

All 9 created files verified present. All 3 task commits (49dd217, dff09c3, a8a390e) confirmed in git history.

---
*Phase: 01-pipeline-foundation*
*Completed: 2026-03-14*
