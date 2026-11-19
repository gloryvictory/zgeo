"""Проверка читаемости пространственных файлов через провайдеры QGIS."""

from __future__ import annotations

from typing import List, Tuple

from .quality_check import (
    QualityIssue,
    ReadabilityProblem,
    readability_issues,
)


def inspect_readability(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить, что файл и его слои открываются и читаются."""

    from .check_dialog import CHECK_READABILITY
    from .file_info import raster_layers, vector_layers
    from .scanner import OTHER, RASTER

    path = geo_file.path
    if not path.exists():
        return _issues(
            [ReadabilityProblem("file_missing")], CHECK_READABILITY
        ), True

    try:
        size = path.stat().st_size
    except OSError:
        return _issues(
            [ReadabilityProblem("file_missing")], CHECK_READABILITY
        ), True

    if size <= 0:
        return _issues(
            [ReadabilityProblem("empty_file")], CHECK_READABILITY
        ), True

    problems: List[ReadabilityProblem] = []
    vector: List[object] = []
    raster: List[object] = []
    open_errors: List[str] = []

    if geo_file.category != RASTER:
        try:
            vector = list(vector_layers(geo_file))
        except Exception as error:
            open_errors.append(_error_text(error))

    if geo_file.category in (RASTER, OTHER):
        try:
            raster = list(raster_layers(geo_file))
        except Exception as error:
            open_errors.append(_error_text(error))

    if not vector and not raster:
        if open_errors:
            problems.append(
                ReadabilityProblem(
                    "open",
                    detail="; ".join(open_errors),
                )
            )
        else:
            problems.append(ReadabilityProblem("no_layers"))

    for layer in vector:
        error = _read_vector_layer(layer)
        if error:
            problems.append(
                ReadabilityProblem(
                    "vector_read",
                    layer=layer.name(),
                    detail=error,
                )
            )

    for layer in raster:
        error = _read_raster_layer(layer)
        if error:
            problems.append(
                ReadabilityProblem(
                    "raster_read",
                    layer=layer.name(),
                    detail=error,
                )
            )

    return _issues(problems, CHECK_READABILITY), True


def _issues(
    problems: List[ReadabilityProblem], check: str
) -> List[QualityIssue]:
    return readability_issues(problems, check)


def _read_vector_layer(layer) -> str:
    """Прочитать один объект, его атрибуты и геометрию."""

    from qgis.core import QgsFeatureRequest

    try:
        request = QgsFeatureRequest().setLimit(1)
        feature = next(iter(layer.getFeatures(request)), None)
        if feature is not None:
            feature.attributes()
            feature.geometry()
    except Exception as error:
        return _error_text(error)
    return ""


def _read_raster_layer(layer) -> str:
    """Прочитать небольшую выборку пикселей по всей области растра."""

    try:
        if layer.bandCount() < 1:
            return "нет каналов"
        provider = layer.dataProvider()
        if provider is None:
            return "провайдер данных недоступен"
        extent = layer.extent()
        if (
            extent is None
            or extent.isNull()
            or extent.width() <= 0
            or extent.height() <= 0
        ):
            return "пустая область данных"
        for sample in _raster_samples(layer, extent):
            block = provider.block(1, sample, 4, 4)
            if block is None:
                return "провайдер не вернул блок данных"
            is_valid = getattr(block, "isValid", None)
            if callable(is_valid) and not is_valid():
                return "блок данных невалиден"
    except Exception as error:
        return _error_text(error)
    return ""


def _raster_samples(layer, extent) -> List[object]:
    """Вернуть небольшие области в начале, центре и конце растра."""

    from qgis.core import QgsRectangle

    width = layer.width()
    height = layer.height()
    if width <= 4 and height <= 4:
        return [extent]

    pixel_width = extent.width() / max(width, 1)
    pixel_height = extent.height() / max(height, 1)
    half_width = pixel_width * 2
    half_height = pixel_height * 2
    samples: List[object] = []
    for factor_x, factor_y in ((0.1, 0.9), (0.5, 0.5), (0.9, 0.1)):
        center_x = extent.xMinimum() + extent.width() * factor_x
        center_y = extent.yMinimum() + extent.height() * factor_y
        samples.append(
            QgsRectangle(
                center_x - half_width,
                center_y - half_height,
                center_x + half_width,
                center_y + half_height,
            )
        )
    return samples


def _error_text(error: object) -> str:
    text = str(error).strip()
    if not text:
        text = error.__class__.__name__
    return text[:300]
