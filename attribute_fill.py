"""Проверка заполненности атрибутов через провайдеры QGIS."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from qgis.core import QgsFieldConstraints, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

from .attribute_check import (
    control_characters,
    control_character_label,
    edge_whitespace,
    escape_control_characters,
    escape_edge_whitespace,
    escape_inner_spaces,
    has_inner_spaces,
    date_year_out_of_range,
    numeric_text_kind,
)
from .file_info import vector_layers
from .quality_check import (
    FieldBlankStats,
    FieldControlStats,
    FieldEdgeSpaceStats,
    FieldInnerSpaceStats,
    FieldDateRangeStats,
    FieldNumericTextStats,
    FieldTextLengthStats,
    FieldFillStats,
    LayerBlankStats,
    LayerControlStats,
    LayerEdgeSpaceStats,
    LayerInnerSpaceStats,
    LayerDateRangeStats,
    LayerNumericTextStats,
    LayerTextLengthStats,
    LayerFillStats,
    QualityIssue,
    attribute_fill_issues,
    blank_string_issues,
    control_character_issues,
    edge_space_issues,
    inner_space_issues,
    date_range_issues,
    length_outlier_positions,
    length_statistics,
    numeric_text_issues,
    suspicious_field_name_issues,
    text_length_issues,
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










def inspect_suspicious_field_names(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить имена полей на технические и пустые названия."""

    layers: List[Tuple[str, Tuple[str, ...]]] = []
    for layer in vector_layers(geo_file):
        field_names = tuple(field.name() for field in layer.fields())
        if not field_names:
            continue
        layers.append((layer.name().strip() or "—", field_names))
    if not layers:
        return [], False
    return suspicious_field_name_issues(layers), True

