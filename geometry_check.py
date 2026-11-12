"""Проверки валидности геометрий и координат векторных слоёв."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMultiPolygon,
    QgsPointXY,
    QgsPolygon,
    QgsProject,
    QgsRectangle,
)

from .check_dialog import CHECK_GEOMETRY_COORDINATES
from .file_info import vector_layers
from .i18n import tr
from .quality_check import QualityIssue, coordinate_problem

MAX_DETAIL_ISSUES = 1000


@dataclass
class _LayerStats:
    """Счётчики проблем одного слоя."""

    name: str
    invalid: int = 0
    self_intersections: int = 0
    unclosed_rings: int = 0
    other_invalid: int = 0
    empty: int = 0
    null: int = 0
    non_finite: int = 0
    huge: int = 0
    out_of_range: int = 0
    swapped: int = 0


@dataclass(frozen=True)
class _CoordinateContext:
    """Параметры проверки координат, общие для всех объектов слоя."""

    geographic: bool
    transform: Optional[QgsCoordinateTransform] = None
    area: Optional[QgsRectangle] = None


def inspect_geometry_and_coordinates(
    geo_file,
    *,
    check_geometry: bool,
    check_coordinates: bool,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить геометрии и координаты всех пространственных слоёв."""

    if not check_geometry and not check_coordinates:
        return [], False

    try:
        layers = vector_layers(geo_file)
    except Exception:
        return [], False

    issues: List[QualityIssue] = []
    applicable = False

    for layer in layers:
        if not layer.isSpatial():
            continue
        applicable = True
        stats = _LayerStats(layer.name())
        coordinate_context = (
            _coordinate_context(layer.crs())
            if check_coordinates
            else None
        )

        try:
            request = QgsFeatureRequest().setNoAttributes()
            detail_budget = MAX_DETAIL_ISSUES
            for feature_index, feature in enumerate(
                layer.getFeatures(request), start=1
            ):
                try:
                    geometry = feature.geometry()
                    feature_id = feature.id()
                    if feature_id is None or feature_id < 0:
                        feature_id = feature_index

                    details: List[QualityIssue] = []
                    if check_geometry:
                        details.extend(
                            _inspect_geometry(
                                geometry,
                                stats,
                                layer.name(),
                                feature_id,
                            )
                        )
                    if coordinate_context is not None:
                        details.extend(
                            _inspect_coordinates(
                                geometry,
                                coordinate_context,
                                stats,
                                layer.name(),
                                feature_id,
                            )
                        )
                    if detail_budget > 0:
                        issues.extend(details[:detail_budget])
                        detail_budget -= min(
                            len(details), detail_budget
                        )
                except Exception:
                    continue
        except Exception:
            continue

        if check_geometry:
            issues.extend(_geometry_issues(stats))
        if check_coordinates:
            issues.extend(_coordinate_issues(stats))

    return issues, applicable


def _detail(
    layer_name: str,
    feature_id: int,
    location: str,
    message: str,
    args: Tuple[object, ...] = (),
) -> QualityIssue:
    return QualityIssue(
        CHECK_GEOMETRY_COORDINATES,
        message,
        args,
        layer=layer_name,
        feature_id=feature_id,
        location=location,
        detail_only=True,
    )


def _inspect_geometry(
    geometry: QgsGeometry,
    stats: _LayerStats,
    layer_name: str,
    feature_id: int,
) -> List[QualityIssue]:
    details: List[QualityIssue] = []

    if geometry.isNull():
        stats.null += 1
        details.append(
            _detail(
                layer_name,
                feature_id,
                "Геометрия",
                "Геометрия отсутствует (null)",
            )
        )
        return details

    if geometry.isEmpty():
        stats.empty += 1
        details.append(
            _detail(
                layer_name,
                feature_id,
                "Геометрия",
                "Пустая геометрия",
            )
        )
        return details

    invalid = _has_unclosed_ring(geometry)
    if invalid:
        stats.unclosed_rings += 1
        details.append(
            _detail(
                layer_name,
                feature_id,
                "Кольцо",
                "Незамкнутое кольцо",
            )
        )

    try:
        if not geometry.isGeosValid():
            invalid = True
            messages = [
                str(error.what())
                for error in geometry.validateGeometry()
            ]
            folded = [message.casefold() for message in messages]
            if any("intersect" in message for message in folded):
                stats.self_intersections += 1
                details.append(
                    _detail(
                        layer_name,
                        feature_id,
                        "Геометрия",
                        "Самопересечение",
                    )
                )
            else:
                stats.other_invalid += 1
                details.append(
                    _detail(
                        layer_name,
                        feature_id,
                        "Геометрия",
                        "Некорректная геометрия: {}",
                        (("; ".join(messages))[:300],),
                    )
                )
    except Exception:
        invalid = True
        stats.other_invalid += 1
        details.append(
            _detail(
                layer_name,
                feature_id,
                "Геометрия",
                "Не удалось проверить геометрию",
            )
        )

    if invalid:
        stats.invalid += 1

    return details


