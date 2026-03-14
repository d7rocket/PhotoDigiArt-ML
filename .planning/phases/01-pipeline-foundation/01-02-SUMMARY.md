---
phase: 01-pipeline-foundation
plan: 02
subsystem: ingestion, ui
tags: [pillow, numpy, qrunnable, qthreadpool, thumbnails, metadata, exif, library-panel, progress-bar]

# Dependency graph
requires:
  - phase: 01-01
    provides: "PySide6 app skeleton, dark theme, ViewportWidget, MainWindow layout"
provides:
  - "Image loading (JPEG, PNG, TIFF) with float32 RGB output"
  - "Batch folder scanning with format filtering"
  - "Thumbnail generation preserving aspect ratio"
  - "EXIF metadata extraction"
  - "LibraryPanel with scrollable 2-column thumbnail grid"
  - "ControlsPanel with extraction button and layout mode radio buttons"
  - "ExtractionProgressBar for batch operation feedback"
  - "IngestionWorker (QRunnable) for background photo loading"
affects: [01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [QRunnable+WorkerSignals for background processing, PIL-to-QPixmap via in-memory PNG buffer, progressive UI population via signal-per-photo]

key-files:
  created:
    - apollo7/ingestion/__init__.py
    - apollo7/ingestion/loader.py
    - apollo7/ingestion/thumbnailer.py
    - apollo7/ingestion/metadata.py
    - apollo7/gui/panels/library_panel.py
    - apollo7/gui/panels/controls_panel.py
    - apollo7/gui/widgets/progress_bar.py
    - apollo7/workers/__init__.py
    - apollo7/workers/ingestion_worker.py
    - tests/test_loader.py
    - tests/test_thumbnailer.py
  modified:
    - apollo7/gui/main_window.py

key-decisions:
  - "PIL-to-QPixmap conversion via in-memory PNG buffer in main thread (Qt requires main thread for pixmap creation)"
  - "IngestionWorker emits PIL thumbnails, not QPixmaps, to keep Qt operations out of worker thread"
  - "Format detection via Pillow header, not file extension, for robust format validation"

patterns-established:
  - "WorkerSignals QObject pattern: signals on separate QObject attached to QRunnable"
  - "Progressive photo loading: worker emits photo_loaded per file, UI updates incrementally"
  - "Library panel grid: 2-column scrollable grid with clickable thumbnail cards"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03]

# Metrics
duration: ~5min
completed: 2026-03-14
---

# Phase 1 Plan 02: Photo Ingestion Pipeline Summary

**Image loader with float32 RGB output, thumbnail grid library panel, batch folder ingestion via QRunnable workers with progressive progress bar feedback**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T15:06:36Z
- **Completed:** 2026-03-14T15:11:13Z
- **Tasks:** 2 (1 TDD + 1 auto)
- **Files created:** 11
- **Files modified:** 1

## Accomplishments
- Image loader handles JPEG, PNG, TIFF with float32 RGB [0-1] normalization, plus batch folder scanning with format filtering
- Thumbnail generator preserves aspect ratio via Pillow LANCZOS resampling
- Metadata extractor returns dimensions, format, file size, and EXIF data
- Library panel with scrollable 2-column thumbnail grid, Load Photo/Folder buttons, and photo count label
- Background ingestion worker keeps UI responsive during batch loading with progressive thumbnail population
- Progress bar shows "Processing X/Y photos..." during batch operations
- 9 new tests covering loader, folder scanning, thumbnails, and metadata; all 20 project tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for loader, thumbnailer, metadata** - `ef07660` (test)
2. **Task 1 GREEN: Image loader, thumbnailer, metadata extraction** - `39a97a2` (feat)
3. **Task 2: Library panel, controls panel, progress bar, ingestion worker** - `d3948d3` (feat)

## Files Created/Modified
- `apollo7/ingestion/__init__.py` - Ingestion package init
- `apollo7/ingestion/loader.py` - load_image (float32 RGB), load_folder (scan + filter)
- `apollo7/ingestion/thumbnailer.py` - generate_thumbnail with aspect ratio preservation
- `apollo7/ingestion/metadata.py` - extract_metadata with EXIF support
- `apollo7/gui/panels/__init__.py` - Panels package init
- `apollo7/gui/panels/library_panel.py` - Scrollable 2-column thumbnail grid with load buttons
- `apollo7/gui/panels/controls_panel.py` - Extract Features button + layout mode radio buttons
- `apollo7/gui/widgets/progress_bar.py` - ExtractionProgressBar with start/update/finish
- `apollo7/workers/__init__.py` - Workers package init
- `apollo7/workers/ingestion_worker.py` - QRunnable background loader with WorkerSignals
- `apollo7/gui/main_window.py` - Wired ingestion buttons, progress bar, PIL-to-QPixmap conversion
- `tests/test_loader.py` - 7 tests for load_image, load_folder, extract_metadata
- `tests/test_thumbnailer.py` - 2 tests for thumbnail generation and aspect ratio

## Decisions Made
- **PIL-to-QPixmap via PNG buffer:** PIL Image thumbnails are serialized to an in-memory PNG byte buffer and deserialized as QPixmap in the main thread. This keeps all Qt pixmap operations in the main thread as required by Qt.
- **Header-based format detection:** Pillow detects image format via file header, not extension. This prevents misidentified files from causing crashes.
- **WorkerSignals on QObject:** Qt signals cannot be defined directly on QRunnable, so a separate WorkerSignals(QObject) is attached to each worker -- standard pattern from research phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion for image dimensions**
- **Found during:** Task 1 GREEN (test verification)
- **Issue:** Test helper `_make_image(size=(200, 150))` creates a numpy array with shape (200, 150, 3) meaning height=200, width=150, but test asserted width==200
- **Fix:** Changed test to use `size=(150, 200)` to create an image with width=200, height=150
- **Files modified:** tests/test_loader.py
- **Verification:** All 9 tests pass
- **Committed in:** 39a97a2 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Minor test correction, no scope creep.

## Issues Encountered

- Plan 01-03 (extraction) was executed in parallel and had already modified main_window.py with extraction code (FeatureStripPanel, _ExtractionWorker, FeatureCache). Integrated ingestion wiring into the existing extraction-aware main_window.py rather than overwriting it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ingestion pipeline complete: photos can be loaded, thumbnails generated, metadata extracted
- Library panel ready for photo selection signals to trigger extraction (Plan 03)
- IngestionWorker pattern reusable for future extraction workers
- Controls panel placeholder ready for wiring in Plan 05

## Self-Check: PASSED

All 12 key files verified present. All 3 task commits (ef07660, 39a97a2, d3948d3) confirmed in git history.

---
*Phase: 01-pipeline-foundation*
*Completed: 2026-03-14*
