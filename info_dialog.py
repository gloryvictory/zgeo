"""Диалог с подробной информацией о файле."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QIcon, QPalette
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .file_info import FieldInfo, FileInfo, RasterLayerInfo, VectorLayerInfo
from .formatting import format_size
from .i18n import tr
from .table_export import export_table_with_dialog

ICON_PATH = Path(__file__).with_name("icon.svg")


class FileInfoDialog(QDialog):
    """Показать общие сведения, CRS, объекты и атрибутивные поля."""

    def __init__(
        self, file_info: FileInfo, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._info = file_info

        self.setWindowTitle(tr("Информация — {}", file_info.path.name))
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(860, 660)
        self.setMinimumSize(680, 480)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)

        title = QLabel(self._info.path.name)
        self._set_font(title, 4, bold=True)
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(title)

        meta = QLabel(
            "{} · {}".format(
                self._info.format_name,
                format_size(self._info.size),
            )
        )
        self._set_font(meta, -1)
        self._set_muted(meta)
        layout.addWidget(meta)

        path_label = QLabel(str(self._info.path))
        path_label.setWordWrap(True)
        path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._set_font(path_label, -1)
        self._set_muted(path_label)
        layout.addWidget(path_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        pages, labels = self._build_layer_pages()
        if pages:
            if len(pages) > 1:
                layer_row = QHBoxLayout()
                layer_caption = QLabel(tr("Слой:"))
                self._set_font(layer_caption, 0, bold=True)
                layer_row.addWidget(layer_caption)

                combo = QComboBox()
                combo.addItems(labels)
                layer_row.addWidget(combo, 1)
                layout.addLayout(layer_row)

            stack = QStackedWidget()
            for page in pages:
                stack.addWidget(page)
            layout.addWidget(stack, 1)

            if len(pages) > 1:
                combo.currentIndexChanged.connect(stack.setCurrentIndex)
        else:
            message = QLabel(
                tr(
                    "Не удалось получить пространственные сведения. "
                    "Файл может быть повреждён или его формат "
                    "не поддерживается установленными провайдерами QGIS."
                )
            )
            message.setWordWrap(True)
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(message, 1)

        if self._info.notes:
            notes = QLabel("\n".join(self._info.notes))
            notes.setWordWrap(True)
            notes.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred,
            )
            self._set_font(notes, -1)
            self._set_muted(notes)
            layout.addWidget(notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_layer_pages(
        self,
    ) -> Tuple[List[QWidget], List[str]]:
        pages: List[QWidget] = []
        labels: List[str] = []

        for layer in self._info.vector_layers:
            pages.append(self._build_vector_page(layer))
            labels.append(tr("Вектор · {}", layer.name))

        for layer in self._info.raster_layers:
            pages.append(self._build_raster_page(layer))
            labels.append(tr("Растр · {}", layer.name))

        return pages, labels

    def _build_vector_page(self, layer: VectorLayerInfo) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        row = 0
        row = self._add_info_row(grid, row, tr("Слой"), layer.name)
        row = self._add_info_row(
            grid, row, tr("Система координат"), layer.crs
        )
        row = self._add_info_row(
            grid,
            row,
            tr("Количество объектов"),
            self._format_feature_count(layer.feature_count),
        )
        row = self._add_info_row(
            grid, row, tr("Геометрия"), layer.geometry
        )
        row = self._add_info_row(grid, row, tr("Экстент"), layer.extent)
        row = self._add_info_row(
            grid, row, tr("Провайдер"), layer.provider
        )
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        fields_caption = QLabel(
            tr("Атрибутивные поля ({})", len(layer.fields))
        )
        self._set_font(fields_caption, 0, bold=True)
        layout.addWidget(fields_caption)

        if layer.fields:
            fields_table = self._build_fields_table(layer.fields)
            layout.addWidget(fields_table, 1)

            export_row = QHBoxLayout()
            export_row.addStretch(1)
            export_button = QPushButton(tr("Экспорт в Excel"))
            export_button.setIcon(
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_DialogSaveButton
                )
            )
            export_button.setMinimumHeight(30)
            export_button.clicked.connect(
                lambda _checked=False, table=fields_table: (
                    self._export_fields_table(table)
                )
            )
            export_row.addWidget(export_button)
            layout.addLayout(export_row)
        else:
            empty = QLabel(tr("Атрибутивные поля отсутствуют."))
            empty.setWordWrap(True)
            self._set_muted(empty)
            layout.addWidget(empty, 1)

        return page

    def _export_fields_table(self, table: QTableWidget) -> None:
        export_table_with_dialog(
            self,
            table,
            tr("{}_поля.xlsx", self._info.path.stem),
            tr("Атрибутивные поля"),
        )

    def _build_raster_page(self, layer: RasterLayerInfo) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        row = 0
        row = self._add_info_row(grid, row, tr("Слой"), layer.name)
        row = self._add_info_row(
            grid, row, tr("Система координат"), layer.crs
        )
        row = self._add_info_row(
            grid,
            row,
            tr("Размер растра"),
            "{} × {} px".format(layer.width, layer.height),
        )
        row = self._add_info_row(
            grid, row, tr("Количество каналов"), str(layer.band_count)
        )
        row = self._add_info_row(
            grid, row, tr("Размер пикселя"), layer.pixel_size
        )
        row = self._add_info_row(grid, row, tr("Экстент"), layer.extent)
        row = self._add_info_row(
            grid, row, tr("Провайдер"), layer.provider
        )
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    def _build_fields_table(self, fields: Tuple[FieldInfo, ...]) -> QTableWidget:
        table = QTableWidget(len(fields), 6)
        table.setHorizontalHeaderLabels(
            [
                tr("Имя"),
                tr("Алиас"),
                tr("Тип"),
                tr("Длина"),
                tr("Точность"),
                tr("Комментарий"),
            ]
        )
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(180)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(0, 150)
        header.resizeSection(1, 140)
        header.resizeSection(2, 110)
        header.resizeSection(3, 65)
        header.resizeSection(4, 75)

        for row, field in enumerate(fields):
            values = (
                field.name,
                field.alias or "—",
                field.type_name,
                str(field.length) if field.length else "—",
                str(field.precision) if field.precision else "—",
                field.comment or "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column in (3, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                    if value != "—":
                        item.setData(
                            Qt.ItemDataRole.UserRole, int(value)
                        )
                table.setItem(row, column, item)

        return table

    def _add_info_row(
        self, grid: QGridLayout, row: int, caption: str, value: str
    ) -> int:
        label = QLabel(caption)
        self._set_font(label, -1, bold=True)
        self._set_muted(label)

        value_label = QLabel(value)
        value_label.setWordWrap(True)
        value_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        grid.addWidget(
            label, row, 0, Qt.AlignmentFlag.AlignTop
        )
        grid.addWidget(value_label, row, 1)
        return row + 1

    @staticmethod
    def _format_feature_count(count: int) -> str:
        if count < 0:
            return tr("Недоступно")
        return "{:,}".format(count).replace(",", " ")

    @staticmethod
    def _set_font(widget: QWidget, size_delta: int, bold: bool = False) -> None:
        font = QFont(widget.font())
        point_size = widget.font().pointSizeF()
        if point_size <= 0:
            point_size = 10.0
        font.setPointSizeF(max(7.0, point_size + size_delta))
        font.setBold(bold)
        widget.setFont(font)

    @staticmethod
    def _set_muted(widget: QWidget) -> None:
        palette = widget.palette()
        palette.setColor(
            QPalette.ColorRole.WindowText,
            palette.color(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.WindowText,
            ),
        )
        widget.setPalette(palette)
