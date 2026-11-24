"""Проверка целостности GeoPackage и SQLite.

Модуль не зависит от QGIS: база открывается через стандартный ``sqlite3``
в режиме только для чтения, поэтому файл не изменяется.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .quality_check import QualityIssue, read_failure_issue
from .scanner import GeoFile

_LOGGER = logging.getLogger(__name__)

SQLITE_EXTENSIONS = frozenset({".gpkg", ".sqlite", ".spatialite"})
REQUIRED_GPKG_TABLES = (
    "gpkg_contents",
    "gpkg_geometry_columns",
    "gpkg_spatial_ref_sys",
)
MAX_DETAILS = 20
MAX_FOREIGN_KEY_ISSUES = 20


def inspect_gpkg_integrity(
    geo_file: GeoFile,
    check: str,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить целостность SQLite и структуру GeoPackage."""

    if geo_file.extension not in SQLITE_EXTENSIONS:
        return [], False

    path = geo_file.path
    if not path.exists():
        return _file_issues(check, "Файл не найден или недоступен"), True

    try:
        size = path.stat().st_size
    except OSError:
        return _file_issues(check, "Файл не найден или недоступен"), True

    if size <= 0:
        return _file_issues(check, "Файл пуст (0 байт)"), True

    try:
        connection = _open_readonly(path)
    except Exception as error:
        return _file_issues(
            check,
            "Не удалось открыть SQLite: {}",
            (_error_text(error),),
        ), True

    try:
        issues = _inspect_connection(
            connection,
            geo_file.extension,
            check,
        )
    finally:
        connection.close()
    return issues, True


def _inspect_connection(
    connection: sqlite3.Connection,
    extension: str,
    check: str,
) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    integrity_issues, fatal = _integrity_issues(connection, check)
    issues.extend(integrity_issues)
    if fatal:
        return issues
    issues.extend(_foreign_key_issues(connection, check))

    table_names = _table_names(connection)
    if table_names is None:
        issues.append(
            read_failure_issue(
                check,
                "GeoPackage",
                "не удалось прочитать список таблиц",
            )
        )
        return issues

    is_gpkg = extension == ".gpkg" or any(
        name in table_names for name in REQUIRED_GPKG_TABLES
    )
    if not is_gpkg:
        return issues

    missing = [
        name for name in REQUIRED_GPKG_TABLES if name not in table_names
    ]
    for name in missing:
        issues.append(
            QualityIssue(
                check,
                "В GeoPackage отсутствует обязательная таблица: {}",
                (name,),
                location="GeoPackage",
            )
        )
    if not missing:
        issues.extend(
            _gpkg_consistency_issues(connection, table_names, check)
        )
    return issues


def _integrity_issues(
    connection: sqlite3.Connection,
    check: str,
) -> Tuple[List[QualityIssue], bool]:
    try:
        quick_rows = _pragma_rows(connection, "quick_check")
    except sqlite3.Error as error:
        return [
            QualityIssue(
                check,
                "Проверка целостности SQLite: {}",
                (_error_text(error),),
                location="PRAGMA quick_check",
            )
        ], True

    if _rows_are_ok(quick_rows):
        return [], False

    details = quick_rows
    try:
        integrity_rows = _pragma_rows(connection, "integrity_check")
        if integrity_rows and not _rows_are_ok(integrity_rows):
            details = integrity_rows
    except sqlite3.Error:
        pass

    issues: List[QualityIssue] = []
    for row in details[:MAX_DETAILS]:
        text = _row_text(row)
        issues.append(
            QualityIssue(
                check,
                "Проверка целостности SQLite: {}",
                (text,),
                location="PRAGMA integrity_check",
            )
        )
    if len(details) > MAX_DETAILS:
        issues.append(
            QualityIssue(
                check,
                "Нарушений целостности SQLite: {} (показаны первые {})",
                (len(details), MAX_DETAILS),
                location="PRAGMA integrity_check",
            )
        )
    return issues, False


def _foreign_key_issues(
    connection: sqlite3.Connection,
    check: str,
) -> List[QualityIssue]:
    try:
        rows = _pragma_rows(connection, "foreign_key_check")
    except sqlite3.Error as error:
        return [
            QualityIssue(
                check,
                "Не удалось проверить внешние ключи: {}",
                (_error_text(error),),
                location="PRAGMA foreign_key_check",
            )
        ]

    issues: List[QualityIssue] = []
    for row in rows[:MAX_FOREIGN_KEY_ISSUES]:
        table = _cell(row, 0)
        rowid = _cell(row, 1)
        parent = _cell(row, 2)
        issues.append(
            QualityIssue(
                check,
                "Нарушение внешнего ключа: таблица {}, строка {}, "
                "родительская таблица {}",
                (table, rowid, parent),
                location=table,
            )
        )
    if len(rows) > MAX_FOREIGN_KEY_ISSUES:
        issues.append(
            QualityIssue(
                check,
                "Нарушений внешнего ключа: {} (показаны первые {})",
                (len(rows), MAX_FOREIGN_KEY_ISSUES),
                location="PRAGMA foreign_key_check",
            )
        )
    return issues


