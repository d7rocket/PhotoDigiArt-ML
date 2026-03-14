"""Background ingestion worker using QRunnable + QThreadPool.

Loads images, generates thumbnails, and extracts metadata in a
background thread. Emits signals for progressive UI updates.

IMPORTANT: QPixmap creation must happen in the main thread.
The worker emits PIL Image thumbnails; the main thread converts
them to QPixmap before passing to the library panel.
"""

import logging
from pathlib import Path

from PySide6 import QtCore

from apollo7.ingestion.loader import SUPPORTED_EXTENSIONS, load_image
from apollo7.ingestion.metadata import extract_metadata
from apollo7.ingestion.thumbnailer import generate_thumbnail

logger = logging.getLogger(__name__)


class WorkerSignals(QtCore.QObject):
    """Signals emitted by IngestionWorker.

    Qt signals must be on a QObject, not QRunnable directly.
    """

    # (current_index, total_count)
    progress = QtCore.Signal(int, int)

    # (file_path_str, pil_thumbnail_image, metadata_dict)
    photo_loaded = QtCore.Signal(str, object, object)

    # Emitted when all files are processed
    finished = QtCore.Signal()

    # Error message string
    error = QtCore.Signal(str)


class IngestionWorker(QtCore.QRunnable):
    """Background worker that loads images, generates thumbnails, and extracts metadata.

    Usage:
        worker = IngestionWorker(file_paths=[...])
        worker.signals.photo_loaded.connect(on_photo_loaded)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, file_paths: list[str | Path] | None = None, folder: str | Path | None = None):
        super().__init__()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

        # Build file list
        self._paths: list[Path] = []
        if file_paths:
            self._paths = [Path(p) for p in file_paths]
        elif folder:
            folder = Path(folder)
            self._paths = sorted(
                p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            )

    def run(self):
        """Execute in background thread."""
        total = len(self._paths)
        if total == 0:
            self.signals.finished.emit()
            return

        for i, path in enumerate(self._paths):
            try:
                image = load_image(path)
                thumbnail = generate_thumbnail(image, size=128)
                metadata = extract_metadata(path)

                # Emit PIL thumbnail -- main thread will convert to QPixmap
                self.signals.photo_loaded.emit(str(path), thumbnail, metadata)

            except Exception as exc:
                logger.warning("Failed to load %s: %s", path, exc)
                self.signals.error.emit(f"Failed: {path.name} -- {exc}")

            self.signals.progress.emit(i + 1, total)

        self.signals.finished.emit()
