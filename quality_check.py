"""Проверки качества атрибутов, набора данных и слоёв.

Модуль не зависит от QGIS: на вход подаются имена полей, системы
координат и количество объектов, собранные через провайдеры QGIS.
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

DBF_FIELD_NAME_LIMIT = 10

REQUIRED_SIDECARS: Dict[str, Tuple[str, ...]] = {
    ".shp": (".dbf", ".shx"),
    ".mif": (".mid",),
    ".tab": (".dat", ".map", ".id"),
}

MISSING_CRS_VALUES = frozenset(
    {"", "—", "-", "Не определена", "Undefined", "Unknown", "Неизвестна"}
)


@dataclass(frozen=True)
class QualityIssue:
    """Одна найденная проблема."""

    check: str
    message: str
    args: Tuple[object, ...] = ()


def directory_files(
    directory: Path, cache: Dict[str, Dict[str, Path]]
) -> Dict[str, Path]:
    """Вернуть файлы каталога по именам в нижнем регистре."""

    key = str(directory)
    files = cache.get(key)
    if files is None:
        try:
            files = {
                item.name.casefold(): item
                for item in directory.iterdir()
                if item.is_file()
            }
        except OSError:
            files = {}
        cache[key] = files
    return files


def completeness_issues(
    geo_file, files: Mapping[str, Path]
) -> List[QualityIssue]:
    """Проверить наличие обязательных файлов набора данных."""

    required = REQUIRED_SIDECARS.get(geo_file.extension)
    if not required:
        return []

    base = geo_file.path.stem.casefold()
    missing = [
        extension
        for extension in required
        if base + extension not in files
    ]
    if not missing:
        return []

    return [
        QualityIssue(
            "dataset_completeness",
            "В наборе отсутствуют файлы: {}",
            (", ".join(missing),),
        )
    ]


def dbf_encoding_issues(
    geo_file, files: Mapping[str, Path]
) -> List[QualityIssue]:
    """Проверить наличие .cpg и корректность указанной кодировки DBF."""

    if geo_file.extension != ".shp":
        return []

    base = geo_file.path.stem.casefold()
    dbf_path = files.get(base + ".dbf")
    if dbf_path is None:
        return []

    issues: List[QualityIssue] = []
    cpg_path = files.get(base + ".cpg")

    if _dbf_ldid(dbf_path) is None:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Не удалось прочитать заголовок DBF",
            )
        )

    if cpg_path is None:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Нет файла .cpg: кодировка DBF не указана",
            )
        )
        return issues

    try:
        content = cpg_path.read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        try:
            content = cpg_path.read_bytes().decode("latin-1").strip()
        except OSError:
            content = ""

    if not content:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Файл .cpg пуст: кодировка DBF не указана",
            )
        )
    elif not is_known_encoding(content):
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Неизвестная кодировка в .cpg: {}",
                (content,),
            )
        )

    return issues


def is_known_encoding(value: str) -> bool:
    """Проверить, что строка .cpg задаёт известную кодировку."""

    text = value.strip()
    if not text:
        return False

    upper = text.upper()
    if upper.startswith("LDID/"):
        try:
            ldid = int(upper.split("/", 1)[1])
        except ValueError:
            return False
        return 0 <= ldid <= 255

    candidate = text
    if candidate.isdigit():
        candidate = "cp" + candidate
    try:
        codecs.lookup(candidate)
    except LookupError:
        return False
    return True


def _dbf_ldid(path: Path) -> Optional[int]:
    """Прочитать байт языкового драйвера из заголовка DBF."""

    try:
        with path.open("rb") as handle:
            header = handle.read(32)
    except OSError:
        return None
    if len(header) < 32:
        return None
    return header[29]


def field_name_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Проверить длину, пробелы и спецсимволы в именах полей."""

    issues: List[QualityIssue] = []
    seen_names = set()

    for _layer_name, field_names in layers:
        for name in field_names:
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            if len(name) > DBF_FIELD_NAME_LIMIT:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: длина {} больше {} символов "
                        "(ограничение DBF)",
                        (name, len(name), DBF_FIELD_NAME_LIMIT),
                    )
                )

            if " " in name:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: содержит пробел",
                        (name,),
                    )
                )

            special = "".join(
                sorted(
                    {
                        character
                        for character in name
                        if character != " "
                        and not (character.isalnum() or character == "_")
                    }
                )
            )
            if special:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: недопустимые символы: {}",
                        (name, special),
                    )
                )

    return issues


def truncated_duplicate_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Найти имена полей, совпадающие после усечения до лимита DBF."""

    issues: List[QualityIssue] = []

    for layer_name, field_names in layers:
        groups: Dict[str, List[str]] = {}
        for name in field_names:
            if not name:
                continue
            key = name[:DBF_FIELD_NAME_LIMIT].casefold()
            groups.setdefault(key, []).append(name)

        for names in groups.values():
            unique = sorted(set(names))
            if len(unique) < 2:
                continue
            issues.append(
                QualityIssue(
                    "truncated_duplicates",
                    "Слой «{}»: после усечения до {} символов совпадают "
                    "имена полей: {}",
                    (layer_name, DBF_FIELD_NAME_LIMIT, ", ".join(unique)),
                )
            )

    return issues


def crs_issues(values: Sequence[str]) -> List[QualityIssue]:
    """Найти отсутствующие, неизвестные или смешанные системы координат."""

    defined = [value for value in values if value]
    if not defined:
        return []

    missing = [
        value for value in defined if value in MISSING_CRS_VALUES
    ]
    unique = {
        value for value in defined if value not in MISSING_CRS_VALUES
    }

    if not unique:
        return [
            QualityIssue(
                "crs_quality",
                "Система координат не определена",
            )
        ]

    issues: List[QualityIssue] = []
    if missing:
        issues.append(
            QualityIssue(
                "crs_quality",
                "У части слоёв не определена система координат",
            )
        )

    if len(unique) > 1:
        examples = ", ".join(sorted(unique)[:3])
        issues.append(
            QualityIssue(
                "crs_quality",
                "Смешанные системы координат: {}",
                (examples,),
            )
        )

    return issues


def empty_layer_issues(
    layers: Sequence[Tuple[str, int]],
) -> List[QualityIssue]:
    """Найти пустые слои и файлы без объектов."""

    if not layers:
        return []

    empty = [
        (name, count) for name, count in layers if count == 0
    ]
    if not empty:
        return []

    issues: List[QualityIssue] = []
    if len(empty) == len(layers):
        issues.append(
            QualityIssue("empty_layers", "Файл не содержит объектов")
        )

    for name, _count in empty:
        issues.append(
            QualityIssue(
                "empty_layers",
                "Слой «{}» не содержит объектов",
                (name,),
            )
        )

    return issues
