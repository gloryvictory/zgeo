"""Загрузка найденных файлов слоями в текущий проект QGIS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from qgis.core import QgsProject, QgsRasterLayer

from .file_info import vector_layers
from .scanner import RASTER


@dataclass(frozen=True)
class LoadResult:
    """Итог загрузки выбранных файлов в проект."""

    added: int = 0
    skipped: int = 0
    errors: Tuple[str, ...] = ()

    @property
    def loaded_names(self) -> int:
        return self.added


def load_files_into_project(
    geo_files: Iterable,
) -> LoadResult:
    """Добавить слои выбранных файлов в текущий проект QGIS.

    Файлы-контейнеры (GeoPackage, MapInfo TAB, SpatiaLite) загружаются
    всеми слоями. Слои, которые уже есть в проекте с тем же источником,
    повторно не добавляются. Ошибки открытия собираются в списке и не
    прерывают загрузку остальных файлов.
    """

    project = QgsProject.instance()
    if project is None:
        return LoadResult(errors=())

    existing = {
        _normalized_source(layer.source())
        for layer in project.mapLayers().values()
    }

    added = 0
    skipped = 0
    errors: List[str] = []

    for geo_file in geo_files:
        try:
            layers = _file_layers(geo_file)
        except Exception as error:
            errors.append("{}: {}".format(geo_file.path.name, error))
            continue

        if not layers:
            errors.append(geo_file.path.name)
            continue

        for layer in layers:
            source = _normalized_source(layer.source())
            if source in existing:
                skipped += 1
                continue
            if not layer.isValid():
                errors.append("{}: {}".format(geo_file.path.name, layer.name()))
                continue
            if project.addMapLayer(layer, True) is None:
                errors.append("{}: {}".format(geo_file.path.name, layer.name()))
                continue
            existing.add(source)
            added += 1

    return LoadResult(added=added, skipped=skipped, errors=tuple(errors))


def _file_layers(geo_file) -> List:
    """Собрать слои одного файла: векторные или растровые."""

    if geo_file.category == RASTER:
        layer = QgsRasterLayer(
            str(geo_file.path), geo_file.path.stem, "gdal"
        )
        return [layer] if layer.isValid() else []

    return list(vector_layers(geo_file))


def _normalized_source(source: str) -> str:
    """Привести источник слоя к сравнимому виду."""

    return " ".join(str(source).split()).casefold()
