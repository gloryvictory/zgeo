"""Проверка содержимого GeoJSON.

Проверяются координаты, замкнутость колец, необязательный ``bbox`` и
структура объектов ``Feature``, ``FeatureCollection`` и
``GeometryCollection``. Модуль не зависит от QGIS и возвращает готовые
``QualityIssue`` для колонки «Проблемы» и отчётов.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional, Tuple

from .geojson_check import GEOMETRY_TYPES
from .quality_check import QualityIssue

MAX_GEOJSON_ISSUES = 1000
MAX_GEOJSON_DEPTH = 100


class _IssueCollector:
    """Собирает подробные ошибки и считает их по категориям."""

    def __init__(self, check: str) -> None:
        self._check = check
        self._details: List[QualityIssue] = []
        self._counts = {
            "coordinates": 0,
            "rings": 0,
            "bbox": 0,
            "structure": 0,
        }
        self.total = 0
        self.truncated = False

    def add(
        self,
        category: str,
        message: str,
        args: Tuple[object, ...] = (),
        location: str = "",
        feature_id: Optional[int] = None,
    ) -> None:
        self.total += 1
        self._counts[category] += 1
        if len(self._details) >= MAX_GEOJSON_ISSUES:
            self.truncated = True
            return
        self._details.append(
            QualityIssue(
                check=self._check,
                message=message,
                args=args,
                feature_id=feature_id,
                location=location,
                detail_only=True,
            )
        )

    def finish(self) -> List[QualityIssue]:
        if not self.total:
            return []

        summary = QualityIssue(
            check=self._check,
            message=(
                "Ошибок GeoJSON: {} (координаты: {}, кольца: {}, "
                "bbox: {}, структура: {})"
            ),
            args=(
                self.total,
                self._counts["coordinates"],
                self._counts["rings"],
                self._counts["bbox"],
                self._counts["structure"],
            ),
            location="GeoJSON",
        )
        issues = [summary]
        issues.extend(self._details)
        if self.truncated:
            issues.append(
                QualityIssue(
                    check=self._check,
                    message=(
                        "Дополнительные ошибки не показаны (лимит {})."
                    ),
                    args=(MAX_GEOJSON_ISSUES,),
                    location="GeoJSON",
                    detail_only=True,
                )
            )
        return issues


def _member(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def _index(path: str, index: int) -> str:
    return f"{path}[{index}]"


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite(value: object) -> bool:
    try:
        return math.isfinite(value)
    except OverflowError:
        return True


def _validate_bbox(
    value: dict,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
) -> None:
    if "bbox" not in value:
        return

    bbox = value["bbox"]
    bbox_path = _member(path, "bbox")
    if not isinstance(bbox, list):
        collector.add(
            "bbox",
            "Поле «bbox» должно быть массивом чисел",
            location=bbox_path,
            feature_id=feature_id,
        )
        return
    if len(bbox) not in (4, 6):
        collector.add(
            "bbox",
            "Поле «bbox» должно содержать 4 или 6 чисел",
            location=bbox_path,
            feature_id=feature_id,
        )
        return

    valid = True
    for index, coordinate in enumerate(bbox):
        if not _is_number(coordinate):
            collector.add(
                "bbox",
                "Элемент bbox должен быть числом: {}",
                (repr(coordinate),),
                _index(bbox_path, index),
                feature_id,
            )
            valid = False
        elif not _is_finite(coordinate):
            collector.add(
                "bbox",
                "Элемент bbox не должен быть NaN/Inf",
                location=_index(bbox_path, index),
                feature_id=feature_id,
            )
            valid = False
    if not valid:
        return

    dimensions = len(bbox) // 2
    for axis in range(dimensions):
        minimum = bbox[axis]
        maximum = bbox[axis + dimensions]
        if minimum > maximum:
            collector.add(
                "bbox",
                "bbox: минимум больше максимума по оси {}",
                (axis + 1,),
                bbox_path,
                feature_id,
            )


def _validate_position(
    value: object,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
) -> None:
    if not isinstance(value, list):
        collector.add(
            "coordinates",
            "Позиция должна быть массивом чисел",
            location=path,
            feature_id=feature_id,
        )
        return
    if len(value) < 2:
        collector.add(
            "coordinates",
            "Позиция должна содержать не менее двух чисел",
            location=path,
            feature_id=feature_id,
        )
        return

    valid = True
    for index, coordinate in enumerate(value):
        coordinate_path = _index(path, index)
        if not _is_number(coordinate):
            collector.add(
                "coordinates",
                "Координата должна быть числом: {}",
                (repr(coordinate),),
                coordinate_path,
                feature_id,
            )
            valid = False
        elif not _is_finite(coordinate):
            collector.add(
                "coordinates",
                "Координата NaN/Inf",
                location=coordinate_path,
                feature_id=feature_id,
            )
            valid = False
    if not valid:
        return

    longitude = value[0]
    latitude = value[1]
    if abs(longitude) <= 90 and 90 < abs(latitude) <= 180:
        collector.add(
            "coordinates",
            "Похоже на перепутанные широту и долготу",
            location=f"{path} ({longitude}, {latitude})",
            feature_id=feature_id,
        )
    elif not -180 <= longitude <= 180:
        collector.add(
            "coordinates",
            "Долгота вне диапазона [-180, 180]: {}",
            (longitude,),
            path,
            feature_id,
        )
    elif not -90 <= latitude <= 90:
        collector.add(
            "coordinates",
            "Широта вне диапазона [-90, 90]: {}",
            (latitude,),
            path,
            feature_id,
        )


def _validate_line(
    value: object,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    *,
    minimum: int = 2,
) -> None:
    if not isinstance(value, list):
        collector.add(
            "coordinates",
            "LineString должен быть массивом позиций",
            location=path,
            feature_id=feature_id,
        )
        return
    if len(value) < minimum:
        collector.add(
            "coordinates",
            "LineString должен содержать не менее {} точек",
            (minimum,),
            path,
            feature_id,
        )
    for index, position in enumerate(value):
        _validate_position(
            position,
            collector,
            _index(path, index),
            feature_id,
        )


def _validate_ring(
    value: object,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
) -> None:
    if not isinstance(value, list):
        collector.add(
            "rings",
            "Кольцо должно быть массивом позиций",
            location=path,
            feature_id=feature_id,
        )
        return
    if len(value) < 4:
        collector.add(
            "rings",
            "Кольцо должно содержать не менее 4 точек",
            location=path,
            feature_id=feature_id,
        )
    for index, position in enumerate(value):
        _validate_position(
            position,
            collector,
            _index(path, index),
            feature_id,
        )
    if len(value) >= 2:
        first = value[0]
        last = value[-1]
        if isinstance(first, list) and isinstance(last, list):
            if first != last:
                collector.add(
                    "rings",
                    "Кольцо не замкнуто: первая и последняя точки "
                    "не совпадают",
                    location=path,
                    feature_id=feature_id,
                )


def _validate_coordinates(
    geometry_type: str,
    coordinates: object,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
) -> None:
    if geometry_type == "Point":
        _validate_position(coordinates, collector, path, feature_id)
        return

    if geometry_type in ("MultiPoint", "LineString"):
        if not isinstance(coordinates, list):
            collector.add(
                "coordinates",
                "Поле «coordinates» должно быть массивом",
                location=path,
                feature_id=feature_id,
            )
            return
        if geometry_type == "LineString" and len(coordinates) < 2:
            collector.add(
                "coordinates",
                "LineString должен содержать не менее 2 точек",
                location=path,
                feature_id=feature_id,
            )
        for index, position in enumerate(coordinates):
            _validate_position(
                position,
                collector,
                _index(path, index),
                feature_id,
            )
        return

    if geometry_type == "MultiLineString":
        if not isinstance(coordinates, list):
            collector.add(
                "coordinates",
                "Поле «coordinates» должно быть массивом",
                location=path,
                feature_id=feature_id,
            )
            return
        for index, line in enumerate(coordinates):
            _validate_line(
                line,
                collector,
                _index(path, index),
                feature_id,
            )
        return

    if geometry_type == "Polygon":
        if not isinstance(coordinates, list):
            collector.add(
                "coordinates",
                "Поле «coordinates» должно быть массивом",
                location=path,
                feature_id=feature_id,
            )
            return
        if not coordinates:
            collector.add(
                "rings",
                "Полигон должен содержать хотя бы одно кольцо",
                location=path,
                feature_id=feature_id,
            )
            return
        for index, ring in enumerate(coordinates):
            _validate_ring(
                ring,
                collector,
                _index(path, index),
                feature_id,
            )
        return

    if geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list):
            collector.add(
                "coordinates",
                "Поле «coordinates» должно быть массивом",
                location=path,
                feature_id=feature_id,
            )
            return
        for polygon_index, polygon in enumerate(coordinates):
            polygon_path = _index(path, polygon_index)
            if not isinstance(polygon, list):
                collector.add(
                    "structure",
                    "Полигон в MultiPolygon должен быть массивом колец",
                    location=polygon_path,
                    feature_id=feature_id,
                )
                continue
            if not polygon:
                collector.add(
                    "rings",
                    "Полигон должен содержать хотя бы одно кольцо",
                    location=polygon_path,
                    feature_id=feature_id,
                )
                continue
            for ring_index, ring in enumerate(polygon):
                _validate_ring(
                    ring,
                    collector,
                    _index(polygon_path, ring_index),
                    feature_id,
                )


def _validate_geometry(
    value: dict,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    depth: int,
) -> None:
    if depth > MAX_GEOJSON_DEPTH:
        collector.add(
            "structure",
            "Структура GeoJSON слишком глубокая",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return
    geometry_type = value.get("type")
    if not isinstance(geometry_type, str):
        collector.add(
            "structure",
            "Отсутствует или неверен тип геометрии: {}",
            (repr(geometry_type),),
            _member(path, "type"),
            feature_id,
        )
        return

    if geometry_type == "GeometryCollection":
        _validate_geometry_collection(
            value,
            collector,
            path,
            feature_id,
            depth,
        )
        return

    if geometry_type not in GEOMETRY_TYPES:
        collector.add(
            "structure",
            "Неизвестный тип геометрии: {}",
            (geometry_type,),
            _member(path, "type"),
            feature_id,
        )
        return

    if "coordinates" not in value:
        collector.add(
            "structure",
            "Отсутствует обязательное поле «coordinates»",
            location=_member(path, "coordinates"),
            feature_id=feature_id,
        )
        return
    _validate_coordinates(
        geometry_type,
        value["coordinates"],
        collector,
        _member(path, "coordinates"),
        feature_id,
    )


def _validate_geometry_collection(
    value: dict,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    depth: int,
) -> None:
    if depth > MAX_GEOJSON_DEPTH:
        collector.add(
            "structure",
            "Структура GeoJSON слишком глубокая",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return
    geometry_type = value.get("type")
    if geometry_type != "GeometryCollection":
        collector.add(
            "structure",
            "Тип GeometryCollection должен быть «GeometryCollection»: {}",
            (repr(geometry_type),),
            _member(path, "type"),
            feature_id,
        )
        return

    if "geometries" not in value:
        collector.add(
            "structure",
            "Отсутствует обязательное поле «geometries»",
            location=_member(path, "geometries"),
            feature_id=feature_id,
        )
        return

    geometries = value["geometries"]
    if not isinstance(geometries, list):
        collector.add(
            "structure",
            "Поле «geometries» должно быть массивом",
            location=_member(path, "geometries"),
            feature_id=feature_id,
        )
        return

    for index, geometry in enumerate(geometries):
        geometry_path = _index(_member(path, "geometries"), index)
        if not isinstance(geometry, dict):
            collector.add(
                "structure",
                "Элемент GeometryCollection должен быть объектом "
                "геометрии",
                location=geometry_path,
                feature_id=feature_id,
            )
            continue
        _validate_bbox(geometry, collector, geometry_path, feature_id)
        _validate_geometry(
            geometry,
            collector,
            geometry_path,
            feature_id,
            depth + 1,
        )


def _validate_feature(
    value: dict,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    depth: int,
) -> None:
    if depth > MAX_GEOJSON_DEPTH:
        collector.add(
            "structure",
            "Структура GeoJSON слишком глубокая",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return
    feature_type = value.get("type")
    if feature_type != "Feature":
        collector.add(
            "structure",
            "Тип объекта Feature должен быть «Feature»: {}",
            (repr(feature_type),),
            _member(path, "type"),
            feature_id,
        )
        return

    if "geometry" not in value:
        collector.add(
            "structure",
            "Отсутствует обязательное поле «geometry»",
            location=_member(path, "geometry"),
            feature_id=feature_id,
        )
    else:
        geometry = value["geometry"]
        if geometry is not None:
            if not isinstance(geometry, dict):
                collector.add(
                    "structure",
                    "Поле «geometry» должно быть объектом или null",
                    location=_member(path, "geometry"),
                    feature_id=feature_id,
                )
            else:
                geometry_path = _member(path, "geometry")
                _validate_bbox(
                    geometry,
                    collector,
                    geometry_path,
                    feature_id,
                )
                _validate_geometry(
                    geometry,
                    collector,
                    geometry_path,
                    feature_id,
                    depth + 1,
                )

    if "properties" not in value:
        collector.add(
            "structure",
            "Отсутствует обязательное поле «properties»",
            location=_member(path, "properties"),
            feature_id=feature_id,
        )
    else:
        properties = value["properties"]
        if properties is not None and not isinstance(properties, dict):
            collector.add(
                "structure",
                "Поле «properties» должно быть объектом или null",
                location=_member(path, "properties"),
                feature_id=feature_id,
            )

    if "id" in value:
        identifier = value["id"]
        if isinstance(identifier, bool) or not isinstance(
            identifier, (str, int, float)
        ):
            collector.add(
                "structure",
                "Поле «id» должно быть строкой или числом",
                location=_member(path, "id"),
                feature_id=feature_id,
            )


def _validate_feature_collection(
    value: dict,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    depth: int,
) -> None:
    if depth > MAX_GEOJSON_DEPTH:
        collector.add(
            "structure",
            "Структура GeoJSON слишком глубокая",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return
    if "features" not in value:
        collector.add(
            "structure",
            "Отсутствует обязательное поле «features»",
            location=_member(path, "features"),
            feature_id=feature_id,
        )
        return

    features = value["features"]
    if not isinstance(features, list):
        collector.add(
            "structure",
            "Поле «features» должно быть массивом",
            location=_member(path, "features"),
            feature_id=feature_id,
        )
        return

    for index, feature in enumerate(features):
        feature_path = _index(_member(path, "features"), index)
        if not isinstance(feature, dict):
            collector.add(
                "structure",
                "Элемент FeatureCollection должен быть объектом Feature",
                location=feature_path,
                feature_id=index + 1,
            )
            continue
        _validate_bbox(feature, collector, feature_path, index + 1)
        _validate_feature(
            feature,
            collector,
            feature_path,
            index + 1,
            depth + 1,
        )


def _validate_object(
    value: object,
    collector: _IssueCollector,
    path: str,
    feature_id: Optional[int],
    depth: int,
) -> None:
    if depth > MAX_GEOJSON_DEPTH:
        collector.add(
            "structure",
            "Структура GeoJSON слишком глубокая",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return
    if not isinstance(value, dict):
        collector.add(
            "structure",
            "Корень GeoJSON должен быть объектом",
            location=path or "GeoJSON",
            feature_id=feature_id,
        )
        return

    _validate_bbox(value, collector, path, feature_id)
    document_type = value.get("type")
    if not isinstance(document_type, str):
        collector.add(
            "structure",
            "Отсутствует или неверен тип GeoJSON: {}",
            (repr(document_type),),
            _member(path, "type"),
            feature_id,
        )
        return

    if document_type == "FeatureCollection":
        _validate_feature_collection(
            value,
            collector,
            path,
            feature_id,
            depth,
        )
    elif document_type == "Feature":
        _validate_feature(value, collector, path, feature_id, depth)
    elif document_type == "GeometryCollection":
        _validate_geometry_collection(
            value,
            collector,
            path,
            feature_id,
            depth,
        )
    elif document_type in GEOMETRY_TYPES:
        _validate_geometry(value, collector, path, feature_id, depth)
    else:
        collector.add(
            "structure",
            "Неизвестный тип GeoJSON: {}",
            (document_type,),
            _member(path, "type"),
            feature_id,
        )


def validate_geojson_document(
    document: object, check: str
) -> List[QualityIssue]:
    """Проверить разобранный GeoJSON-документ."""

    collector = _IssueCollector(check)
    _validate_object(document, collector, "", None, 0)
    return collector.finish()


def validate_geojson_file(path: Path, check: str) -> List[QualityIssue]:
    """Прочитать и проверить файл GeoJSON."""

    try:
        with Path(path).open("r", encoding="utf-8-sig") as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        reason = str(error) or error.__class__.__name__
        return [
            QualityIssue(
                check=check,
                message="Не удалось прочитать GeoJSON: {}",
                args=(reason,),
                location="Файл",
            )
        ]

    try:
        return validate_geojson_document(document, check)
    except (RecursionError, TypeError, ValueError) as error:
        reason = str(error) or error.__class__.__name__
        return [
            QualityIssue(
                check=check,
                message="Не удалось проверить GeoJSON: {}",
                args=(reason,),
                location="GeoJSON",
            )
        ]
