"""Background extraction worker using QRunnable + QThreadPool.

Runs the full extraction pipeline (color, edges, depth) and generates
point cloud data for each photo in a background thread. Emits signals
for progressive viewport updates.

IMPORTANT: Point cloud arrays are generated in the worker thread but
must be added to the pygfx scene in the main thread.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
from PySide6 import QtCore

if TYPE_CHECKING:
    from apollo7.extraction.cache import FeatureCache
    from apollo7.extraction.pipeline import ExtractionPipeline
    from apollo7.pointcloud.generator import PointCloudGenerator

logger = logging.getLogger(__name__)


class WorkerSignals(QtCore.QObject):
    """Signals emitted by ExtractionWorker.

    Qt signals must be on a QObject, not QRunnable directly.
    """

    # (current_index, total_count)
    progress = QtCore.Signal(int, int)

    # (photo_path, features_dict, point_cloud_tuple)
    # point_cloud_tuple is (positions, colors, sizes) numpy arrays
    photo_complete = QtCore.Signal(str, dict, object)

    # Emitted when all photos are processed
    finished = QtCore.Signal()

    # (photo_path, error_message)
    error = QtCore.Signal(str, str)


class ExtractionWorker(QtCore.QRunnable):
    """Background worker that runs extraction + point cloud generation.

    For each photo:
    1. Run extraction pipeline (color, edges, depth in order)
    2. Generate point cloud from features
    3. Emit photo_complete with features and point cloud arrays

    Errors per-photo are caught and emitted; processing continues.

    Usage:
        worker = ExtractionWorker(photo_paths, images, pipeline, generator, cache)
        worker.signals.photo_complete.connect(on_photo_complete)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        photo_paths: list[str],
        images: dict[str, np.ndarray],
        pipeline: "ExtractionPipeline",
        generator: "PointCloudGenerator",
        cache: "FeatureCache",
        mode: str = "depth_projected",
        depth_exaggeration: float = 4.0,
        multi_photo_mode: str = "stacked",
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

        self._photo_paths = photo_paths
        self._images = images
        self._pipeline = pipeline
        self._generator = generator
        self._cache = cache
        self._mode = mode
        self._depth_exaggeration = depth_exaggeration
        self._multi_photo_mode = multi_photo_mode

    def run(self) -> None:
        """Execute in background thread."""
        total = len(self._photo_paths)
        if total == 0:
            self.signals.finished.emit()
            return

        for i, path in enumerate(self._photo_paths):
            try:
                image = self._images.get(path)
                if image is None:
                    self.signals.error.emit(path, "Image not found in memory")
                    self.signals.progress.emit(i + 1, total)
                    continue

                # Run extraction pipeline (color first, then edges, then depth)
                features = self._pipeline.run(image, path, cache=self._cache)

                # Generate point cloud
                kwargs: dict[str, Any] = {}
                if self._mode == "depth_projected":
                    kwargs["depth_exaggeration"] = self._depth_exaggeration
                    if self._multi_photo_mode == "stacked":
                        # Stack layers with Z offset based on photo index
                        kwargs["layer_offset"] = i * (self._depth_exaggeration + 2.0)

                try:
                    positions, colors, sizes = self._generator.generate(
                        image, features, mode=self._mode, **kwargs
                    )
                    cloud_data = (positions, colors, sizes)
                except Exception as gen_exc:
                    # If point cloud generation fails (e.g., no depth model),
                    # still emit features with None cloud
                    logger.warning(
                        "Point cloud generation failed for %s: %s", path, gen_exc
                    )
                    cloud_data = None

                self.signals.photo_complete.emit(path, features, cloud_data)

            except Exception as exc:
                logger.error("Extraction failed for %s: %s", path, exc)
                self.signals.error.emit(path, str(exc))

            self.signals.progress.emit(i + 1, total)

        self.signals.finished.emit()