def _has_unclosed_ring(geometry: QgsGeometry) -> bool:
    try:
        collection = geometry.constGet()
    except Exception:
        return False

    polygons: List[QgsPolygon] = []
    if isinstance(collection, QgsPolygon):
        polygons.append(collection)
    elif isinstance(collection, QgsMultiPolygon):
        for index in range(collection.numGeometries()):
            polygon = collection.geometryN(index)
            if isinstance(polygon, QgsPolygon):
                polygons.append(polygon)

    for polygon in polygons:
        rings = []
        exterior = polygon.exteriorRing()
        if exterior is not None:
            rings.append(exterior)
        for index in range(polygon.numInteriorRings()):
            interior = polygon.interiorRing(index)
            if interior is not None:
                rings.append(interior)
        if any(not ring.isClosed() for ring in rings):
            return True

    return False


def _is_projected(crs: QgsCoordinateReferenceSystem) -> bool:
    """Проверить проекционную СК с учётом разных версий QGIS."""

    method = getattr(crs, "isProjected", None)
    if callable(method):
        try:
            return bool(method())
        except Exception:
            pass

    crs_type = getattr(Qgis, "CrsType", None)
    type_method = getattr(crs, "type", None)
    if crs_type is not None and callable(type_method):
        try:
            value = type_method()
            return value in (
                crs_type.Projected,
                crs_type.DerivedProjected,
            )
        except Exception:
            pass

    return crs.isValid() and not crs.isGeographic()


def _coordinate_context(
    crs: QgsCoordinateReferenceSystem,
) -> _CoordinateContext:
    geographic = crs.isValid() and crs.isGeographic()
    transform: Optional[QgsCoordinateTransform] = None
    area = None

    if _is_projected(crs):
        try:
            transform = QgsCoordinateTransform(
                crs,
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )
        except Exception:
            transform = None

        bounds_method = getattr(crs, "bounds", None)
        if bounds_method is not None:
            try:
                candidate = bounds_method()
                if candidate is not None and not candidate.isNull():
                    area = candidate
            except Exception:
                area = None

    return _CoordinateContext(
        geographic=geographic,
        transform=transform,
        area=area,
    )


def _inspect_coordinates(
    geometry: QgsGeometry,
    context: _CoordinateContext,
    stats: _LayerStats,
    layer_name: str,
    feature_id: int,
) -> List[QualityIssue]:
    if geometry.isNull() or geometry.isEmpty():
        return []

    details: List[QualityIssue] = []
    for vertex_index, vertex in enumerate(
        geometry.vertices(), start=1
    ):
        x = vertex.x()
        y = vertex.y()
        problem = coordinate_problem(
            x, y, geographic=context.geographic
        )

        if problem is None and context.transform is not None:
            try:
                point = context.transform.transform(QgsPointXY(x, y))
                problem = coordinate_problem(
                    point.x(), point.y(), geographic=True
                )
                if problem in ("non_finite", "swapped"):
                    problem = "out_of_range"
                if (
                    context.area is not None
                    and problem is None
                    and not context.area.contains(point)
                ):
                    problem = "out_of_range"
            except Exception:
                problem = "out_of_range"

        if problem == "non_finite":
            stats.non_finite += 1
            message = "Координата NaN/Inf"
        elif problem == "huge":
            stats.huge += 1
            message = "Слишком большая координата"
        elif problem == "swapped":
            stats.swapped += 1
            message = "Похоже на перепутанные широту и долготу"
        elif problem == "out_of_range":
            stats.out_of_range += 1
            message = "Координата вне диапазона CRS"
        else:
            continue

        details.append(
            _detail(
                layer_name,
                feature_id,
                tr("Вершина {}", vertex_index),
                message,
            )
        )

    return details


def _geometry_issues(stats: _LayerStats) -> List[QualityIssue]:
    if not (stats.invalid or stats.empty or stats.null):
        return []
    return [
        QualityIssue(
            CHECK_GEOMETRY_COORDINATES,
            "Слой «{}»: некорректных геометрий: {} "
            "(самопересечения: {}, незамкнутые кольца: {}, прочие: {}), "
            "пустых: {}, null-геометрий: {}",
            (
                stats.name,
                stats.invalid,
                stats.self_intersections,
                stats.unclosed_rings,
                stats.other_invalid,
                stats.empty,
                stats.null,
            ),
        )
    ]


def _coordinate_issues(stats: _LayerStats) -> List[QualityIssue]:
    if not (
        stats.non_finite
        or stats.huge
        or stats.out_of_range
        or stats.swapped
    ):
        return []
    return [
        QualityIssue(
            CHECK_GEOMETRY_COORDINATES,
            "Слой «{}»: координаты — NaN/Inf: {}, слишком большие: {}, "
            "вне диапазона CRS: {}, похоже на перепутанные широту и "
            "долготу: {}",
            (
                stats.name,
                stats.non_finite,
                stats.huge,
                stats.out_of_range,
                stats.swapped,
            ),
        )
    ]
