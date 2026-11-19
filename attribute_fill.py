"""Проверка заполненности атрибутов через провайдеры QGIS."""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Tuple

from qgis.core import QgsFieldConstraints, QgsVectorLayer

from .file_info import vector_layers
from .quality_check import (
    FieldFillStats,
    LayerFillStats,
    QualityIssue,
    attribute_fill_issues,
)

_LOGGER = logging.getLogger(__name__)


def inspect_attribute_fill(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить NULL/пустые строки и заполненность полей всех слоёв."""

    stats: List[LayerFillStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return attribute_fill_issues(stats), bool(stats)


def _inspect_layer(layer: QgsVectorLayer) -> Optional[LayerFillStats]:
    fields = list(layer.fields())
    if not fields:
        return None

    required = _required_field_names(layer, fields)
    totals = [0] * len(fields)
    empties = [0] * len(fields)
    feature_count = 0
    fully_empty_features = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            row_empty = True
            for index in range(len(fields)):
                totals[index] += 1
                value = values[index] if index < len(values) else None
                if _is_empty(value):
                    empties[index] += 1
                else:
                    row_empty = False
            if row_empty:
                fully_empty_features += 1
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    field_stats = tuple(
        FieldFillStats(
            name=field.name(),
            total=feature_count,
            empty=empties[index],
            required=field.name() in required,
        )
        for index, field in enumerate(fields)
    )
    return LayerFillStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=field_stats,
        fully_empty_features=fully_empty_features,
    )


def _required_field_names(
    layer: QgsVectorLayer, fields: Sequence
) -> set:
    """Вернуть поля с NOT NULL и поля первичного ключа."""

    try:
        primary_key = {
            index for index in layer.primaryKeyAttributes() if index >= 0
        }
    except Exception:
        primary_key = set()

    required = {
        fields[index].name()
        for index in primary_key
        if 0 <= index < len(fields)
    }
    not_null = QgsFieldConstraints.ConstraintNotNull
    not_set = QgsFieldConstraints.ConstraintStrengthNotSet
    for field in fields:
        if field.name() in required:
            continue
        try:
            strength = field.constraints().constraintStrength(not_null)
        except Exception:
            _LOGGER.debug(
                "Could not read constraint strength for field %s",
                field.name(),
                exc_info=True,
            )
            continue
        if strength != not_set:
            required.add(field.name())
    return required


def _is_empty(value: object) -> bool:
    """NULL, пустая строка или строка только из пробелов."""

    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, bytes):
        return not value
    return False