def _gpkg_consistency_issues(
    connection: sqlite3.Connection,
    table_names: Set[str],
    check: str,
) -> List[QualityIssue]:
    try:
        contents_rows = connection.execute(
            "SELECT table_name, data_type, srs_id FROM gpkg_contents"
        ).fetchall()
        geometry_rows = connection.execute(
            "SELECT table_name, column_name, geometry_type_name, srs_id "
            "FROM gpkg_geometry_columns"
        ).fetchall()
        srs_rows = connection.execute(
            "SELECT srs_id FROM gpkg_spatial_ref_sys"
        ).fetchall()
    except sqlite3.Error as error:
        return [
            QualityIssue(
                check,
                "Не удалось прочитать таблицы GeoPackage: {}",
                (_error_text(error),),
                location="GeoPackage",
            )
        ]

    contents: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
    for row in contents_rows:
        table = _text(row[0])
        if not table:
            continue
        contents[table] = (_text(row[1]), _int_or_none(row[2]))

    srs_ids = {
        _int_or_none(row[0])
        for row in srs_rows
        if _int_or_none(row[0]) is not None
    }
    geometry_tables: Set[str] = set()
    issues: List[QualityIssue] = []

    for row in geometry_rows:
        table = _text(row[0])
        column = _text(row[1])
        srs_id = _int_or_none(row[3])
        if not table or not column:
            issues.append(
                QualityIssue(
                    check,
                    "Некорректная запись gpkg_geometry_columns: "
                    "пустое имя таблицы или колонки",
                    location="gpkg_geometry_columns",
                )
            )
            continue

        geometry_tables.add(table)
        content = contents.get(table)
        if content is None:
            issues.append(
                QualityIssue(
                    check,
                    "Геометрическая колонка {}: таблица {} отсутствует "
                    "в gpkg_contents",
                    (column, table),
                    location=table,
                )
            )
        else:
            data_type, content_srs = content
            if data_type != "features":
                issues.append(
                    QualityIssue(
                        check,
                        "Таблица {} в gpkg_contents имеет тип {}, "
                        "ожидается features",
                        (table, data_type or "—"),
                        location=table,
                    )
                )
            if srs_id is None:
                issues.append(
                    QualityIssue(
                        check,
                        "Геометрическая колонка {}: не указан srs_id",
                        (column,),
                        location=table,
                    )
                )
            elif srs_id not in srs_ids:
                issues.append(
                    QualityIssue(
                        check,
                        "Геометрическая колонка {}: srs_id {} отсутствует "
                        "в gpkg_spatial_ref_sys",
                        (column, srs_id),
                        location=table,
                    )
                )
            if content_srs != srs_id:
                issues.append(
                    QualityIssue(
                        check,
                        "Несовпадение srs_id для таблицы {}: "
                        "gpkg_contents={}, gpkg_geometry_columns={}",
                        (
                            table,
                            _display(content_srs),
                            _display(srs_id),
                        ),
                        location=table,
                    )
                )

        if table in table_names:
            columns = _table_columns(connection, table)
            if columns is None:
                issues.append(
                    read_failure_issue(
                        check,
                        table,
                        "не удалось прочитать список колонок",
                    )
                )
            elif column not in columns:
                issues.append(
                    QualityIssue(
                        check,
                        "Геометрическая колонка {}: в таблице {} нет такой "
                        "колонки",
                        (column, table),
                        location=table,
                    )
                )

    for table, (data_type, srs_id) in contents.items():
        if table not in table_names:
            issues.append(
                QualityIssue(
                    check,
                    "Таблица {} из gpkg_contents отсутствует в базе",
                    (table,),
                    location=table,
                )
            )
        if data_type != "features":
            continue
        if table not in geometry_tables:
            issues.append(
                QualityIssue(
                    check,
                    "Для таблицы {} нет записи в gpkg_geometry_columns",
                    (table,),
                    location=table,
                )
            )
        if srs_id is None:
            issues.append(
                QualityIssue(
                    check,
                    "В gpkg_contents для таблицы {} не указан srs_id",
                    (table,),
                    location=table,
                )
            )

    return issues


def _open_readonly(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=2.0)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _pragma_rows(
    connection: sqlite3.Connection,
    pragma: str,
) -> List[Tuple[object, ...]]:
    return [
        tuple(row)
        for row in connection.execute("PRAGMA {}".format(pragma))
    ]


def _table_names(connection: sqlite3.Connection) -> Optional[Set[str]]:
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        return {_text(row[0]) for row in rows if _text(row[0])}
    except sqlite3.Error:
        _LOGGER.exception("Failed to read sqlite_master")
        return None


def _table_columns(
    connection: sqlite3.Connection,
    table: str,
) -> Optional[Set[str]]:
    try:
        rows = connection.execute(
            "SELECT name FROM pragma_table_info(?)",
            (table,),
        )
        return {_text(row[0]) for row in rows if _text(row[0])}
    except sqlite3.Error:
        _LOGGER.exception("Failed to read columns of table %r", table)
        return None


def _rows_are_ok(rows: List[Tuple[object, ...]]) -> bool:
    if not rows:
        return True
    for row in rows:
        text = _text(row[0]) if row else ""
        if text.lower() != "ok":
            return False
    return True


def _row_text(row: Tuple[object, ...]) -> str:
    values = [_text(value) for value in row if _text(value)]
    return " | ".join(values) or "неизвестная ошибка"


def _cell(
    row: Tuple[object, ...],
    index: int,
    default: str = "—",
) -> str:
    if index >= len(row):
        return default
    return _text(row[index]) or default


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int_or_none(value: object) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _display(value: Optional[int]) -> str:
    return "—" if value is None else str(value)


def _error_text(error: object) -> str:
    text = _text(error)
    if not text:
        text = error.__class__.__name__
    return text[:300]


def _file_issues(
    check: str,
    message: str,
    args: Tuple[object, ...] = (),
) -> List[QualityIssue]:
    return [
        QualityIssue(
            check,
            message,
            args,
            location="Файл",
        )
    ]
