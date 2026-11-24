"""Поиск дублей по атрибутам: строки, ключи, регистр и вхождения.

Модуль не зависит от QGIS: на вход подаются имена полей, значения строк
и идентификаторы объектов, собранные через провайдеры QGIS. Проверка
тяжёлая, поэтому все переборы ограничены константами модуля.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .quality_check import QualityIssue, read_failure_issue

_LOGGER = logging.getLogger(__name__)

DUPLICATE_FULL_ROW = "full_row"
DUPLICATE_KEY = "key"
DUPLICATE_NORMALIZED = "normalized"
DUPLICATE_PARTIAL = "partial"

MAX_GROUPS_PER_FIELD = 200
MAX_EXAMPLES = 10
PARTIAL_MIN_LENGTH = 4
PARTIAL_MIN_PERCENT = 50.0
PARTIAL_MAX_VALUES = 1000
MAX_FEATURES = 50000


@dataclass(frozen=True)
class AttributeDuplicate:
    """Одна группа дублей по атрибутам."""

    kind: str
    field: str = ""
    values: Tuple[str, ...] = ()
    feature_ids: Tuple[int, ...] = ()
    percent: float = 0.0

    @property
    def count(self) -> int:
        return len(self.feature_ids)


def normalize_value(value: object) -> str:
    """Привести значение к виду без учёта регистра и лишних пробелов."""

    if value is None:
        return ""
    return " ".join(str(value).split()).casefold()


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _field_indexes(
    field_names: Sequence[str], rows: Sequence[Sequence[object]]
) -> List[int]:
    """Индексы текстовых полей: хотя бы одно строковое значение."""

    indexes: List[int] = []
    for index in range(len(field_names)):
        for row in rows:
            if index < len(row) and isinstance(row[index], str):
                indexes.append(index)
                break
    return indexes


def _group_values(
    rows: Sequence[Sequence[object]],
    feature_ids: Sequence[int],
    indexes: Sequence[int],
) -> Dict[Tuple[str, ...], List[int]]:
    groups: Dict[Tuple[str, ...], List[int]] = {}
    for position, row in enumerate(rows):
        key = tuple(
            _text(row[index]) if index < len(row) else ""
            for index in indexes
        )
        groups.setdefault(key, []).append(feature_ids[position])
    return groups


def _duplicate_groups(
    groups: Dict[Tuple[str, ...], List[int]],
    *,
    kind: str,
    field: str = "",
    max_groups: int = MAX_GROUPS_PER_FIELD,
) -> List[AttributeDuplicate]:
    duplicates: List[AttributeDuplicate] = []
    for values, ids in groups.items():
        if len(ids) < 2:
            continue
        duplicates.append(
            AttributeDuplicate(
                kind=kind,
                field=field,
                values=values,
                feature_ids=tuple(ids[:MAX_EXAMPLES]),
            )
        )
        if len(duplicates) >= max_groups:
            break
    return duplicates


def _normalized_duplicates(
    field_names: Sequence[str],
    rows: Sequence[Sequence[object]],
    feature_ids: Sequence[int],
    indexes: Sequence[int],
) -> List[AttributeDuplicate]:
    duplicates: List[AttributeDuplicate] = []
    for index in indexes:
        groups: Dict[str, Dict[str, List[int]]] = {}
        for position, row in enumerate(rows):
            value = row[index] if index < len(row) else None
            if value is None or not isinstance(value, str) or not value.strip():
                continue
            normalized = normalize_value(value)
            variants = groups.setdefault(normalized, {})
            variants.setdefault(value, []).append(feature_ids[position])

        found = 0
        for normalized, variants in groups.items():
            ids = [
                feature_id
                for variant_ids in variants.values()
                for feature_id in variant_ids
            ]
            if len(ids) < 2:
                continue
            duplicates.append(
                AttributeDuplicate(
                    kind=DUPLICATE_NORMALIZED,
                    field=field_names[index],
                    values=tuple(list(variants)[:MAX_EXAMPLES]),
                    feature_ids=tuple(ids[:MAX_EXAMPLES]),
                )
            )
            found += 1
            if found >= MAX_GROUPS_PER_FIELD:
                break
    return duplicates


def _partial_duplicates(
    field_names: Sequence[str],
    rows: Sequence[Sequence[object]],
    feature_ids: Sequence[int],
    indexes: Sequence[int],
    *,
    min_length: int = PARTIAL_MIN_LENGTH,
    min_percent: float = PARTIAL_MIN_PERCENT,
    max_values: int = PARTIAL_MAX_VALUES,
) -> List[AttributeDuplicate]:
    """Найти значения, целиком входящие в другие значения того же поля.

    Вхождение проверяется без учёта регистра, в отчёте остаются исходные
    значения. Процент считается по длинам исходных значений.
    """

    duplicates: List[AttributeDuplicate] = []
    for index in indexes:
        owners: Dict[str, List[int]] = {}
        for position, row in enumerate(rows):
            value = row[index] if index < len(row) else None
            if not isinstance(value, str):
                continue
            text = value.strip()
            if len(text) < min_length:
                continue
            owners.setdefault(text, []).append(feature_ids[position])

        values = sorted(owners, key=len)
        if len(values) > max_values:
            values = values[:max_values]
        limit = len(values)
        found = 0
        for short_index in range(limit):
            short = values[short_index]
            short_length = len(short)
            for long_index in range(short_index + 1, limit):
                long = values[long_index]
                if long == short:
                    continue
                percent = short_length * 100.0 / len(long)
                if percent < min_percent:
                    break
                if short.casefold() not in long.casefold():
                    continue
                duplicates.append(
                    AttributeDuplicate(
                        kind=DUPLICATE_PARTIAL,
                        field=field_names[index],
                        values=(short, long),
                        feature_ids=tuple(
                            (
                                owners[short][:MAX_EXAMPLES]
                                + owners[long][:MAX_EXAMPLES]
                            )[:MAX_EXAMPLES]
                        ),
                        percent=round(percent, 1),
                    )
                )
                found += 1
                if found >= MAX_GROUPS_PER_FIELD:
                    break
            if found >= MAX_GROUPS_PER_FIELD:
                break
    return duplicates


def find_attribute_duplicates(
    field_names: Sequence[str],
    rows: Sequence[Sequence[object]],
    feature_ids: Sequence[int],
    *,
    max_groups: int = MAX_GROUPS_PER_FIELD,
) -> List[AttributeDuplicate]:
    """Найти все виды дублей по атрибутам для одного слоя."""

    if not rows or not field_names:
        return []

    text_indexes = _field_indexes(field_names, rows)
    duplicates: List[AttributeDuplicate] = []

    all_indexes = list(range(len(field_names)))
    duplicates.extend(
        _duplicate_groups(
            _group_values(rows, feature_ids, all_indexes),
            kind=DUPLICATE_FULL_ROW,
            max_groups=max_groups,
        )
    )

    if text_indexes and len(text_indexes) != len(field_names):
        duplicates.extend(
            _duplicate_groups(
                _group_values(rows, feature_ids, text_indexes),
                kind=DUPLICATE_KEY,
                max_groups=max_groups,
            )
        )

    if text_indexes:
        duplicates.extend(
            _normalized_duplicates(
                field_names, rows, feature_ids, text_indexes
            )
        )
        duplicates.extend(
            _partial_duplicates(field_names, rows, feature_ids, text_indexes)
        )

    return duplicates


def _ids_text(ids: Iterable[int]) -> str:
    return ", ".join(str(feature_id) for feature_id in ids)


def _values_text(values: Sequence[str]) -> str:
    return ", ".join("«{}»".format(value) for value in values)


def attribute_duplicate_issues(
    layer: str,
    duplicates: Sequence[AttributeDuplicate],
    feature_count: int,
) -> List[QualityIssue]:
    """Собрать замечания по найденным дублям атрибутов."""

    issues: List[QualityIssue] = []
    for duplicate in duplicates:
        if duplicate.kind == DUPLICATE_FULL_ROW:
            message = (
                "Слой «{}»: полные дубли строк — объектов {} с полностью "
                "совпадающими атрибутами (объекты: {})"
            )
            args: Tuple[object, ...] = (
                layer,
                duplicate.count,
                _ids_text(duplicate.feature_ids),
            )
            location = "Атрибуты"
        elif duplicate.kind == DUPLICATE_KEY:
            message = (
                "Слой «{}»: дубли составного ключа по текстовым полям — "
                "объектов {} с одинаковыми значениями (объекты: {})"
            )
            args = (
                layer,
                duplicate.count,
                _ids_text(duplicate.feature_ids),
            )
            location = "Атрибуты"
        elif duplicate.kind == DUPLICATE_NORMALIZED:
            message = (
                "Слой «{}»: поле «{}» — значения совпадают без учёта "
                "регистра и лишних пробелов: {} (объектов {} из {})"
            )
            args = (
                layer,
                duplicate.field,
                _values_text(duplicate.values),
                duplicate.count,
                feature_count,
            )
            location = duplicate.field
        else:
            message = (
                "Слой «{}»: поле «{}» — частичное вхождение: «{}» входит "
                "в «{}» ({}%, объекты: {})"
            )
            args = (
                layer,
                duplicate.field,
                duplicate.values[0],
                duplicate.values[1],
                duplicate.percent,
                _ids_text(duplicate.feature_ids),
            )
            location = duplicate.field
        issues.append(
            QualityIssue(
                "attribute_duplicates",
                message,
                args,
                layer=layer,
                location=location,
            )
        )
    return issues


def inspect_attribute_duplicates(
    geo_file,
    *,
    max_features: int = MAX_FEATURES,
) -> Tuple[List[QualityIssue], bool]:
    """Прочитать атрибуты слоёв через провайдеры QGIS и найти дубли."""

    from .file_info import vector_layers

    issues: List[QualityIssue] = []
    applicable = False
    for layer in vector_layers(geo_file):
        field_names = [field.name() for field in layer.fields()]
        if not field_names:
            continue
        rows: List[Tuple[object, ...]] = []
        feature_ids: List[int] = []
        try:
            for feature in layer.getFeatures():
                rows.append(tuple(feature.attributes()))
                feature_ids.append(feature.id())
                if len(rows) >= max_features:
                    break
        except Exception as exc:
            _LOGGER.exception("Failed to read layer %r", layer.name())
            issues.append(
                read_failure_issue(
                    "attribute_duplicates",
                    layer.name().strip() or "—",
                    str(exc),
                )
            )
            applicable = True
            continue
        if len(rows) < 2:
            applicable = True
            continue

        applicable = True
        duplicates = find_attribute_duplicates(
            field_names, rows, feature_ids
        )
        layer_name = layer.name().strip() or "—"
        issues.extend(
            attribute_duplicate_issues(layer_name, duplicates, len(rows))
        )
    return issues, applicable
