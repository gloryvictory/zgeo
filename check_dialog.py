"""Диалог выбора проверок ZGeo."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTextBrowser,
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
CHECK_METADATA_CRS = "metadata_crs"
CHECK_PRJ = "prj_file"
CHECK_GEOMETRY = "geometry_quality"
CHECK_COORDINATES = "coordinates_quality"
CHECK_DUPLICATES = "duplicate_features"
CHECK_FILE_PATHS = "file_paths"

PROBLEM_CHECKS = frozenset(
    {
        CHECK_FILE_PATHS,
        CHECK_CRS_QUALITY,
        CHECK_COUNT_QUALITY,
        CHECK_FIELD_NAMES,
        CHECK_DATASET_INTEGRITY,
        CHECK_METADATA_CRS,
        CHECK_PRJ,
        CHECK_GEOMETRY,
        CHECK_DUPLICATES,
        CHECK_COORDINATES,
    }
)

LAYER_PROBLEM_CHECKS = frozenset(
    {
        CHECK_CRS_QUALITY,
        CHECK_COUNT_QUALITY,
        CHECK_FIELD_NAMES,
        CHECK_METADATA_CRS,
        CHECK_PRJ,
        CHECK_GEOMETRY,
        CHECK_DUPLICATES,
        CHECK_COORDINATES,
    }
)


@dataclass(frozen=True)
class CheckDefinition:
    """Описание одной проверки."""

    key: str
    label: str
    description: str
    checked: bool = True
    details: Tuple[str, ...] = ()
    examples: Tuple[str, ...] = ()


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
            details=(
                tr(
                    "Для каждого файла ZGeo складывает размер основного "
                    "файла и всех связанных файлов набора в той же папке. "
                    "Значения берутся из файловой системы и заменяют "
                    "приблизительный размер, показанный после сканирования."
                ),
                tr(
                    "В колонке «Размер» и в отчётах показывается полный "
                    "объём набора. Если связанный файл отсутствует, "
                    "учитываются только существующие файлы."
                ),
            ),
            examples=(
                tr(
                    "roads.shp + roads.shx + roads.dbf + roads.prj + "
                    "roads.cpg — полный размер Shapefile."
                ),
                tr(
                    "roads.mif + roads.mid — полный размер MapInfo MIF/MID."
                ),
                tr(
                    "dem.tif + dem.tif.aux.xml + dem.tif.ovr + dem.tfw — "
                    "полный размер растрового набора."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_FILE_PATHS,
            label=tr("Проверка имён и путей файлов"),
            description=tr(
                "Проверяет длину пути, недопустимые символы и "
                "зарезервированные имена, совпадения имён без учёта "
                "регистра и осиротевшие сопутствующие файлы."
            ),
            checked=False,
            details=(
                tr(
                    "Для каждого найденного файла проверяются длина "
                    "полного пути (больше 260 символов — ограничение "
                    "Windows), символы <>:\"|?* и управляющие символы в "
                    "имени, зарезервированные имена (CON, PRN, AUX, NUL, "
                    "COM1-9, LPT1-9) и завершение имени пробелом или "
                    "точкой."
                ),
                tr(
                    "В каждой папке ZGeo ищет файлы, имена которых "
                    "различаются только регистром, а также осиротевшие "
                    "сопутствующие файлы: roads.dbf, roads.prj, "
                    "dem.tif.aux.xml и подобные без основного файла "
                    "набора."
                ),
                tr(
                    "Проверка только сообщает о проблемах и не "
                    "переименовывает файлы. Результаты по папке "
                    "показываются один раз — у первого файла папки."
                ),
            ),
            examples=(
                tr(
                    "Путь в 275 символов — отмечается превышение "
                    "ограничения Windows."
                ),
                tr(
                    "В папке есть roads.dbf без roads.shp — отмечается "
                    "осиротевший сопутствующий файл."
                ),
                tr(
                    "Файлы Roads.shp и roads.shp различаются только "
                    "регистром — отмечается совпадение имён."
                ),
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
            details=(
                tr(
                    "ZGeo открывает каждый слой через провайдеры QGIS, "
                    "читает его систему координат и записывает название в "
                    "колонку «Система координат»."
                ),
                tr(
                    "Проверка отмечает файлы, у которых система координат "
                    "не определена или неизвестна, а также файлы, в "
                    "которых слои используют разные системы координат."
                ),
                tr(
                    "Для растров система координат читается из метаданных "
                    "растра; если её нет, значение остаётся неопределённым."
                ),
            ),
            examples=(
                tr(
                    "EPSG:3857 — WGS 84 / Pseudo-Mercator: проблема не "
                    "найдена."
                ),
                tr(
                    "Пустое значение или «Не определена»: файл помечается "
                    "как проблемный."
                ),
                tr(
                    "Два слоя GeoPackage с EPSG:3857 и EPSG:4326: "
                    "отмечается смешанная система координат."
                ),
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
            details=(
                tr(
                    "Для каждого слоя ZGeo считает объекты через "
                    "провайдеры QGIS и обновляет колонку «Элементов»."
                ),
                tr(
                    "Пустой слой отмечается отдельно. Если в файле нет ни "
                    "одного объекта, файл помечается как не содержащий "
                    "объектов."
                ),
                tr(
                    "Для растров количество элементов не подсчитывается."
                ),
            ),
            examples=(
                tr(
                    "Слой roads: 1 245 объектов — проблема не найдена."
                ),
                tr(
                    "Слой buildings: 0 объектов — отмечается пустой слой."
                ),
                tr(
                    "GeoPackage из двух пустых слоёв: файл помечается как "
                    "не содержащий объектов."
                ),
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
            details=(
                tr(
                    "Для векторных слоёв ZGeo читает имена атрибутивных "
                    "полей и проверяет нелатинские символы, длину больше "
                    "10 символов (ограничение DBF), пробелы и символы, "
                    "кроме букв, цифр и подчёркивания."
                ),
                tr(
                    "Отдельно ищутся имена, которые совпадают после "
                    "усечения до 10 символов."
                ),
                tr("Для растров проверка не применяется."),
            ),
            examples=(
                tr(
                    "Поле «Наименование»: нелатинские символы — "
                    "отмечается."
                ),
                tr(
                    "Поле very_long_field_name: длина больше 10 символов — "
                    "отмечается."
                ),
                tr(
                    "Поля population_2024 и population_2025: после "
                    "усечения до 10 символов совпадают — отмечается дубль."
                ),
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
            details=(
                tr(
                    "ZGeo проверяет обязательные файлы набора: для SHP — "
                    ".dbf и .shx, для MIF — .mid, для TAB — .dat, .map и "
                    ".id."
                ),
                tr(
                    "Для SHP дополнительно проверяется наличие .cpg и "
                    "корректность указанной в нём кодировки DBF."
                ),
                tr(
                    "Проверка не меняет список файлов и ищет "
                    "сопутствующие файлы в той же папке."
                ),
            ),
            examples=(
                tr(
                    "roads.shp без roads.dbf и roads.shx — отмечается "
                    "отсутствие файлов набора."
                ),
                tr(
                    "roads.shp + roads.dbf + roads.shx без roads.cpg — "
                    "отмечается отсутствие .cpg."
                ),
                tr(
                    "roads.cpg с текстом UTF-8 — кодировка распознана; с "
                    "текстом x-unknown — отмечается неизвестная кодировка."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_METADATA_CRS,
            label=tr("Проверка метаданных и CRS"),
            description=tr(
                "Проверяет наличие .prj и .cpg у SHP, .aux.xml и .ovr "
                "у растров, файла привязки .tfw/.tifw/.wld при "
                "отсутствии CRS, а также устаревшие CRS, единицы и "
                "порядок осей."
            ),
            checked=False,
            details=(
                tr(
                    "Для SHP проверяется наличие .prj (или .qpj) и .cpg. "
                    "Для растров проверяется наличие .aux.xml и .ovr, а "
                    "если система координат не определена — файла "
                    "привязки .tfw, .tifw или .wld."
                ),
                tr(
                    "Для слоёв проверяются устаревшие системы координат, "
                    "отсутствие кода EPSG или другого авторитета, "
                    "неметрические единицы у проекционных систем, не "
                    "градусы у географических систем и нестандартный "
                    "порядок осей YX."
                ),
            ),
            examples=(
                tr(
                    "roads.shp без roads.prj — отмечается отсутствие "
                    "метаданных системы координат."
                ),
                tr(
                    "dem.tif без dem.tif.aux.xml и dem.tif.ovr — "
                    "отмечаются отсутствующие вспомогательные метаданные."
                ),
                tr(
                    "Слой в EPSG:3857 с единицами «футы» — отмечаются "
                    "неметрические единицы."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_PRJ,
            label=tr("Проверка .prj-файла"),
            description=tr(
                "Проверяет наличие файла .prj, его читаемость и "
                "согласованность с системой координат слоя."
            ),
            checked=False,
            details=(
                tr(
                    "ZGeo ищет файл .prj рядом с набором данных и "
                    "разбирает его содержимое как WKT: проверяются "
                    "наличие, кодировка, пустой файл, парность скобок и "
                    "корневой тип системы координат."
                ),
                tr(
                    "Затем сведения из .prj сравниваются с системой "
                    "координат слоя: тип (географическая или "
                    "проекционная) и код EPSG, если он указан в .prj."
                ),
                tr(
                    "Если файла .prj нет, но есть .qpj, замечание не "
                    "выводится: QGIS использует .qpj как замену."
                ),
            ),
            examples=(
                tr(
                    "roads.prj с WKT EPSG:3857 и слой в EPSG:3857 — "
                    "проблема не найдена."
                ),
                tr(
                    "Пустой roads.prj — отмечается «Файл .prj пуст»."
                ),
                tr(
                    "В .prj географическая система, а слой в "
                    "проекционной — отмечается несовпадение типа CRS."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_GEOMETRY,
            label=tr("Проверка валидности геометрий"),
            description=tr(
                "Ищет самопересечения, незамкнутые кольца, пустые и "
                "null-геометрии."
            ),
            checked=False,
            details=(
                tr(
                    "Для каждого векторного слоя ZGeo перебирает объекты "
                    "и проверяет геометрию: null и пустые геометрии, "
                    "незамкнутые кольца, самопересечения и прочие ошибки "
                    "валидности."
                ),
                tr(
                    "Итоги группируются по слою, а для найденных ошибок "
                    "сохраняются номер объекта и место ошибки; подробно "
                    "описывается до 1000 ошибок на слой."
                ),
            ),
            examples=(
                tr(
                    "Полигон с самопересечением — отмечается "
                    "«Самопересечение»."
                ),
                tr(
                    "Кольцо, у которого первая и последняя вершины не "
                    "совпадают — отмечается «Незамкнутое кольцо»."
                ),
                tr(
                    "Объект без геометрии — отмечается «Геометрия "
                    "отсутствует (null)»."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_DUPLICATES,
            label=tr("Проверка дублей объектов"),
            description=tr(
                "Ищет объекты с полностью совпадающей геометрией."
            ),
            checked=False,
            details=(
                tr(
                    "Для каждого векторного слоя ZGeo сравнивает "
                    "геометрию объектов побайтово: в ключ входит тип "
                    "геометрии, число вершин и все координаты, включая Z."
                ),
                tr(
                    "Пустые и null-геометрии не сравниваются. Для групп "
                    "совпадений показывается первый объект и номера его "
                    "дублей; подробно описывается до 1000 дублей на слой."
                ),
                tr(
                    "Объекты с одинаковыми координатами, но разными "
                    "атрибутами тоже считаются дублями геометрии: ZGeo "
                    "сравнивает только геометрию."
                ),
            ),
            examples=(
                tr(
                    "Два полигона с одинаковым набором вершин — второй "
                    "отмечается как «Дубль геометрии объекта 1»."
                ),
                tr(
                    "Объекты с одинаковым контуром, но разными "
                    "атрибутами — тоже дубль геометрии."
                ),
                tr(
                    "Объекты с совпадающими координатами, но разным "
                    "порядком вершин — не дубли."
                ),
            ),
        ),
        CheckDefinition(
            key=CHECK_COORDINATES,
            label=tr("Проверка координат"),
            description=tr(
                "Ищет NaN/Inf, слишком большие значения, перепутанные "
                "широту и долготу и координаты вне допустимого диапазона "
                "CRS."
            ),
            checked=False,
            details=(
                tr(
                    "Для каждой вершины объекта координаты проверяются на "
                    "NaN и бесконечность, на абсолютные значения больше "
                    "1e9, на перепутанные широту и долготу и на выход за "
                    "диапазон CRS."
                ),
                tr(
                    "Для географических систем координат долгота должна "
                    "быть в пределах от -180 до 180, широта — от -90 до "
                    "90. Для проекционных систем вершина преобразуется в "
                    "WGS 84 и проверяется попадание в границы системы "
                    "координат."
                ),
                tr(
                    "Итоги группируются по слою, а для найденных ошибок "
                    "сохраняются номер объекта и вершины; подробно "
                    "описывается до 1000 ошибок на слой."
                ),
            ),
            examples=(
                tr(
                    "Вершина с координатой NaN — отмечается «Координата "
                    "NaN/Inf»."
                ),
                tr(
                    "Координата (500, 95) в географической системе — "
                    "отмечается «Похоже на перепутанные широту и долготу»."
                ),
                tr(
                    "Координата с абсолютным значением больше 1e9 — "
                    "отмечается «Слишком большая координата»."
                ),
            ),
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
                details=(
                    tr(
                        "ZGeo читает каждый файл .json и .geojson и "
                        "проверяет структуру по полю type: допустимые типы "
                        "геометрий, Feature, FeatureCollection и "
                        "GeometryCollection, а также обязательные "
                        "вложенные поля features и geometries."
                    ),
                    tr(
                        "Содержимое координат не анализируется. Файлы, "
                        "которые не читаются как JSON или не являются "
                        "GeoJSON, исключаются из списка и не участвуют в "
                        "остальных проверках."
                    ),
                ),
                examples=(
                    tr(
                        '{"type": "FeatureCollection", "features": [...]} '
                        "— GeoJSON, файл остаётся в списке."
                    ),
                    tr(
                        '{"type": "Feature", "geometry": {...}, '
                        '"properties": {...}} — GeoJSON, файл остаётся.'
                    ),
                    tr(
                        '{"name": "settings", "values": [...]} — не '
                        "GeoJSON, файл исключается."
                    ),
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
                "найденных файлов. Нажмите «i» справа, чтобы открыть "
                "подробное описание с примерами."
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
            info_button.clicked.connect(
                lambda _checked=False, key=definition.key: (
                    self._show_details_for(key)
                )
            )
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

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)
        body.addWidget(scroll, 1)

        self._details_panel = self._build_details_panel()
        self._details_panel.setVisible(False)
        body.addWidget(self._details_panel)

        layout.addLayout(body, 1)

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

    def _build_details_panel(self) -> QFrame:
        """Создать панель подробного описания проверки."""

        panel = QFrame()
        panel.setObjectName("zgeoCheckDetailsPanel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(430)
        panel.setAccessibleName(tr("Подробное описание проверки"))

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 10, 12, 12)
        panel_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        header_label = QLabel(tr("Подробное описание"))
        self._set_font(header_label, -1, bold=True)
        header.addWidget(header_label)
        header.addStretch(1)

        close_button = QToolButton()
        close_button.setObjectName("zgeoCheckDetailsCloseButton")
        close_button.setText("×")
        close_button.setAutoRaise(True)
        close_button.setFixedSize(24, 24)
        close_button.setToolTip(tr("Закрыть описание"))
        close_button.setAccessibleName(tr("Закрыть описание"))
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self._hide_details)
        header.addWidget(close_button)

        panel_layout.addLayout(header)

        self._details_browser = QTextBrowser()
        self._details_browser.setObjectName("zgeoCheckDetailsText")
        self._details_browser.setFrameShape(QFrame.Shape.NoFrame)
        self._details_browser.setOpenExternalLinks(False)
        self._details_browser.setReadOnly(True)
        self._details_browser.setAccessibleName(
            tr("Подробное описание проверки")
        )
        self._details_browser.setStyleSheet(
            "QTextBrowser { background: transparent; }"
        )
        panel_layout.addWidget(self._details_browser, 1)
        return panel

    def _show_details_for(self, key: str) -> None:
        """Показать подробное описание проверки по её ключу."""

        for definition in self._definitions:
            if definition.key == key:
                self._show_details(definition)
                return

    def _show_details(self, definition: CheckDefinition) -> None:
        """Заполнить и открыть панель подробного описания."""

        self._details_browser.setHtml(self._details_html(definition))
        self._details_browser.verticalScrollBar().setValue(0)
        was_hidden = not self._details_panel.isVisible()
        self._details_panel.setVisible(True)
        if was_hidden and self.isVisible():
            self.resize(max(self.width(), 960), max(self.height(), 580))

    def _hide_details(self) -> None:
        """Закрыть панель подробного описания."""

        self._details_panel.setVisible(False)
        if self.isVisible():
            self.resize(640, max(self.height(), 480))

    def _details_html(self, definition: CheckDefinition) -> str:
        """Собрать HTML для панели подробного описания."""

        parts = [
            '<h3 style="margin-top: 0;">{}</h3>'.format(
                html.escape(definition.label)
            ),
            "<p>{}</p>".format(html.escape(definition.description)),
        ]

        if definition.details:
            parts.append(
                "<p><b>{}</b></p>".format(
                    html.escape(tr("Что будет сделано"))
                )
            )
            parts.extend(
                "<p>{}</p>".format(html.escape(paragraph))
                for paragraph in definition.details
            )

        if definition.examples:
            parts.append(
                "<p><b>{}</b></p>".format(html.escape(tr("Примеры")))
            )
            parts.append("<ul>")
            parts.extend(
                "<li><tt>{}</tt></li>".format(html.escape(example))
                for example in definition.examples
            )
            parts.append("</ul>")

        return "".join(parts)

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
