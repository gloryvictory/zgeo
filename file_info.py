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

from .attribute_check import has_non_latin_characters
from .i18n import tr
from .scanner import OTHER, RASTER, TABLE, VECTOR, GeoFile

_LAYER_TYPE = getattr(Qgis, "LayerType", None)
_VECTOR_LAYER_TYPE = getattr(_LAYER_TYPE, "Vector", 0)
_RASTER_LAYER_TYPE = getattr(_LAYER_TYPE, "Raster", 1)


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


@dataclass(frozen=True)
class LayerSummary:
    """Краткие сведения для таблицы списка файлов."""

    crs: str
    element_count: Optional[int]


@dataclass(frozen=True)
class AttributeCheck:
    """Результат проверки имён полей векторных слоёв файла."""

    field_names: Tuple[str, ...]
    non_latin_names: Tuple[str, ...]

    @property
    def has_issues(self) -> bool:
        return bool(self.non_latin_names)


def inspect_geofile(geo_file: GeoFile) -> FileInfo:
    """Открыть файл через провайдеры QGIS и собрать сведения о слоях."""

    path = geo_file.path
    vector_layers: List[VectorLayerInfo] = []
    raster_layers: List[RasterLayerInfo] = []
    notes: List[str] = []

    try:
        vector_layers.extend(_inspect_vector_layers(geo_file))
    except Exception as error:
        notes.append(tr("Векторные данные: {}", error))

    if _should_inspect_raster(geo_file, vector_layers):
        try:
            raster_layers.extend(_inspect_raster_layers(geo_file))
        except Exception as error:
            notes.append(tr("Растровые данные: {}", error))

    return FileInfo(
        path=path,
        format_name=geo_file.format.name,
        size=geo_file.size,
        vector_layers=tuple(vector_layers),
        raster_layers=tuple(raster_layers),
        notes=tuple(notes),
    )


def inspect_layer_summary(geo_file: GeoFile) -> LayerSummary:
    """Получить систему координат и число элементов без чтения полей."""

    try:
        vector_summaries = _vector_layer_summaries(geo_file)
    except Exception:
        vector_summaries = []

    if vector_summaries:
        return LayerSummary(
            crs=_summarize_crs(
                [crs for crs, _count in vector_summaries]
            ),
            element_count=_summarize_count(
                [count for _crs, count in vector_summaries]
            ),
        )

    try:
        if not _should_inspect_raster(geo_file, []):
            return LayerSummary("—", None)
        raster_layers = _inspect_raster_layers(geo_file)
    except Exception:
        raster_layers = []

    if not raster_layers:
        return LayerSummary("—", None)

    return LayerSummary(
        crs=_summarize_crs([layer.crs for layer in raster_layers]),
        element_count=None,
    )


def inspect_attribute_names(geo_file: GeoFile) -> AttributeCheck:
    """Проверить имена полей всех векторных слоёв файла."""

    field_names = _vector_field_names(geo_file)
    non_latin_names = tuple(
        name
        for name in field_names
        if has_non_latin_characters(name)
    )
    return AttributeCheck(
        field_names=field_names,
        non_latin_names=non_latin_names,
    )


def _vector_field_names(geo_file: GeoFile) -> Tuple[str, ...]:
    path = geo_file.path
    names: List[str] = []
    seen_names = set()
    seen_uris = set()

    for details in _query_sublayers("ogr", path):
        if details.type() != _VECTOR_LAYER_TYPE:
            continue
        provider = details.providerKey() or "ogr"
        layer = QgsVectorLayer(details.uri(), details.name(), provider)
        if not layer.isValid():
            continue
        uri = layer.source()
        if uri in seen_uris:
            continue
        seen_uris.add(uri)
        for field in layer.fields():
            name = field.name()
            if name and name not in seen_names:
                seen_names.add(name)
                names.append(name)

    if not names and geo_file.category in (VECTOR, TABLE, OTHER):
        layer = QgsVectorLayer(str(path), path.stem, "ogr")
        if layer.isValid():
            for field in layer.fields():
                name = field.name()
                if name and name not in seen_names:
                    seen_names.add(name)
                    names.append(name)

    return tuple(names)


def _vector_layer_summaries(
    geo_file: GeoFile,
) -> List[Tuple[str, int]]:
    path = geo_file.path
    summaries: List[Tuple[str, int]] = []
    seen_uris = set()

    for details in _query_sublayers("ogr", path):
        if details.type() != _VECTOR_LAYER_TYPE:
            continue
        provider = details.providerKey() or "ogr"
        layer = QgsVectorLayer(details.uri(), details.name(), provider)
        if not layer.isValid():
            continue
        uri = layer.source()
        if uri in seen_uris:
            continue
        seen_uris.add(uri)
        summaries.append((_crs_text(layer), layer.featureCount()))

    if not summaries and geo_file.category in (VECTOR, TABLE, OTHER):
        layer = QgsVectorLayer(str(path), path.stem, "ogr")
        if layer.isValid():
            summaries.append((_crs_text(layer), layer.featureCount()))

    return summaries


def _summarize_crs(values: List[str]) -> str:
    unique = {value for value in values if value}
    if not unique:
        return "—"
    if len(unique) == 1:
        return next(iter(unique))
    return tr("Разные")


def _summarize_count(values: List[int]) -> Optional[int]:
    if not values or any(value < 0 for value in values):
        return None
    return sum(values)


def _inspect_vector_layers(geo_file: GeoFile) -> List[VectorLayerInfo]:
    path = geo_file.path
    layers: List[VectorLayerInfo] = []
    seen_uris = set()

    for details in _query_sublayers("ogr", path):
        if details.type() != _VECTOR_LAYER_TYPE:
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
        if details.type() != _RASTER_LAYER_TYPE:
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
    try:
        registry = QgsProviderRegistry.instance()
        metadata = registry.providerMetadata(provider)
        if metadata is None:
            return []
        query = getattr(metadata, "querySublayers", None)
        if query is None:
            return []
        return list(query(str(path)))
    except Exception:
        return []


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
        return tr("Не определена")
    authid = crs.authid()
    description = crs.description()
    if authid and description:
        return "{} — {}".format(authid, description)
    return authid or description or tr("Не определена")


def _geometry_text(layer: QgsVectorLayer) -> str:
    if not layer.isSpatial():
        return tr("Без геометрии")
    try:
        return QgsWkbTypes.displayString(layer.wkbType()) or tr(
            "Не определена"
        )
    except (TypeError, AttributeError):
        return tr("Не определена")


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
