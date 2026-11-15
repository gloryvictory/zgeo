"""Копирование выбранных наборов данных в папку."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .dataset_size import DirectoryIndex, measure_geo_file_cached
from .scanner import GeoFile

CHUNK_SIZE = 1024 * 1024
ProgressCallback = Callable[[int, int, Path], None]
CancelCallback = Callable[[], bool]


@dataclass(frozen=True)
class CopyItem:
    """Один файл, который нужно скопировать."""

    source: Path
    destination: Path
    size: int


@dataclass(frozen=True)
class CopyPlan:
    """План копирования выбранных наборов данных."""

    items: Tuple[CopyItem, ...]
    skipped_same: Tuple[Path, ...]
    duplicate_names: Tuple[str, ...]
    total_size: int


@dataclass(frozen=True)
class CopyResult:
    """Результат копирования."""

    copied: Tuple[Path, ...]
    errors: Tuple[Tuple[Path, str], ...]
    cancelled: bool


class CopyCancelled(Exception):
    """Копирование прервано пользователем."""


def build_copy_plan(
    files: Iterable[GeoFile],
    destination: Path,
) -> CopyPlan:
    """Собрать основные файлы и сопутствующие файлы выбранных наборов."""

    destination = Path(destination)
    cache: Dict[str, DirectoryIndex] = {}
    sources: List[Path] = []
    seen_sources = set()

    for geo_file in files:
        detail = measure_geo_file_cached(geo_file, cache)
        for source in (geo_file.path, *detail.sidecars):
            key = _normalized(source)
            if key in seen_sources:
                continue
            seen_sources.add(key)
            sources.append(Path(source))

    items: List[CopyItem] = []
    skipped_same: List[Path] = []
    duplicate_names: List[str] = []
    seen_destinations = set()

    for source in sources:
        target = destination / source.name
        if _normalized(source) == _normalized(target):
            skipped_same.append(source)
            continue

        target_key = _normalized(target)
        if target_key in seen_destinations:
            if source.name not in duplicate_names:
                duplicate_names.append(source.name)
        else:
            seen_destinations.add(target_key)

        try:
            size = source.stat().st_size
        except OSError:
            size = 0
        items.append(CopyItem(source=source, destination=target, size=size))

    return CopyPlan(
        items=tuple(items),
        skipped_same=tuple(skipped_same),
        duplicate_names=tuple(duplicate_names),
        total_size=sum(item.size for item in items),
    )


def copy_plan(
    plan: CopyPlan,
    progress_callback: Optional[ProgressCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
) -> CopyResult:
    """Скопировать файлы плана, сообщая о ходе и ошибках."""

    copied: List[Path] = []
    errors: List[Tuple[Path, str]] = []
    cancelled = False
    done = 0
    total_items = len(plan.items)

    for index, item in enumerate(plan.items, 1):
        if should_cancel is not None and should_cancel():
            cancelled = True
            break

        try:
            _copy_file(
                item.source,
                item.destination,
                _item_progress_callback(
                    progress_callback,
                    done,
                    plan.total_size,
                    item.source,
                ),
                should_cancel,
            )
            copied.append(item.destination)
        except CopyCancelled:
            cancelled = True
            break
        except Exception as error:
            errors.append((item.source, str(error)))

        done += item.size
        if progress_callback is not None:
            if plan.total_size > 0:
                progress_callback(
                    min(done, plan.total_size),
                    plan.total_size,
                    item.source,
                )
            else:
                progress_callback(index, total_items, item.source)

    return CopyResult(
        copied=tuple(copied),
        errors=tuple(errors),
        cancelled=cancelled,
    )


def _item_progress_callback(
    progress_callback: Optional[ProgressCallback],
    base: int,
    total_size: int,
    source: Path,
) -> Optional[ProgressCallback]:
    if progress_callback is None or total_size <= 0:
        return None

    def report(copied_bytes: int, _source_size: int) -> None:
        progress_callback(
            min(base + copied_bytes, total_size),
            total_size,
            source,
        )

    return report


def _copy_file(
    source: Path,
    destination: Path,
    progress_callback: Optional[ProgressCallback],
    should_cancel: Optional[CancelCallback],
) -> None:
    """Скопировать один файл через временный файл рядом с назначением."""

    source_size = source.stat().st_size
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=str(destination.parent),
            prefix=".zgeo-copy-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            copied_bytes = 0
            with source.open("rb") as handle:
                while True:
                    if (
                        should_cancel is not None
                        and should_cancel()
                    ):
                        raise CopyCancelled()
                    chunk = handle.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    temporary.write(chunk)
                    copied_bytes += len(chunk)
                    if progress_callback is not None:
                        progress_callback(copied_bytes, source_size)

        try:
            shutil.copystat(source, temporary_path)
        except OSError:
            pass
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _normalized(path: Path) -> str:
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(Path(path).absolute()).casefold()
