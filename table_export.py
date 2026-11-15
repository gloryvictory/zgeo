"""Экспорт таблиц интерфейса в Excel и HTML с выбором файла."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QTableWidget

from .excel_export import CellValue, SheetSpec, write_xlsx_sheets
from .explorer import reveal_files
from .html_export import write_html_sheets
from .i18n import tr


def export_table_with_dialog(
    parent,
    table: QTableWidget,
    default_filename: str,
    sheet_name: str,
    summary_rows: Optional[Iterable[Sequence[CellValue]]] = None,
) -> Optional[Path]:
    """Предложить сохранить таблицу и записать её в .xlsx."""

    if table.rowCount() == 0:
        return None

    headers = [
        table.horizontalHeaderItem(column).text()
        if table.horizontalHeaderItem(column) is not None
        else ""
        for column in range(table.columnCount())
    ]
    rows = _table_rows(table)
    if summary_rows:
        rows.extend([list(row) for row in summary_rows])
    return export_rows_with_dialog(
        parent,
        headers,
        rows,
        default_filename,
        sheet_name,
    )


def export_rows_with_dialog(
    parent,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    default_filename: str,
    sheet_name: str,
    extra_sheets: Optional[Iterable[SheetSpec]] = None,
) -> Optional[Path]:
    """Предложить сохранить строки в .xlsx и открыть проводник.

    Дополнительные таблицы записываются отдельными листами книги.
    """

    rows = list(rows)
    if not rows:
        return None

    path = _choose_save_path(
        parent,
        tr("Экспорт в Excel"),
        default_filename,
        "Excel (*.xlsx)",
        ".xlsx",
    )
    if path is None:
        return None

    sheets: list = [(sheet_name, headers, rows)]
    if extra_sheets:
        sheets.extend(list(extra_sheets))

    try:
        write_xlsx_sheets(path, sheets)
    except Exception as error:
        _show_export_error(parent, error)
        return None

    _reveal_exported(parent, path)
    return path


def export_rows_with_html_dialog(
    parent,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    default_filename: str,
    sheet_name: str,
    extra_sheets: Optional[Iterable[SheetSpec]] = None,
    title: Optional[str] = None,
) -> Optional[Path]:
    """Предложить сохранить строки в .html и открыть проводник.

    Все дополнительные таблицы записываются в тот же HTML-файл
    отдельными разделами.
    """

    rows = list(rows)
    if not rows:
        return None

    path = _choose_save_path(
        parent,
        tr("Экспорт в HTML"),
        default_filename,
        "HTML (*.html)",
        ".html",
    )
    if path is None:
        return None

    sheets: list = [(sheet_name, headers, rows)]
    if extra_sheets:
        sheets.extend(list(extra_sheets))

    try:
        write_html_sheets(path, sheets, title=title)
    except Exception as error:
        _show_export_error(parent, error)
        return None

    _reveal_exported(parent, path)
    return path


def _choose_save_path(
    parent,
    caption: str,
    default_filename: str,
    file_filter: str,
    suffix: str,
) -> Optional[Path]:
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        caption,
        str(start_dir / default_filename),
        file_filter,
    )
    if not selected:
        return None

    path = Path(selected)
    if path.suffix.lower() != suffix:
        path = path.with_suffix(suffix)
    return path


def _show_export_error(parent, error: Exception) -> None:
    QMessageBox.critical(
        parent,
        "ZGeo",
        tr("Не удалось экспортировать таблицу:\n{}", error),
    )


def _reveal_exported(parent, path: Path) -> None:
    errors = reveal_files([path])
    if not errors:
        return
    QMessageBox.warning(
        parent,
        "ZGeo",
        tr(
            "Таблица экспортирована:\n{}\n\n"
            "Не удалось открыть проводник:\n{}",
            path,
            "\n".join(errors),
        ),
    )


def _table_rows(table: QTableWidget) -> list:
    rows = []
    for row in range(table.rowCount()):
        values = []
        for column in range(table.columnCount()):
            item = table.item(row, column)
            if item is None:
                values.append("")
                continue
            raw_value = item.data(Qt.ItemDataRole.UserRole)
            values.append(
                raw_value if raw_value is not None else item.text()
            )
        rows.append(values)
    return rows
