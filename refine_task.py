"""Фоновое уточнение полного объема файлов для панели ZGeo."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Iterable, List, Optional

from qgis.PyQt.QtCore import QObject, QRunnable, pyqtSignal

from .dataset_size import refine_geo_files
from .scanner import GeoFile


class RefineSignals(QObject):
    """Сигналы фоновой задачи уточнения объемов."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object, object, bool)


class RefineTask(QRunnable):
    """Задача уточнения объемов, выполняемая в пуле потоков Qt."""

    PROGRESS_INTERVAL = 0.05

    def __init__(self, files: Iterable[GeoFile]) -> None:
        super().__init__()
        self.files: List[GeoFile] = list(files)
        self.signals = RefineSignals()
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
            files = refine_geo_files(
                self.files,
                progress_callback=self._report_progress,
                should_cancel=self._should_cancel,
            )
        except Exception as caught:
            error = caught

        self.signals.finished.emit(files, error, self._cancelled)

    def _should_cancel(self) -> bool:
        if self._cancel_event.is_set():
            self._cancelled = True
            return True
        return False

    def _report_progress(
        self, current: int, total: int, path: Path
    ) -> None:
        now = time.monotonic()
        if now - self._last_progress_at < self.PROGRESS_INTERVAL:
            return
        self._last_progress_at = now
        self.signals.progress.emit(current, total, str(path))
