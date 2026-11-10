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
    QGridLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr

ICON_PATH = Path(__file__).with_name("icon.svg")

CHECK_ATTRIBUTE_NAMES = "attribute_names"
CHECK_REFINE_DATA = "refine_data"


@dataclass(frozen=True)
class CheckDefinition:
    """Описание одной проверки."""

    key: str
    label: str
    description: str
    checked: bool = True


def check_definitions() -> List[CheckDefinition]:
    """Вернуть проверки с учётом текущего языка интерфейса."""

    return [
        CheckDefinition(
            key=CHECK_ATTRIBUTE_NAMES,
            label=tr("Проверка имён атрибутивных полей"),
            description=tr(
                "Проверяет имена полей векторных файлов и добавляет "
                "колонку «Проблемы с атрибутами». Если в имени поля есть "
                "нелатинские символы, ставится «Да», иначе «Нет»; для "
                "растровых файлов — «—»."
            ),
        ),
        CheckDefinition(
            key=CHECK_REFINE_DATA,
            label=tr("Уточнение характеристик и объёмов"),
            description=tr(
                "Читает систему координат, количество элементов и полный "
                "объём наборов данных с учётом сопутствующих файлов."
            ),
            checked=False,
        ),
    ]


class ChecksDialog(QDialog):
    """Окно выбора проверок перед их выполнением."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._checkboxes: Dict[str, QCheckBox] = {}
        self._info_buttons: Dict[str, QToolButton] = {}
        self._definitions = check_definitions()

        self.setWindowTitle(tr("Проверки данных"))
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(580, 250)
        self.setMinimumWidth(520)

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

        grid = QGridLayout()
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

        layout.addLayout(grid)
        layout.addStretch(1)

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
