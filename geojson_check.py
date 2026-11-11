"""Проверка JSON-файлов на соответствие спецификации GeoJSON.

Проверка опирается на поле ``type``: в документе должен быть объект с
допустимым типом GeoJSON, а у коллекций — корректные вложенные объекты
(``features``, ``geometries``). Содержимое координат не анализируется.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

GEOMETRY_TYPES = frozenset(
    {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }
)
CONTAINER_TYPES = frozenset(
    {"GeometryCollection", "Feature", "FeatureCollection"}
)
GEOJSON_TYPES = GEOMETRY_TYPES | CONTAINER_TYPES
JSON_EXTENSIONS = frozenset({".json", ".geojson"})


@dataclass(frozen=True)
class GeoJsonCheck:
    """Результат проверки одного JSON-файла."""

    is_geojson: bool
    document_type: str
    error: str


def is_geojson_document(value: object) -> bool:
    """Проверить, что разобранное значение является GeoJSON-объектом."""

    if not isinstance(value, dict):
        return False
    return _is_geojson_object(value)


def _is_geojson_object(value: dict) -> bool:
    document_type = value.get("type")
    if not isinstance(document_type, str):
        return False

    if document_type == "FeatureCollection":
        features = value.get("features")
        return isinstance(features, list) and all(
            _is_feature(feature) for feature in features
        )

    if document_type == "Feature":
        return _is_feature(value)

    if document_type == "GeometryCollection":
        geometries = value.get("geometries")
        return isinstance(geometries, list) and all(
            _is_geometry(geometry) for geometry in geometries
        )

    return _is_geometry(value)


def _is_feature(value: object) -> bool:
    if not isinstance(value, dict) or value.get("type") != "Feature":
        return False

    geometry = value.get("geometry")
    if geometry is not None and not _is_geometry(geometry):
        return False

    properties = value.get("properties")
    if properties is not None and not isinstance(properties, dict):
        return False

    return True


def _is_geometry(value: object) -> bool:
    return isinstance(value, dict) and value.get("type") in GEOMETRY_TYPES


def check_json_file(path: Path) -> GeoJsonCheck:
    """Прочитать файл и определить, является ли он GeoJSON."""

    try:
        with Path(path).open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        reason = str(error) or error.__class__.__name__
        return GeoJsonCheck(False, "", reason)

    if is_geojson_document(data):
        return GeoJsonCheck(True, str(data.get("type", "")), "")

    if not isinstance(data, dict):
        return GeoJsonCheck(False, "", "root value is not a JSON object")
    return GeoJsonCheck(False, "", "type is missing or not a GeoJSON type")
