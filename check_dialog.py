"""Диалог выбора проверок ZGeo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr

ICON_PATH = Path(__file__).with_name("icon.svg")

CHECK_SIZE = "refine_size"
CHECK_SIZE_SHP = "refine_size_shp"
CHECK_SIZE_MIF_MID = "refine_size_mif_mid"
CHECK_CRS = "refine_crs"
CHECK_ELEMENT_COUNT = "refine_element_count"
CHECK_JSON_GEOJSON = "json_geojson"
CHECK_ATTRIBUTE_NAMES = "attribute_names"
CHECK_SHP_FIELD_NAMES = "shp_field_names"
CHECK_TRUNCATED_DUPLICATES = "truncated_duplicates"
CHECK_DBF_ENCODING = "dbf_encoding"
CHECK_DATASET_COMPLETENESS = "dataset_completeness"
CHECK_CRS_QUALITY = "crs_quality"
CHECK_GEOMETRY_VALIDITY = "geometry_validity"
CHECK_COORDINATE_RANGE = "coordinate_range"
CHECK_EMPTY_LAYERS = "empty_layers"

PROBLEM_CHECKS = frozenset(
    {
        CHECK_ATTRIBUTE_NAMES,
        CHECK_SHP_FIELD_NAMES,
        CHECK_TRUNCATED_DUPLICATES,
        CHECK_DBF_ENCODING,
        CHECK_DATASET_COMPLETENESS,
        CHECK_CRS_QUALITY,
        CHECK_GEOMETRY_VALIDITY,
        CHECK_COORDINATE_RANGE,
        CHECK_EMPTY_LAYERS,
    }
)

LAYER_PROBLEM_CHECKS = frozenset(
    {
        CHECK_ATTRIBUTE_NAMES,
        CHECK_SHP_FIELD_NAMES,
        CHECK_TRUNCATED_DUPLICATES,
        CHECK_CRS_QUALITY,
        CHECK_GEOMETRY_VALIDITY,
        CHECK_COORDINATE_RANGE,
        CHECK_EMPTY_LAYERS,
    }
)


@dataclass(frozen=True)
class CheckDefinition:
    """Описание одной проверки."""

    key: str
    label: str
    description: str
    checked: bool = True


def check_definitions(
    include_json_check: bool = True,
) -> List[CheckDefinition]:
    """Вернуть проверки с учётом текущего языка интерфейса."""

    definitions = [
        CheckDefinition(
            key=CHECK_SIZE,
            label=tr("Уточнить размер"),
            description=tr(
                "Считает полный размер каждого набора данных с учётом "
                "сопутствующих файлов."
            ),
        ),
        CheckDefinition(
            key=CHECK_SIZE_SHP,
            label=tr("Уточнить размер SHP"),
            description=tr(
                "Считает полный размер только наборов ESRI Shapefile с "
                "учётом сопутствующих файлов."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_SIZE_MIF_MID,
            label=tr("Уточнить размер MIF/MID"),
            description=tr(
                "Считает полный размер только наборов MapInfo MIF/MID с "
                "учётом файлов .mif и .mid."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_CRS,
            label=tr("Уточнить систему координат"),
            description=tr(
                "Читает систему координат слоёв и обновляет колонку "
                "«Система координат»."
            ),
        ),
        CheckDefinition(
            key=CHECK_ELEMENT_COUNT,
            label=tr("Уточнить количество элементов"),
            description=tr(
                "Считает количество элементов слоёв и обновляет колонку "
                "«Элементов»."
            ),
        ),
        CheckDefinition(
            key=CHECK_ATTRIBUTE_NAMES,
            label=tr("Проверка имён атрибутивных полей"),
            description=tr(
                "Проверяет имена полей векторных файлов на нелатинские "
                "символы и добавляет колонку «Проблемы». Если в имени поля "
                "есть нелатинские символы, ставится «Да», иначе «Нет»; для "
                "растровых файлов — «—»."
            ),
        ),
        CheckDefinition(
            key=CHECK_SHP_FIELD_NAMES,
            label=tr("Проверка имён полей для Shapefile"),
            description=tr(
                "Проверяет длину имён полей (не более 10 символов для "
                "DBF), пробелы и недопустимые символы."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_TRUNCATED_DUPLICATES,
            label=tr("Проверка дублей имён после усечения"),
            description=tr(
                "Ищет поля, имена которых совпадают после усечения до "
                "10 символов."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_DBF_ENCODING,
            label=tr("Проверка кодировки DBF и .cpg"),
            description=tr(
                "Проверяет наличие файла .cpg и корректность указанной "
                "кодировки DBF."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_DATASET_COMPLETENESS,
            label=tr("Проверка комплектности набора"),
            description=tr(
                "Проверяет обязательные файлы: .shp + .dbf + .shx, "
                ".mif + .mid, .tab + .dat/.map/.id."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_CRS_QUALITY,
            label=tr("Проверка системы координат"),
            description=tr(
                "Ищет файлы без системы координат, с неизвестной или "
                "смешанной системой координат."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_GEOMETRY_VALIDITY,
            label=tr("Проверка валидности геометрий"),
            description=tr(
                "Ищет самопересечения, незамкнутые кольца, пустые и "
                "null-геометрии."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_COORDINATE_RANGE,
            label=tr("Проверка координат"),
            description=tr(
                "Ищет NaN/Inf, слишком большие координаты, перепутанные "
                "широту и долготу и выход за допустимый диапазон CRS."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_EMPTY_LAYERS,
            label=tr("Проверка пустых слоёв"),
            description=tr(
                "Ищет пустые слои и файлы с нулевым количеством объектов."
            ),
            checked=False,
        ),
    ]

    if include_json_check:
        attribute_index = next(
            index
            for index, definition in enumerate(definitions)
            if definition.key == CHECK_ATTRIBUTE_NAMES
        )
        definitions.insert(
            attribute_index,
            CheckDefinition(
                key=CHECK_JSON_GEOJSON,
                label=tr("Проверка JSON на формат GEOJSON"),
                description=tr(
                    "Проверяет файлы .json и .geojson по полю type. "
                    "Файлы, не являющиеся GeoJSON, исключаются из списка."
                ),
            ),
        )

    return definitions


class ChecksDialog(QDialog):
    """Окно выбора проверок перед их выполнением."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        include_json_check: bool = True,
    ) -> None:
        super().__init__(parent)
        self._checkboxes: Dict[str, QCheckBox] = {}
        self._info_buttons: Dict[str, QToolButton] = {}
        self._definitions = check_definitions(include_json_check)

        self.setWindowTitle(tr("Проверки"))
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(680, 640)
        self.setMinimumSize(580, 460)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        title = QLabel(tr("Выберите проверки"))
        self._set_font(title, 3, bold=True)
        layout.addWidget(title)

        hint = QLabel(
            tr(
                "Отметьте проверки, которые нужно выполнить для "
                "найденных файлов."
            )
        )
        hint.setWordWrap(True)
        self._set_font(hint, -1)
        layout.addWidget(hint)

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)

        for row, definition in enumerate(self._definitions):
            checkbox = QCheckBox(definition.label)
            checkbox.setChecked(definition.checked)
            checkbox.toggled.connect(self._update_run_button)
            self._checkboxes[definition.key] = checkbox
            grid.addWidget(checkbox, row, 0)

            info_button = QToolButton()
            info_button.setText("i")
            info_button.setObjectName("zgeoCheckInfoButton")
            info_button.setAutoRaise(True)
            info_button.setFixedSize(24, 24)
            info_button.setToolTip(definition.description)
            info_button.setToolTipDuration(10000)
            info_button.setAccessibleName(
                tr("Описание проверки: {}", definition.label)
            )
            info_button.setAccessibleDescription(definition.description)
            info_button.setCursor(Qt.CursorShape.PointingHandCursor)
            info_font = QFont(info_button.font())
            info_font.setPointSizeF(max(10.0, info_font.pointSizeF() + 2.0))
            info_font.setBold(True)
            info_button.setFont(info_font)
            self._info_buttons[definition.key] = info_button
            grid.addWidget(
                info_button,
                row,
                1,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.run_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.run_button.setText(tr("Выполнить"))
        self.run_button.setDefault(True)
        self.run_button.setAutoDefault(True)
        self.cancel_button.setText(tr("Отмена"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_run_button()

    def selected_checks(self) -> List[str]:
        """Вернуть ключи отмеченных проверок в порядке списка."""

        return [
            definition.key
            for definition in self._definitions
            if self._checkboxes[definition.key].isChecked()
        ]

    def _update_run_button(self) -> None:
        self.run_button.setEnabled(bool(self.selected_checks()))

    def _set_font(
        self, widget: QWidget, size_delta: int, bold: bool = False
    ) -> None:
        font = QFont(widget.font())
        point_size = widget.font().pointSizeF()
        if point_size <= 0:
            point_size = 10.0
        font.setPointSizeF(max(7.0, point_size + size_delta))
        font.setBold(bold)
        widget.setFont(font)
