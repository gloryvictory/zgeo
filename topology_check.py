"""Проверки топологии полигонов и линий."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from qgis.core import (
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsSpatialIndex,
    QgsWkbTypes,
)

from .check_dialog import CHECK_TOPOLOGY
from .file_info import vector_layers
from .quality_check import (
    QualityIssue,
    TopologyStats,
    topology_summary_issues,
)

MAX_DETAIL_ISSUES = 1000
MAX_ID_LIST = 8

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Entry:
    """Объект слоя, участвующий в топологической проверке."""

    key: int
    feature_id: int
    geometry: QgsGeometry
    parts: Tuple[Tuple[QgsPointXY, ...], ...] = ()
    endpoints: Tuple[Tuple[QgsPointXY, int], ...] = ()


def inspect_topology(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить наложения, разрывы, висячие линии и пересечения."""

    try:
        layers = vector_layers(geo_file)
    except Exception:
        return [], False

    issues: List[QualityIssue] = []
    applicable = False

    for layer in layers:
        if not layer.isSpatial():
            continue

        try:
            layer_geometry_type = QgsWkbTypes.geometryType(
                layer.wkbType()
            )
        except Exception:
            layer_geometry_type = None
        if layer_geometry_type in (
            QgsWkbTypes.PolygonGeometry,
            QgsWkbTypes.LineGeometry,
        ):
            applicable = True

        tolerance = _layer_tolerance(layer)
        polygons, lines = _collect_entries(layer, tolerance)
        if not polygons and not lines:
            continue

        applicable = True
        details: List[QualityIssue] = []
        stats = TopologyStats(layer.name())

        if polygons:
            polygon_index = _build_index(polygons)
            polygon_by_key = {entry.key: entry for entry in polygons}
            _polygon_overlaps(
                polygons,
                polygon_index,
                polygon_by_key,
                stats,
                details,
            )
            _polygon_gaps(
                polygons,
                polygon_index,
                polygon_by_key,
                stats,
                details,
            )

        if lines:
            line_index = _build_index(lines)
            line_by_key = {entry.key: entry for entry in lines}
            _dangling_lines(
                lines,
                line_index,
                line_by_key,
                stats,
                details,
                tolerance,
            )
            _line_intersections(
                lines,
                line_index,
                line_by_key,
                stats,
                details,
                tolerance,
            )

        issues.extend(details)
        issues.extend(topology_summary_issues(stats))

    return issues, applicable


def _layer_tolerance(layer) -> float:
    """Допуск для совпадения концов линий в единицах CRS слоя."""

    try:
        extent = layer.extent()
        span = max(extent.width(), extent.height(), 1.0)
    except Exception:
        span = 1.0
    return span * 1e-8


def _collect_entries(
    layer, tolerance: float
) -> Tuple[List[_Entry], List[_Entry]]:
    polygons: List[_Entry] = []
    lines: List[_Entry] = []

    try:
        request = QgsFeatureRequest().setNoAttributes()
        for index, feature in enumerate(
            layer.getFeatures(request), start=1
        ):
            try:
                geometry = feature.geometry()
                if (
                    geometry is None
                    or geometry.isNull()
                    or geometry.isEmpty()
                    or not geometry.isGeosValid()
                ):
                    continue

                geometry_type = QgsWkbTypes.geometryType(
                    geometry.wkbType()
                )
                if geometry_type not in (
                    QgsWkbTypes.PolygonGeometry,
                    QgsWkbTypes.LineGeometry,
                ):
                    continue

                feature_id = feature.id()
                if feature_id is None or feature_id < 0:
                    feature_id = index

                if geometry_type == QgsWkbTypes.PolygonGeometry:
                    polygons.append(
                        _Entry(index, feature_id, geometry)
                    )
                    continue

                parts = tuple(
                    tuple(part)
                    for part in _line_parts(geometry)
                    if len(part) >= 2
                )
                if not parts:
                    continue
                lines.append(
                    _Entry(
                        index,
                        feature_id,
                        geometry,
                        parts,
                        _line_endpoints(parts, tolerance),
                    )
                )
            except Exception:
                _LOGGER.debug(
                    "Skipping feature while collecting topology entries",
                    exc_info=True,
                )
                continue
    except Exception:
        _LOGGER.debug(
            "Skipping layer %s while collecting topology entries",
            layer.name(),
            exc_info=True,
        )

    return polygons, lines


