"""Экспорт таблиц интерфейса в Excel с выбором файла."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QTableWidget

from .excel_export import CellValue, write_xlsx


def export_table_with_dialog(
    parent,
    table: QTableWidget,
    default_filename: str,
    sheet_name: str,
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
    return export_rows_with_dialog(
        parent,
        headers,
        _table_rows(table),
        default_filename,
        sheet_name,
    )


def export_rows_with_dialog(
    parent,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    default_filename: str,
    sheet_name: str,
) -> Optional[Path]:
    """Предложить сохранить произвольный набор строк в .xlsx."""

    rows = list(rows)
    if not rows:
        return None

    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        "Экспорт в Excel",
        str(start_dir / default_filename),
        "Excel (*.xlsx)",
    )
    if not selected:
        return None

    path = Path(selected)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")

    try:
        write_xlsx(path, sheet_name, headers, rows)
    except Exception as error:
        QMessageBox.critical(
            parent,
            "ZGeo",
            "Не удалось экспортировать таблицу:\n{}".format(error),
        )
        return None

    QMessageBox.information(
        parent,
        "ZGeo",
        "Таблица экспортирована:\n{}".format(path),
    )
    return path


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
