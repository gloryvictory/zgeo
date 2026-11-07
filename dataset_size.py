"""Полный объем пространственных наборов данных.

Некоторые форматы хранят данные не в одном файле, а в наборе: например,
Shapefile состоит из SHP, DBF, SHX, PRJ и других файлов, а MapInfo MIF
дополняется MID. Модуль не зависит от QGIS и PyQt, поэтому его можно
тестировать отдельно.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .scanner import FORMATS, RASTER, GeoFile

ProgressCallback = Callable[[int, int, Path], None]
CancelCallback = Callable[[], bool]
DirectoryIndex = Dict[str, Path]

# Сопутствующие файлы, имя которых начинается с имени основного файла:
# roads.shp -> roads.dbf, roads.shx и т.п.
_STEM_SIDECARS: Dict[str, Tuple[str, ...]] = {
    ".shp": (
        ".shx",
        ".dbf",
        ".prj",
        ".cpg",
        ".qix",
        ".sbn",
        ".sbx",
        ".fbn",
        ".fbx",
        ".ain",
        ".aih",
        ".atx",
        ".ixs",
        ".mxs",
        ".fix",
    ),
    ".mif": (".mid",),
    ".tab": (".dat", ".map", ".id", ".ind"),
    ".csv": (".csvt", ".prj"),
    ".bil": (".hdr", ".prj", ".tfw", ".wld", ".stx", ".clr"),
    ".bsq": (".hdr", ".prj", ".tfw", ".wld", ".stx", ".clr"),
    ".bip": (".hdr", ".prj", ".tfw", ".wld", ".stx", ".clr"),
}

# Файлы, имя которых дописывается после полного имени основного файла:
# roads.shp -> roads.shp.xml, dem.tif -> dem.tif.aux.xml.
_APPENDED_SIDECARS: Dict[str, Tuple[str, ...]] = {
    ".shp": (".xml",),
    ".tif": (".aux.xml", ".ovr"),
    ".tiff": (".aux.xml", ".ovr"),
    ".img": (".aux.xml", ".ovr"),
    ".jp2": (".aux.xml", ".ovr"),
    ".ecw": (".aux.xml", ".ovr"),
    ".sid": (".aux.xml", ".ovr"),
    ".asc": (".aux.xml", ".ovr"),
    ".dem": (".aux.xml", ".ovr"),
    ".hgt": (".aux.xml", ".ovr"),
    ".nc": (".aux.xml", ".ovr"),
    ".hdf": (".aux.xml", ".ovr"),
    ".h5": (".aux.xml", ".ovr"),
}

# Общие спутники растров: world-файлы и файл проекции.
_RASTER_STEM_SIDECARS = (".tfw", ".wld", ".prj")
_RASTER_EXTENSIONS = frozenset(
    extension
    for extension, format_info in FORMATS.items()
    if format_info.category == RASTER
)


@dataclass(frozen=True)
class DatasetSize:
    """Размер набора данных с разбивкой на основной файл и спутники."""

    path: Path
    primary_size: int
    sidecar_size: int
    sidecars: Tuple[Path, ...]

    @property
    def total_size(self) -> int:
        return self.primary_size + self.sidecar_size


def _dataset_names(path: Path) -> Tuple[str, ...]:
    """Вернуть имена основного файла и его возможных спутников."""

    suffix = path.suffix.lower()
    names: List[str] = [path.name]

    for extension in _STEM_SIDECARS.get(suffix, ()):
        names.append(path.stem + extension)

    if suffix in _RASTER_EXTENSIONS:
        for extension in _RASTER_STEM_SIDECARS:
            names.append(path.stem + extension)

    for extension in _APPENDED_SIDECARS.get(suffix, ()):
        names.append(path.name + extension)

    unique: List[str] = []
    seen = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(name)
    return tuple(unique)


def _read_directory_index(directory: Path) -> DirectoryIndex:
    """Сопоставить имена файлов в каталоге без учета регистра."""

    try:
        entries = list(directory.iterdir())
    except OSError:
        return {}

    index: DirectoryIndex = {}
    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        index[entry.name.casefold()] = entry
    return index


def _safe_size(path: Optional[Path]) -> int:
    if path is None:
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def measure_geo_file(
    geo_file: GeoFile,
    directory_index: Optional[DirectoryIndex] = None,
) -> DatasetSize:
    """Посчитать размер файла вместе с его сопутствующими файлами."""

    path = geo_file.path
    index = (
        directory_index
        if directory_index is not None
        else _read_directory_index(path.parent)
    )

    primary = index.get(path.name.casefold())
    if primary is None:
        try:
            if path.is_file():
                primary = path
        except OSError:
            primary = None

    candidates: List[Path] = []
    if primary is not None:
        candidates.append(primary)

    for name in _dataset_names(path)[1:]:
        candidate = index.get(name.casefold())
        if candidate is not None:
            candidates.append(candidate)

    unique: List[Path] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    primary_key = str(primary).casefold() if primary is not None else None
    sidecars = tuple(
        candidate
        for candidate in unique
        if str(candidate).casefold() != primary_key
    )

    return DatasetSize(
        path=path,
        primary_size=_safe_size(primary),
        sidecar_size=sum(_safe_size(item) for item in sidecars),
        sidecars=sidecars,
    )


def measure_geo_file_cached(
    geo_file: GeoFile,
    cache: Dict[str, DirectoryIndex],
) -> DatasetSize:
    """Посчитать размер набора, переиспользуя индекс каталога."""

    directory = geo_file.path.parent
    directory_key = str(directory)
    directory_index = cache.get(directory_key)
    if directory_index is None:
        directory_index = _read_directory_index(directory)
        cache[directory_key] = directory_index
    return measure_geo_file(geo_file, directory_index)


def refine_geo_files(
    files: Iterable[GeoFile],
    progress_callback: Optional[ProgressCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
) -> List[GeoFile]:
    """Вернуть копии файлов с уточненным полным объемом."""

    source = list(files)
    total = len(source)
    result: List[GeoFile] = []
    cache: Dict[str, DirectoryIndex] = {}

    for index, geo_file in enumerate(source, 1):
        if should_cancel is not None and should_cancel():
            break

        directory_key = str(geo_file.path.parent)
        directory_index = cache.get(directory_key)
        if directory_index is None:
            directory_index = _read_directory_index(geo_file.path.parent)
            cache[directory_key] = directory_index

        detail = measure_geo_file(geo_file, directory_index)
        result.append(replace(geo_file, size=detail.total_size))

        if progress_callback is not None:
            progress_callback(index, total, geo_file.path)

    return result