def _line_parts(
    geometry: QgsGeometry,
) -> List[Tuple[QgsPointXY, ...]]:
    try:
        if geometry.isMultipart():
            return [
                tuple(part) for part in geometry.asMultiPolyline()
            ]
        return [tuple(geometry.asPolyline())]
    except Exception:
        return []


def _line_endpoints(
    parts: Sequence[Sequence[QgsPointXY]], tolerance: float
) -> Tuple[Tuple[QgsPointXY, int], ...]:
    endpoints: List[Tuple[QgsPointXY, int]] = []
    for part_index, part in enumerate(parts):
        if len(part) < 2:
            continue
        if _points_close(part[0], part[-1], tolerance):
            continue
        endpoints.append((part[0], part_index))
        endpoints.append((part[-1], part_index))
    return tuple(endpoints)


def _points_close(
    first: QgsPointXY, second: QgsPointXY, tolerance: float
) -> bool:
    return (
        abs(first.x() - second.x()) <= tolerance
        and abs(first.y() - second.y()) <= tolerance
    )


def _build_index(entries: Sequence[_Entry]) -> QgsSpatialIndex:
    index = QgsSpatialIndex()
    for entry in entries:
        try:
            index.insertFeature(
                entry.key, entry.geometry.boundingBox()
            )
        except Exception:
            _LOGGER.debug(
                "Could not add feature %s to the spatial index",
                entry.feature_id,
                exc_info=True,
            )
            continue
    return index


def _polygon_overlaps(
    polygons: Sequence[_Entry],
    index: QgsSpatialIndex,
    by_key: Dict[int, _Entry],
    stats: TopologyStats,
    details: List[QualityIssue],
) -> None:
    for entry in polygons:
        try:
            candidates = index.intersects(entry.geometry.boundingBox())
        except Exception:
            _LOGGER.debug(
                "Could not query the spatial index for polygon %s",
                entry.feature_id,
                exc_info=True,
            )
            continue
        for key in candidates:
            if key <= entry.key:
                continue
            other = by_key.get(key)
            if other is None:
                continue
            try:
                if not entry.geometry.intersects(other.geometry):
                    continue
                overlap = entry.geometry.intersection(other.geometry)
                if overlap.isNull() or overlap.isEmpty():
                    continue
                area = overlap.area()
            except Exception:
                _LOGGER.debug(
                    "Could not compare polygons %s and %s",
                    entry.feature_id,
                    other.feature_id,
                    exc_info=True,
                )
                continue
            if area <= 0:
                continue

            stats.polygon_overlaps += 1
            if len(details) >= MAX_DETAIL_ISSUES:
                continue
            details.append(
                QualityIssue(
                    CHECK_TOPOLOGY,
                    "Наложение полигонов: объект {} и объект {} — "
                    "площадь {}",
                    (
                        entry.feature_id,
                        other.feature_id,
                        _format_number(area),
                    ),
                    layer=stats.layer,
                    location="Полигон",
                    detail_only=True,
                )
            )


def _polygon_gaps(
    polygons: Sequence[_Entry],
    index: QgsSpatialIndex,
    by_key: Dict[int, _Entry],
    stats: TopologyStats,
    details: List[QualityIssue],
) -> None:
    if len(polygons) < 2:
        return

    union = _union_polygons(polygons)
    if union is None:
        return

    for ring in _interior_rings(union):
        if len(ring) < 3:
            continue
        try:
            gap = QgsGeometry.fromPolygonXY([ring])
            if gap.isNull() or gap.isEmpty():
                continue
            area = gap.area()
            if area <= 0:
                continue
            boundary = QgsGeometry.fromPolylineXY(ring)
            owners: Set[int] = set()
            for key in index.intersects(gap.boundingBox()):
                other = by_key.get(key)
                if other is None:
                    continue
                try:
                    if other.geometry.intersects(boundary):
                        owners.add(other.feature_id)
                except Exception:
                    _LOGGER.debug(
                        "Could not test the gap boundary against feature %s",
                        other.feature_id,
                        exc_info=True,
                    )
                    continue
            if len(owners) < 2:
                continue
        except Exception:
            _LOGGER.debug(
                "Skipping an invalid polygon gap candidate",
                exc_info=True,
            )
            continue

        stats.polygon_gaps += 1
        if len(details) >= MAX_DETAIL_ISSUES:
            continue
        centroid = gap.centroid().asPoint()
        details.append(
            QualityIssue(
                CHECK_TOPOLOGY,
                "Разрыв полигонов: площадь {} — окружён объектами: {}",
                (_format_number(area), _format_ids(owners)),
                layer=stats.layer,
                location=(
                    "Разрыв "
                    f"({centroid.x():.6g}, {centroid.y():.6g})"
                ),
                detail_only=True,
            )
        )