def inspect_date_range(
    geo_file,
    *,
    max_year: Optional[int] = None,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить даты и отметки времени вне разумного диапазона."""

    limit = max_year if max_year is not None else datetime.now().year
    stats: List[LayerDateRangeStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_date_layer(layer, limit)
        if layer_stats is not None:
            stats.append(layer_stats)
    return date_range_issues(stats), bool(stats)


def _inspect_date_layer(
    layer: QgsVectorLayer, max_year: int
) -> Optional[LayerDateRangeStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() in (QVariant.String, QVariant.Date, QVariant.DateTime)
    ]
    if not indexes:
        return None

    invalid = {index: [] for index, _name in indexes}
    years = {index: [] for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = values[index] if index < len(values) else None
                text = _date_text(value)
                if not text:
                    continue
                year = date_year_out_of_range(text, max_year=max_year)
                if year is None:
                    continue
                invalid[index].append((feature.id(), text.strip()))
                years[index].append(year)
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    return LayerDateRangeStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(
            FieldDateRangeStats(
                name=name,
                total=feature_count,
                invalid=tuple(invalid[index]),
                earliest=min(years[index]) if years[index] else 0,
                latest=max(years[index]) if years[index] else 0,
            )
            for index, name in indexes
        ),
    )


def _date_text(value: object) -> str:
    """Привести значение поля даты к строке для разбора."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    text = str(value)
    return text if text and text not in ("NULL", "None") else ""

def inspect_text_length(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить аномальную длину значений в текстовых полях."""

    stats: List[LayerTextLengthStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_length_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return text_length_issues(stats), bool(stats)


def _inspect_length_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerTextLengthStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not indexes:
        return None

    lengths = {index: [] for index, _name in indexes}
    feature_ids = {index: [] for index, _name in indexes}
    values = {index: [] for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            attributes = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = (
                    attributes[index] if index < len(attributes) else None
                )
                if not isinstance(value, str) or not value.strip():
                    continue
                lengths[index].append(len(value))
                feature_ids[index].append(feature.id())
                values[index].append(value)
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    fields: List[FieldTextLengthStats] = []
    for index, name in indexes:
        field_lengths = lengths[index]
        mean, deviation = length_statistics(field_lengths)
        outliers = tuple(
            (feature_ids[index][position], field_lengths[position])
            for position in length_outlier_positions(field_lengths)
        )
        example = ""
        if outliers:
            first_id = outliers[0][0]
            try:
                position = feature_ids[index].index(first_id)
            except ValueError:
                position = 0
            example = escape_inner_spaces(values[index][position])
        fields.append(
            FieldTextLengthStats(
                name=name,
                total=len(field_lengths),
                outliers=outliers,
                mean=mean,
                deviation=deviation,
                example=example,
            )
        )

    return LayerTextLengthStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(fields),
    )

def inspect_numeric_text(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить текстовые поля, где значения записаны числами."""

    stats: List[LayerNumericTextStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_numeric_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return numeric_text_issues(stats), bool(stats)


def _inspect_numeric_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerNumericTextStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not indexes:
        return None

    numeric = {index: 0 for index, _name in indexes}
    integer = {index: 0 for index, _name in indexes}
    real = {index: 0 for index, _name in indexes}
    examples = {index: "" for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = values[index] if index < len(values) else None
                if not isinstance(value, str):
                    continue
                kind = numeric_text_kind(value)
                if not kind:
                    continue
                numeric[index] += 1
                if kind == "integer":
                    integer[index] += 1
                else:
                    real[index] += 1
                if not examples[index]:
                    examples[index] = value.strip()
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    return LayerNumericTextStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(
            FieldNumericTextStats(
                name=name,
                total=feature_count,
                numeric=numeric[index],
                integer=integer[index],
                real=real[index],
                example=examples[index],
            )
            for index, name in indexes
        ),
    )

def inspect_inner_spaces(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить двойные пробелы внутри значений текстовых полей."""

    stats: List[LayerInnerSpaceStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_inner_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return inner_space_issues(stats), bool(stats)


def _inspect_inner_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerInnerSpaceStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not indexes:
        return None

    affected = {index: 0 for index, _name in indexes}
    examples = {index: "" for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = values[index] if index < len(values) else None
                if not isinstance(value, str):
                    continue
                if not has_inner_spaces(value):
                    continue
                affected[index] += 1
                if not examples[index]:
                    examples[index] = escape_inner_spaces(value.strip())
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    return LayerInnerSpaceStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(
            FieldInnerSpaceStats(
                name=name,
                total=feature_count,
                affected=affected[index],
                example=examples[index],
            )
            for index, name in indexes
        ),
    )

def inspect_edge_spaces(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить пробелы, табуляцию и переводы строк по краям значений."""

    stats: List[LayerEdgeSpaceStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_edge_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return edge_space_issues(stats), bool(stats)


def _inspect_edge_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerEdgeSpaceStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not indexes:
        return None

    affected = {index: 0 for index, _name in indexes}
    leading = {index: 0 for index, _name in indexes}
    trailing = {index: 0 for index, _name in indexes}
    examples = {index: "" for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = values[index] if index < len(values) else None
                if not isinstance(value, str) or not value.strip():
                    continue
                head, tail = edge_whitespace(value)
                if not head and not tail:
                    continue
                affected[index] += 1
                if head:
                    leading[index] += 1
                if tail:
                    trailing[index] += 1
                if not examples[index]:
                    examples[index] = escape_edge_whitespace(value)
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    return LayerEdgeSpaceStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(
            FieldEdgeSpaceStats(
                name=name,
                total=feature_count,
                affected=affected[index],
                leading=leading[index],
                trailing=trailing[index],
                example=examples[index],
            )
            for index, name in indexes
        ),
    )

def inspect_blank_strings(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить пустые строки и строки из пробелов в текстовых полях."""

    stats: List[LayerBlankStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_blank_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return blank_string_issues(stats), bool(stats)


def _inspect_blank_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerBlankStats]:
    indexes = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not indexes:
        return None

    blanks = {index: 0 for index, _name in indexes}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in indexes:
                value = values[index] if index < len(values) else None
                if not isinstance(value, str):
                    continue
                if not value.strip():
                    blanks[index] += 1
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    return LayerBlankStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=tuple(
            FieldBlankStats(
                name=name, total=feature_count, blank=blanks[index]
            )
            for index, name in indexes
        ),
    )

def inspect_control_characters(
    geo_file,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить управляющие и невидимые символы в текстовых полях."""

    stats: List[LayerControlStats] = []
    for layer in vector_layers(geo_file):
        layer_stats = _inspect_control_layer(layer)
        if layer_stats is not None:
            stats.append(layer_stats)
    return control_character_issues(stats), bool(stats)


def _inspect_control_layer(
    layer: QgsVectorLayer,
) -> Optional[LayerControlStats]:
    fields = [
        (index, field.name())
        for index, field in enumerate(layer.fields())
        if field.type() == QVariant.String
    ]
    if not fields:
        return None

    counts = {index: 0 for index, _name in fields}
    found = {index: [] for index, _name in fields}
    examples = {index: "" for index, _name in fields}
    feature_count = 0

    try:
        for feature in layer.getFeatures():
            values = feature.attributes()
            feature_count += 1
            for index, _name in fields:
                value = values[index] if index < len(values) else None
                if not isinstance(value, str):
                    continue
                characters = control_characters(value)
                if not characters:
                    continue
                counts[index] += 1
                for character in characters:
                    if character not in found[index]:
                        found[index].append(character)
                if not examples[index]:
                    examples[index] = escape_control_characters(value)
    except Exception:
        return None

    if feature_count <= 0:
        return None

    layer_name = layer.name().strip() or "—"
    field_stats = tuple(
        FieldControlStats(
            name=name,
            features_with_chars=counts[index],
            characters=tuple(
                control_character_label(character)
                for character in found[index]
            ),
            example=examples[index],
        )
        for index, name in fields
        if counts[index]
    )
    if not field_stats:
        return LayerControlStats(
            layer=layer_name, feature_count=feature_count, fields=()
        )
    return LayerControlStats(
        layer=layer_name,
        feature_count=feature_count,
        fields=field_stats,
    )

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
