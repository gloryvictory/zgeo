"""Поиск пространственных файлов в каталоге.

Модуль не зависит от QGIS и PyQt, поэтому его можно тестировать отдельно.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

ProgressCallback = Callable[[Path, int], None]
CancelCallback = Callable[[], bool]

# Категории используются интерфейсом для подсказок и фильтрации.
VECTOR = "vector"
RASTER = "raster"
TABLE = "table"
OTHER = "other"


@dataclass(frozen=True)
class FormatInfo:
    """Описание поддерживаемого формата."""

    name: str
    category: str


@dataclass(frozen=True)
class FormatGroup:
    """Формат с одним или несколькими расширениями."""

    name: str
    category: str
    extensions: Tuple[str, ...]


@dataclass(frozen=True)
class GeoFile:
    """Найденный пространственный файл."""

    path: Path
    relative_path: Path
    format: FormatInfo
    size: int

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def relative_posix(self) -> str:
        return self.relative_path.as_posix()

    @property
    def category(self) -> str:
        return self.format.category


# Форматы, которые QGIS умеет открывать напрямую (или через установленный
# дополнительный провайдер). Служебные файлы вроде .dbf, .shx, .prj и
# .shp.xml намеренно не попадают в список: они относятся к набору данных,
# а не являются самостоятельными слоями.
FORMATS: Dict[str, FormatInfo] = {
    # Векторные форматы
    ".shp": FormatInfo("ESRI Shapefile", VECTOR),
    ".gpkg": FormatInfo("GeoPackage", VECTOR),
    ".geojson": FormatInfo("GeoJSON", VECTOR),
    ".json": FormatInfo("GeoJSON", VECTOR),
    ".geojsonl": FormatInfo("GeoJSON Sequence", VECTOR),
    ".ndjson": FormatInfo("GeoJSON Sequence", VECTOR),
    ".gml": FormatInfo("GML", VECTOR),
    ".kml": FormatInfo("KML", VECTOR),
    ".kmz": FormatInfo("KMZ", VECTOR),
    ".gpx": FormatInfo("GPX", VECTOR),
    ".tab": FormatInfo("MapInfo TAB", VECTOR),
    ".mif": FormatInfo("MapInfo MIF", VECTOR),
    ".dxf": FormatInfo("DXF", VECTOR),
    ".dwg": FormatInfo("DWG", VECTOR),
    ".dgn": FormatInfo("DGN", VECTOR),
    ".fgb": FormatInfo("FlatGeobuf", VECTOR),
    ".sqlite": FormatInfo("SQLite", VECTOR),
    ".spatialite": FormatInfo("SpatiaLite", VECTOR),
    ".osm": FormatInfo("OpenStreetMap", VECTOR),
    ".pbf": FormatInfo("OSM PBF", VECTOR),
    ".parquet": FormatInfo("GeoParquet", VECTOR),
    ".arrow": FormatInfo("GeoArrow", VECTOR),
    ".vrt": FormatInfo("VRT", OTHER),
    ".mbtiles": FormatInfo("MBTiles", OTHER),
    ".pmtiles": FormatInfo("PMTiles", OTHER),

    # Растровые форматы
    ".tif": FormatInfo("GeoTIFF / TIFF", RASTER),
    ".tiff": FormatInfo("GeoTIFF / TIFF", RASTER),
    ".cog": FormatInfo("Cloud Optimized GeoTIFF", RASTER),
    ".img": FormatInfo("ERDAS IMG", RASTER),
    ".asc": FormatInfo("Esri ASCII Grid", RASTER),
    ".dem": FormatInfo("DEM", RASTER),
    ".hgt": FormatInfo("SRTM HGT", RASTER),
    ".jp2": FormatInfo("JPEG 2000", RASTER),
    ".ecw": FormatInfo("ECW", RASTER),
    ".sid": FormatInfo("MrSID", RASTER),
    ".bil": FormatInfo("BIL", RASTER),
    ".bsq": FormatInfo("BSQ", RASTER),
    ".bip": FormatInfo("BIP", RASTER),
    ".nc": FormatInfo("NetCDF", RASTER),
    ".hdf": FormatInfo("HDF", RASTER),
    ".h5": FormatInfo("HDF5", RASTER),
    ".grib": FormatInfo("GRIB", RASTER),
    ".grb": FormatInfo("GRIB", RASTER),
    ".grib2": FormatInfo("GRIB2", RASTER),

    # Таблицы, которые QGIS также может подключать как слои
    ".csv": FormatInfo("CSV", TABLE),
    ".tsv": FormatInfo("TSV", TABLE),
    ".xls": FormatInfo("Excel", TABLE),
    ".xlsx": FormatInfo("Excel", TABLE),
}

SUPPORTED_EXTENSIONS = tuple(sorted(FORMATS))
DEFAULT_DISABLED_FORMATS = frozenset({"Excel"})


def get_format_groups() -> List[FormatGroup]:
    """Вернуть форматы, сгруппированные по отображаемому имени."""

    groups: Dict[str, FormatGroup] = {}
    for extension, format_info in FORMATS.items():
        group = groups.get(format_info.name)
        if group is None:
            groups[format_info.name] = FormatGroup(
                format_info.name,
                format_info.category,
                (extension,),
            )
            continue

        groups[format_info.name] = FormatGroup(
            group.name,
            group.category,
            group.extensions + (extension,),
        )

    return list(groups.values())


def get_format(path: Path) -> Optional[FormatInfo]:
    """Вернуть описание формата по расширению файла."""

    return FORMATS.get(Path(path).suffix.lower())


def _make_geofile(path: Path, root: Path, format_info: FormatInfo) -> GeoFile:
    try:
        size = path.stat().st_size
    except OSError:
        # Файл может быть недоступен для чтения, но имя всё равно полезно
        # показать пользователю.
        size = 0

    return GeoFile(
        path=path,
        relative_path=path.relative_to(root),
        format=format_info,
        size=size,
    )


def scan_folder(
    folder: Path,
    recursive: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
    enabled_formats: Optional[Set[str]] = None,
) -> List[GeoFile]:
    """Найти поддерживаемые пространственные файлы в каталоге.

    Args:
        folder: Каталог для сканирования.
        recursive: Искать ли файлы во вложенных каталогах.
        progress_callback: Получает путь текущего найденного файла
            поддерживаемого формата и число уже найденных файлов.
        should_cancel: Если возвращает True, поиск останавливается.
            Уже найденные файлы возвращаются как частичный результат.
        enabled_formats: Имена форматов, которые нужно искать.
            Если None, ищутся все поддерживаемые форматы.

    Returns:
        Отсортированный по относительному пути список файлов.

    Raises:
        NotADirectoryError: Если переданный путь не является каталогом.
    """

    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    found: List[GeoFile] = []

    def cancelled() -> bool:
        return should_cancel is not None and should_cancel()

    def format_enabled(format_info: FormatInfo) -> bool:
        return (
            enabled_formats is None
            or format_info.name in enabled_formats
        )

    def report(path: Path) -> None:
        if progress_callback is not None:
            progress_callback(path, len(found))

    if recursive:
        stopped = False
        for dir_path, _dir_names, file_names in os.walk(root):
            if cancelled():
                break
            directory = Path(dir_path)
            for file_name in file_names:
                if cancelled():
                    stopped = True
                    break
                path = directory / file_name
                format_info = FORMATS.get(path.suffix.lower())
                if format_info is None:
                    continue
                found.append(_make_geofile(path, root, format_info))
                report(path)
            if stopped:
                break
    else:
        try:
            entries = list(root.iterdir())
        except OSError:
            entries = []

        for path in entries:
            if cancelled():
                break
            if not path.is_file():
                continue
            format_info = FORMATS.get(path.suffix.lower())
            if format_info is None:
                continue
            found.append(_make_geofile(path, root, format_info))
            report(path)

    found.sort(
        key=lambda item: (
            item.relative_posix.casefold(),
            item.path.name.casefold(),
        )
    )
    return found