def _union_polygons(
    polygons: Sequence[_Entry],
) -> Optional[QgsGeometry]:
    geometries = [entry.geometry for entry in polygons]
    try:
        union = QgsGeometry.unaryUnion(geometries)
        if union is not None and not union.isNull() and not union.isEmpty():
            return union
    except Exception:
        _LOGGER.debug(
            "Unary union failed; trying pairwise union", exc_info=True
        )

    try:
        union = polygons[0].geometry
        for entry in polygons[1:]:
            union = union.combine(entry.geometry)
        if not union.isNull() and not union.isEmpty():
            return union
    except Exception:
        _LOGGER.debug("Pairwise polygon union failed", exc_info=True)
    return None


def _interior_rings(
    geometry: QgsGeometry,
) -> List[List[QgsPointXY]]:
    try:
        if geometry.isMultipart():
            polygons = geometry.asMultiPolygon()
        else:
            polygons = [geometry.asPolygon()]
    except Exception:
        return []

    rings: List[List[QgsPointXY]] = []
    for polygon in polygons:
        if not polygon:
            continue
        for ring in polygon[1:]:
            if ring:
                rings.append(list(ring))
    return rings


def _dangling_lines(
    lines: Sequence[_Entry],
    index: QgsSpatialIndex,
    by_key: Dict[int, _Entry],
    stats: TopologyStats,
    details: List[QualityIssue],
    tolerance: float,
) -> None:
    endpoint_counts: Dict[Tuple[int, int], int] = {}
    for entry in lines:
        for point, _part_index in entry.endpoints:
            key = _point_key(point, tolerance)
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1

    for entry in lines:
        free: List[QgsPointXY] = []
        for point, part_index in entry.endpoints:
            key = _point_key(point, tolerance)
            if endpoint_counts.get(key, 0) > 1:
                continue
            if _endpoint_connected(
                point,
                entry,
                part_index,
                index,
                by_key,
                tolerance,
            ):
                continue
            free.append(point)

        if not free:
            continue

        stats.dangling_lines += 1
        stats.free_ends += len(free)
        if len(details) >= MAX_DETAIL_ISSUES:
            continue
        first = free[0]
        details.append(
            QualityIssue(
                CHECK_TOPOLOGY,
                "Висячая линия: объект {} — свободных концов: {}",
                (entry.feature_id, len(free)),
                layer=stats.layer,
                location=(
                    "Конец линии "
                    f"({first.x():.6g}, {first.y():.6g})"
                ),
                detail_only=True,
            )
        )


def _endpoint_connected(
    point: QgsPointXY,
    owner: _Entry,
    owner_part: int,
    index: QgsSpatialIndex,
    by_key: Dict[int, _Entry],
    tolerance: float,
) -> bool:
    point_geometry = QgsGeometry.fromPointXY(point)
    rectangle = QgsRectangle(
        point.x() - tolerance,
        point.y() - tolerance,
        point.x() + tolerance,
        point.y() + tolerance,
    )
    try:
        candidates = index.intersects(rectangle)
    except Exception:
        return False

    for key in candidates:
        candidate = by_key.get(key)
        if candidate is None:
            continue
        if candidate.key == owner.key:
            for part_index, part in enumerate(candidate.parts):
                if part_index == owner_part or len(part) < 2:
                    continue
                try:
                    part_geometry = QgsGeometry.fromPolylineXY(
                        list(part)
                    )
                    if (
                        part_geometry.distance(point_geometry)
                        <= tolerance
                    ):
                        return True
                except Exception:
                    _LOGGER.debug(
                        "Could not compare line parts for feature %s",
                        candidate.feature_id,
                        exc_info=True,
                    )
                    continue
            continue

        try:
            if candidate.geometry.distance(point_geometry) <= tolerance:
                return True
        except Exception:
            _LOGGER.debug(
                "Could not compare line feature %s",
                candidate.feature_id,
                exc_info=True,
            )
            continue

    return False


