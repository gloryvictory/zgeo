"""Фоновое сканирование каталога для панели ZGeo."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import List, Optional, Set

from qgis.PyQt.QtCore import QObject, QRunnable, pyqtSignal

from .scanner import GeoFile, scan_folder


class ScanSignals(QObject):
    """Сигналы фоновой задачи сканирования."""

    progress = pyqtSignal(str, int)
    finished = pyqtSignal(object, object, bool)


class ScanTask(QRunnable):
    """Задача сканирования, выполняемая в пуле потоков Qt."""

    PROGRESS_INTERVAL = 0.05

    def __init__(
        self,
        folder: Path,
        enabled_formats: Optional[Set[str]] = None,
    ) -> None:
        super().__init__()
        self.folder = Path(folder)
        self.enabled_formats = enabled_formats
        self.signals = ScanSignals()
        self._cancel_event = threading.Event()
        self._last_progress_at = 0.0
        self._cancelled = False

    def cancel(self) -> None:
        """Попросить задачу остановиться после текущего файла."""

        self._cancel_event.set()

    def run(self) -> None:
        files: List[GeoFile] = []
        error: Optional[Exception] = None
        try:
            files = scan_folder(
                self.folder,
                progress_callback=self._report_progress,
                should_cancel=self._should_cancel,
                enabled_formats=self.enabled_formats,
            )
        except Exception as caught:
            error = caught

        self.signals.finished.emit(files, error, self._cancelled)

    def _should_cancel(self) -> bool:
        if self._cancel_event.is_set():
            self._cancelled = True
            return True
        return False

    def _report_progress(self, path: Path, found_count: int) -> None:
        now = time.monotonic()
        if now - self._last_progress_at < self.PROGRESS_INTERVAL:
            return
        self._last_progress_at = now
        self.signals.progress.emit(str(path), found_count)
