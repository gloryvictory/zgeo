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
CHECK_JSON_GEOJSON = "json_geojson"
CHECK_CRS_QUALITY = "crs_quality"
CHECK_COUNT_QUALITY = "count_quality"
CHECK_FIELD_NAMES = "field_names"
CHECK_DATASET_INTEGRITY = "dataset_integrity"
CHECK_GEOMETRY_COORDINATES = "geometry_coordinates"

PROBLEM_CHECKS = frozenset(
    {
        CHECK_CRS_QUALITY,
        CHECK_COUNT_QUALITY,
        CHECK_FIELD_NAMES,
        CHECK_DATASET_INTEGRITY,
        CHECK_GEOMETRY_COORDINATES,
    }
)

LAYER_PROBLEM_CHECKS = frozenset(
    {
        CHECK_CRS_QUALITY,
        CHECK_COUNT_QUALITY,
        CHECK_FIELD_NAMES,
        CHECK_GEOMETRY_COORDINATES,
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
            key=CHECK_CRS_QUALITY,
            label=tr("Уточнить систему координат и проверить СК"),
            description=tr(
                "Читает систему координат слоёв, обновляет колонку "
                "«Система координат» и отмечает отсутствующую, неизвестную "
                "или смешанную СК."
            ),
        ),
        CheckDefinition(
            key=CHECK_COUNT_QUALITY,
            label=tr(
                "Уточнить количество элементов и проверить пустые слои"
            ),
            description=tr(
                "Считает количество элементов, обновляет колонку "
                "«Элементов» и отмечает пустые слои и файлы без объектов."
            ),
        ),
        CheckDefinition(
            key=CHECK_FIELD_NAMES,
            label=tr("Проверка имён полей"),
            description=tr(
                "Проверяет нелатинские символы, длину имени (не более "
                "10 символов DBF), пробелы, недопустимые символы и дубли "
                "после усечения."
            ),
        ),
        CheckDefinition(
            key=CHECK_DATASET_INTEGRITY,
            label=tr("Проверка набора данных"),
            description=tr(
                "Проверяет обязательные файлы набора, наличие .cpg и "
                "корректность указанной кодировки DBF."
            ),
            checked=False,
        ),
        CheckDefinition(
            key=CHECK_GEOMETRY_COORDINATES,
            label=tr("Проверка геометрий и координат"),
            description=tr(
                "Ищет самопересечения, незамкнутые кольца, пустые и "
                "null-геометрии, NaN/Inf, слишком большие координаты, "
                "перепутанные широту и долготу и выход за диапазон CRS."
            ),
            checked=False,
        ),
    ]

    if include_json_check:
        field_index = next(
            index
            for index, definition in enumerate(definitions)
            if definition.key == CHECK_FIELD_NAMES
        )
        definitions.insert(
            field_index,
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
        self.resize(640, 480)
        self.setMinimumSize(540, 380)

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