def _line_intersections(
    lines: Sequence[_Entry],
    index: QgsSpatialIndex,
    by_key: Dict[int, _Entry],
    stats: TopologyStats,
    details: List[QualityIssue],
    tolerance: float,
) -> None:
    for entry in lines:
        try:
            candidates = index.intersects(entry.geometry.boundingBox())
        except Exception:
            _LOGGER.debug(
                "Could not query the spatial index for line %s",
                entry.feature_id,
                exc_info=True,
            )
            continue
        for key in candidates:
            if key <= entry.key:
                continue
            other = by_key.get(key)
            if other is None:
                continue
            try:
                if not entry.geometry.intersects(other.geometry):
                    continue
                intersection = entry.geometry.intersection(
                    other.geometry
                )
            except Exception:
                _LOGGER.debug(
                    "Could not intersect lines %s and %s",
                    entry.feature_id,
                    other.feature_id,
                    exc_info=True,
                )
                continue
            if (
                intersection is None
                or intersection.isNull()
                or intersection.isEmpty()
            ):
                continue

            has_line, points = _intersection_parts(intersection)
            if has_line:
                stats.line_overlaps += 1
                if len(details) < MAX_DETAIL_ISSUES:
                    details.append(
                        QualityIssue(
                            CHECK_TOPOLOGY,
                            "Наложение линий: объект {} и объект {} — "
                            "длина {}",
                            (
                                entry.feature_id,
                                other.feature_id,
                                _format_number(
                                    intersection.length()
                                ),
                            ),
                            layer=stats.layer,
                            location="Наложение",
                            detail_only=True,
                        )
                    )
                continue

            crossing = [
                point
                for point in points
                if not _point_is_endpoint(point, entry, tolerance)
                and not _point_is_endpoint(point, other, tolerance)
            ]
            if not crossing:
                continue

            stats.line_intersections += 1
            if len(details) >= MAX_DETAIL_ISSUES:
                continue
            details.append(
                QualityIssue(
                    CHECK_TOPOLOGY,
                    "Пересечение линий: объект {} и объект {}",
                    (entry.feature_id, other.feature_id),
                    layer=stats.layer,
                    location="Пересечение",
                    detail_only=True,
                )
            )


def _intersection_parts(
    geometry: QgsGeometry,
) -> Tuple[bool, List[QgsPointXY]]:
    try:
        if geometry.isMultipart():
            return False, list(geometry.asMultiPoint())
        return False, [geometry.asPoint()]
    except Exception:
        return True, []


def _point_is_endpoint(
    point: QgsPointXY, entry: _Entry, tolerance: float
) -> bool:
    return any(
        _distance(point, endpoint) <= tolerance
        for endpoint, _part_index in entry.endpoints
    )


def _distance(first: QgsPointXY, second: QgsPointXY) -> float:
    dx = first.x() - second.x()
    dy = first.y() - second.y()
    return (dx * dx + dy * dy) ** 0.5


def _point_key(
    point: QgsPointXY, tolerance: float
) -> Tuple[int, int]:
    if tolerance <= 0:
        return (round(point.x(), 12), round(point.y(), 12))
    return (
        round(point.x() / tolerance),
        round(point.y() / tolerance),
    )


def _format_number(value: float) -> str:
    return f"{value:.6g}"


def _format_ids(ids: Iterable[int]) -> str:
    values = sorted(ids)
    if len(values) > MAX_ID_LIST:
        return (
            ", ".join(str(value) for value in values[:MAX_ID_LIST])
            + ", …"
        )
    return ", ".join(str(value) for value in values)
