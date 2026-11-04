"""Получение подробной информации о пространственном файле."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .scanner import OTHER, RASTER, TABLE, VECTOR, GeoFile


@dataclass(frozen=True)
class FieldInfo:
    name: str
    alias: str
    type_name: str
    length: int
    precision: int
    comment: str


@dataclass(frozen=True)
class VectorLayerInfo:
    name: str
    uri: str
    crs: str
    feature_count: int
    geometry: str
    extent: str
    provider: str
    fields: Tuple[FieldInfo, ...]


@dataclass(frozen=True)
class RasterLayerInfo:
    name: str
    uri: str
    crs: str
    width: int
    height: int
    band_count: int
    extent: str
    pixel_size: str
    provider: str


@dataclass(frozen=True)
class FileInfo:
    path: Path
    format_name: str
    size: int
    vector_layers: Tuple[VectorLayerInfo, ...]
    raster_layers: Tuple[RasterLayerInfo, ...]
    notes: Tuple[str, ...] = ()


def inspect_geofile(geo_file: GeoFile) -> FileInfo:
    """Открыть файл через провайдеры QGIS и собрать сведения о слоях."""

    path = geo_file.path
    vector_layers: List[VectorLayerInfo] = []
    raster_layers: List[RasterLayerInfo] = []
    notes: List[str] = []

    try:
        vector_layers.extend(_inspect_vector_layers(geo_file))
    except Exception as error:
        notes.append("Векторные данные: {}".format(error))

    if _should_inspect_raster(geo_file, vector_layers):
        try:
            raster_layers.extend(_inspect_raster_layers(geo_file))
        except Exception as error:
            notes.append("Растровые данные: {}".format(error))

    if not vector_layers and not raster_layers:
        notes.append(
            "QGIS не смог определить пространственные слои в этом файле."
        )

    return FileInfo(
        path=path,
        format_name=geo_file.format.name,
        size=geo_file.size,
        vector_layers=tuple(vector_layers),
        raster_layers=tuple(raster_layers),
        notes=tuple(notes),
    )


def _inspect_vector_layers(geo_file: GeoFile) -> List[VectorLayerInfo]:
    path = geo_file.path
    layers: List[VectorLayerInfo] = []
    seen_uris = set()

    for details in _query_sublayers("ogr", path):
        if details.type() != Qgis.LayerType.Vector:
            continue
        provider = details.providerKey() or "ogr"
        layer = QgsVectorLayer(details.uri(), details.name(), provider)
        if not layer.isValid():
            continue
        info = _vector_layer_info(layer)
        if info.uri not in seen_uris:
            seen_uris.add(info.uri)
            layers.append(info)

    if not layers and geo_file.category in (VECTOR, TABLE, OTHER):
        layer = QgsVectorLayer(str(path), path.stem, "ogr")
        if layer.isValid():
            layers.append(_vector_layer_info(layer))

    return layers


def _inspect_raster_layers(geo_file: GeoFile) -> List[RasterLayerInfo]:
    path = geo_file.path
    layers: List[RasterLayerInfo] = []
    seen_uris = set()

    for details in _query_sublayers("gdal", path):
        if details.type() != Qgis.LayerType.Raster:
            continue
        provider = details.providerKey() or "gdal"
        layer = QgsRasterLayer(details.uri(), details.name(), provider)
        if not layer.isValid():
            continue
        info = _raster_layer_info(layer)
        if info.uri not in seen_uris:
            seen_uris.add(info.uri)
            layers.append(info)

    if not layers and geo_file.category == RASTER:
        layer = QgsRasterLayer(str(path), path.stem, "gdal")
        if layer.isValid():
            layers.append(_raster_layer_info(layer))

    return layers


def _query_sublayers(provider: str, path: Path):
    registry = QgsProviderRegistry.instance()
    metadata = registry.providerMetadata(provider)
    if metadata is None:
        return []
    return list(metadata.querySublayers(str(path)))


def _should_inspect_raster(
    geo_file: GeoFile, vector_layers: List[VectorLayerInfo]
) -> bool:
    if geo_file.category == RASTER:
        return True
    if geo_file.category == OTHER:
        return True
    if geo_file.extension == ".gpkg":
        return True
    return not vector_layers and geo_file.category != TABLE


def _vector_layer_info(layer: QgsVectorLayer) -> VectorLayerInfo:
    fields = tuple(_field_info(field) for field in layer.fields())
    return VectorLayerInfo(
        name=layer.name(),
        uri=layer.source(),
        crs=_crs_text(layer),
        feature_count=layer.featureCount(),
        geometry=_geometry_text(layer),
        extent=_extent_text(layer.extent()),
        provider=layer.providerType(),
        fields=fields,
    )


def _raster_layer_info(layer: QgsRasterLayer) -> RasterLayerInfo:
    pixel_x = layer.rasterUnitsPerPixelX()
    pixel_y = layer.rasterUnitsPerPixelY()
    if abs(pixel_x - pixel_y) < 1e-12:
        pixel_size = "{:g}".format(pixel_x)
    else:
        pixel_size = "{:g} × {:g}".format(pixel_x, pixel_y)

    return RasterLayerInfo(
        name=layer.name(),
        uri=layer.source(),
        crs=_crs_text(layer),
        width=layer.width(),
        height=layer.height(),
        band_count=layer.bandCount(),
        extent=_extent_text(layer.extent()),
        pixel_size=pixel_size,
        provider=layer.providerType(),
    )


def _field_info(field) -> FieldInfo:
    return FieldInfo(
        name=field.name(),
        alias=field.alias(),
        type_name=field.typeName(),
        length=field.length(),
        precision=field.precision(),
        comment=field.comment(),
    )


def _crs_text(layer) -> str:
    crs = layer.crs()
    if crs is None or not crs.isValid():
        return "Не определена"
    authid = crs.authid()
    description = crs.description()
    if authid and description:
        return "{} — {}".format(authid, description)
    return authid or description or "Не определена"


def _geometry_text(layer: QgsVectorLayer) -> str:
    try:
        return QgsWkbTypes.displayString(layer.wkbType()) or "Без геометрии"
    except (TypeError, AttributeError):
        return "Не определена"


def _extent_text(extent) -> str:
    try:
        if extent.isNull():
            return "—"
        return "{:.6f}, {:.6f} — {:.6f}, {:.6f}".format(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMaximum(),
            extent.yMaximum(),
        )
    except (AttributeError, TypeError):
        return "—"
