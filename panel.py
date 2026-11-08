"""Плавающая панель ZGeo."""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set, Tuple

from qgis.PyQt.QtCore import (
    QFileInfo,
    QSettings,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
)
from qgis.PyQt.QtGui import QFont, QIcon, QPalette
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .charts import BarChart, BarDatum
from .dataset_size import DirectoryIndex, measure_geo_file_cached
from .explorer import reveal_files
from .file_info import (
    AttributeCheck,
    LayerSummary,
    inspect_attribute_names,
    inspect_geofile,
    inspect_layer_summary,
)
from .formatting import format_size
from .info_dialog import FileInfoDialog
from .scan_task import ScanTask
from .scanner import (
    DEFAULT_DISABLED_FORMATS,
    OTHER,
    RASTER,
    TABLE,
    VECTOR,
    FormatGroup,
    GeoFile,
    get_format_groups,
)
from .stats import build_size_distribution, build_type_distribution
from .table_export import (
    export_rows_with_dialog,
    export_table_with_dialog,
)
from .version import get_plugin_version

CATEGORY_LABELS = {
    VECTOR: "Векторные данные",
    RASTER: "Растровые данные",
    TABLE: "Таблица",
    OTHER: "Прочие данные",
}

LAST_FOLDER_KEY = "zgeo/last_folder"
DISABLED_FORMATS_KEY = "zgeo/disabled_formats"
ICON_PATH = Path(__file__).with_name("icon.svg")
ATTRIBUTE_CHECK_TOOLTIP = (
    "Проверить атрибуты: проверить имена полей векторных файлов "
    "и добавить колонку «Проблемы с атрибутами».\n"
    "Если в названии поля есть нелатинские символы (например, "
    "кириллица) — «Да»; если проблем нет — «Нет»; для растровых "
    "файлов — «—»."
)
SIZE_CHART_COLOR = "#0F766E"
TYPE_CHART_COLORS = (
    "#0F766E",
    "#D97706",
    "#2563EB",
    "#7C3AED",
    "#DB2777",
    "#0891B2",
    "#65A30D",
    "#64748B",
)


class ZGeoPanel(QDockWidget):
    """Каталог пространственных файлов, открываемый как плавающая панель."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._folder: Optional[Path] = None
        self._files: List[GeoFile] = []
        self._file_by_path: Dict[str, GeoFile] = {}
        self._entries: List[Tuple[QTreeWidgetItem, str]] = []
        self._item_by_path: Dict[str, QTreeWidgetItem] = {}
        self._element_counts: Dict[str, int] = {}
        self._file_index_by_path: Dict[str, int] = {}
        self._size_index_cache: Dict[str, DirectoryIndex] = {}
        self._scan_task: Optional[ScanTask] = None
        self._busy = False
        self._settings = QSettings()
        self._format_checkboxes: Dict[str, QCheckBox] = {}
        self._disabled_formats = self._load_disabled_formats()
        self._icon_provider = QFileIconProvider()
        self._icon_cache: Dict[str, QIcon] = {}

        self._details_queue: Deque[GeoFile] = deque()
        self._details_total = 0
        self._details_processed = 0
        self._details_paused = False
        self._details_timer = QTimer(self)
        self._details_timer.setSingleShot(True)
        self._details_timer.setInterval(0)
        self._details_timer.timeout.connect(self._process_next_detail)

        self._attribute_running = False
        self._attribute_checked = False
        self._attribute_queue: Deque[GeoFile] = deque()
        self._attribute_total = 0
        self._attribute_processed = 0
        self._attribute_issue_count = 0
        self._attribute_timer = QTimer(self)
        self._attribute_timer.setSingleShot(True)
        self._attribute_timer.setInterval(0)
        self._attribute_timer.timeout.connect(
            self._process_next_attribute_check
        )

        self.setObjectName("ZGeoPanel")
        self.setWindowTitle("ZGeo — геоданные")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.setMinimumWidth(520)
        self.resize(720, 700)

        self._build_ui()
        self._update_controls()
        self._set_empty(
            "Геоданные не выбраны",
            "Нажмите «Выбрать папку», чтобы найти шейпфайлы, GeoPackage "
            "и другие пространственные данные.",
        )
        self._set_stats_empty(
            "Статистика пуста",
            "Выберите папку и выполните сканирование. Здесь появятся "
            "диаграммы по размеру и типу файлов.",
        )

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("zgeoRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        layout.addLayout(self._build_brand())
        layout.addSpacing(3)

        caption = QLabel("ПАПКА")
        self._set_font(caption, -1, bold=True)
        self._set_muted(caption)
        layout.addWidget(caption)

        self.folder_name_label = QLabel("Папка не выбрана")
        self.folder_name_label.setObjectName("zgeoFolderName")
        self.folder_name_label.setWordWrap(True)
        self.folder_name_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.folder_name_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._set_font(self.folder_name_label, 3, bold=True)
        layout.addWidget(self.folder_name_label)

        self.folder_path_label = QLabel("Выберите каталог на диске")
        self.folder_path_label.setWordWrap(True)
        self.folder_path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.folder_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._set_font(self.folder_path_label, -1)
        self._set_muted(self.folder_path_label)
        layout.addWidget(self.folder_path_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)

        self.choose_button = QPushButton("Выбрать папку")
        self.choose_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self.choose_button.setMinimumHeight(32)
        self.choose_button.clicked.connect(self.choose_folder)
        buttons.addWidget(self.choose_button, 1)

        self.refresh_button = QToolButton()
        self.refresh_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.refresh_button.setIconSize(QSize(18, 18))
        self.refresh_button.setAutoRaise(True)
        self.refresh_button.setFixedSize(32, 32)
        self.refresh_button.setToolTip("Пересканировать папку")
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_button)

        layout.addLayout(buttons)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_files_page(), "Файлы")
        self.tabs.addTab(self._build_stats_page(), "Статистика")
        self.tabs.addTab(self._build_settings_page(), "Настройки")
        self.tabs.setTabToolTip(
            0, "Найденные пространственные файлы"
        )
        self.tabs.setTabToolTip(
            1, "Диаграммы по размеру и типу файлов"
        )
        self.tabs.setTabToolTip(
            2, "Форматы файлов, которые нужно искать"
        )
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self._build_status_bar())

        self.setWidget(root)

    def _build_status_bar(self) -> QStatusBar:
        bar = QStatusBar()
        self.status_bar = bar
        bar.setObjectName("zgeoStatusBar")
        bar.setSizeGripEnabled(False)
        bar.setContentsMargins(0, 0, 0, 0)

        self.status_message_label = QLabel("Готово")
        self.status_message_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.status_message_label, -1)
        bar.addWidget(self.status_message_label, 1)

        self.selection_label = QLabel("Выбрано: 0 из 0")
        self.selection_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.selection_label.setMinimumWidth(150)
        self._set_font(self.selection_label, -1)
        bar.addPermanentWidget(self.selection_label)
        return bar

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self.summary_label = QLabel("Файлов: 0 · Общий объем: 0 Б")
        self._set_font(self.summary_label, 0, bold=True)
        layout.addWidget(self.summary_label)

        self.problems_label = QLabel("Проблемных файлов: 0")
        self._set_font(self.problems_label, -1)
        self.problems_label.setVisible(False)
        layout.addWidget(self.problems_label)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр по имени, формату или пути")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_edit, 1)

        self.problems_only_checkbox = QCheckBox("Только проблемные")
        self.problems_only_checkbox.setToolTip(
            "Показывать только файлы, у которых проверка атрибутов "
            "нашла проблемы"
        )
        self.problems_only_checkbox.setEnabled(False)
        self.problems_only_checkbox.toggled.connect(
            self._on_problems_filter_toggled
        )
        filter_row.addWidget(self.problems_only_checkbox)

        layout.addLayout(filter_row)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_tree())
        self.scan_page = self._build_scan_page()
        self.stack.addWidget(self.scan_page)
        self.stack.setMinimumHeight(260)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self._build_file_actions())
        self.tree.itemSelectionChanged.connect(self._update_file_actions)
        return page

    def _build_file_actions(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(3)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        self.info_button = QToolButton()
        self.info_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        )
        self.info_button.setIconSize(QSize(18, 18))
        self.info_button.setAutoRaise(True)
        self.info_button.setFixedSize(30, 30)
        self.info_button.setToolTip("Информация")
        self.info_button.setAccessibleName("Информация")
        self.info_button.clicked.connect(self._show_file_info)
        buttons.addWidget(self.info_button)

        self.explorer_button = QToolButton()
        self.explorer_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DirOpenIcon
            )
        )
        self.explorer_button.setIconSize(QSize(18, 18))
        self.explorer_button.setAutoRaise(True)
        self.explorer_button.setFixedSize(30, 30)
        self.explorer_button.setToolTip("Открыть в проводнике")
        self.explorer_button.setAccessibleName("Открыть в проводнике")
        self.explorer_button.clicked.connect(self._open_in_explorer)
        buttons.addWidget(self.explorer_button)

        self.export_list_button = QToolButton()
        self.export_list_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogSaveButton
            )
        )
        self.export_list_button.setIconSize(QSize(18, 18))
        self.export_list_button.setAutoRaise(True)
        self.export_list_button.setFixedSize(30, 30)
        self.export_list_button.setToolTip("Экспорт в Excel")
        self.export_list_button.setAccessibleName("Экспорт в Excel")
        self.export_list_button.clicked.connect(self._export_file_list)
        buttons.addWidget(self.export_list_button)

        self.check_attributes_button = QToolButton()
        self.check_attributes_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogApplyButton
            )
        )
        self.check_attributes_button.setIconSize(QSize(18, 18))
        self.check_attributes_button.setAutoRaise(True)
        self.check_attributes_button.setFixedSize(30, 30)
        self.check_attributes_button.setToolTip(
            ATTRIBUTE_CHECK_TOOLTIP
        )
        self.check_attributes_button.setAccessibleName(
            "Проверить атрибуты"
        )
        self.check_attributes_button.clicked.connect(
            self._start_attribute_check
        )
        buttons.addWidget(self.check_attributes_button)

        self.cancel_task_button = QToolButton()
        self.cancel_task_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogCancelButton
            )
        )
        self.cancel_task_button.setIconSize(QSize(18, 18))
        self.cancel_task_button.setAutoRaise(True)
        self.cancel_task_button.setFixedSize(30, 30)
        self.cancel_task_button.setToolTip("Прервать длительную операцию")
        self.cancel_task_button.setAccessibleName("Прервать операцию")
        self.cancel_task_button.setVisible(False)
        self.cancel_task_button.clicked.connect(
            self._cancel_long_operation
        )
        buttons.addWidget(self.cancel_task_button)

        buttons.addStretch(1)

        layout.addLayout(buttons)
        return container

    def _build_stats_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)

        self.stats_stack = QStackedWidget()
        self.stats_stack.addWidget(self._build_stats_empty_page())
        self.stats_content_widget = self._build_stats_content()
        self.stats_stack.addWidget(self.stats_content_widget)
        layout.addWidget(self.stats_stack, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(6)
        self.select_all_button = QPushButton("Выбрать все")
        self.select_all_button.setToolTip("Отметить все форматы")
        self.select_all_button.clicked.connect(self._select_all_formats)
        self.clear_all_button = QPushButton("Сбросить все")
        self.clear_all_button.setToolTip("Снять все отметки")
        self.clear_all_button.clicked.connect(self._clear_all_formats)
        self.only_vector_button = QPushButton("Только вектор")
        self.only_vector_button.setToolTip(
            "Оставить только векторные форматы"
        )
        self.only_vector_button.clicked.connect(self._select_only_vector)
        self.only_raster_button = QPushButton("Только растр")
        self.only_raster_button.setToolTip(
            "Оставить только растровые форматы"
        )
        self.only_raster_button.clicked.connect(self._select_only_raster)
        for button in (
            self.select_all_button,
            self.clear_all_button,
            self.only_vector_button,
            self.only_raster_button,
        ):
            button.setMinimumHeight(28)
            quick_actions.addWidget(button, 1)
        layout.addLayout(quick_actions)

        hint = QLabel(
            "Отметьте форматы, которые должны попадать в каталог. "
            "Изменения применяются при следующем сканировании."
        )
        hint.setWordWrap(True)
        self._set_font(hint, -1)
        self._set_muted(hint)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        groups = get_format_groups()
        for category, category_label in CATEGORY_LABELS.items():
            category_groups = [
                group for group in groups
                if group.category == category
            ]
            if not category_groups:
                continue

            group_box = QGroupBox(category_label)
            group_layout = QVBoxLayout(group_box)
            group_layout.setSpacing(5)

            for group in category_groups:
                checkbox = QCheckBox(
                    self._format_checkbox_text(group)
                )
                checkbox.setChecked(
                    group.name not in self._disabled_formats
                )
                checkbox.setToolTip(
                    "Расширения: {}".format(
                        ", ".join(group.extensions)
                    )
                )
                checkbox.toggled.connect(
                    lambda checked, name=group.name: (
                        self._on_format_toggled(name, checked)
                    )
                )
                self._format_checkboxes[group.name] = checkbox
                group_layout.addWidget(checkbox)

            content_layout.addWidget(group_box)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return page

    @staticmethod
    def _format_checkbox_text(group: FormatGroup) -> str:
        return "{} ({})".format(
            group.name, ", ".join(group.extensions)
        )

    def _load_disabled_formats(self) -> Set[str]:
        value = self._settings.value(DISABLED_FORMATS_KEY, None)
        if value is None:
            return set(DEFAULT_DISABLED_FORMATS)
        if isinstance(value, (list, tuple)):
            return {
                str(item) for item in value if str(item).strip()
            }
        return {
            line.strip()
            for line in str(value).splitlines()
            if line.strip()
        }

    def _save_disabled_formats(self) -> None:
        self._settings.setValue(
            DISABLED_FORMATS_KEY,
            "\n".join(sorted(self._disabled_formats)),
        )
        self._settings.sync()

    def _on_format_toggled(self, name: str, checked: bool) -> None:
        if checked:
            self._disabled_formats.discard(name)
        else:
            self._disabled_formats.add(name)
        self._save_disabled_formats()
        self._set_status(
            "Настройки сохранены. Изменения применятся при следующем "
            "сканировании."
        )

    def _select_all_formats(self) -> None:
        self._set_format_selection(
            None,
            "Все форматы выбраны. Изменения применятся при следующем "
            "сканировании.",
        )

    def _clear_all_formats(self) -> None:
        self._set_format_selection(
            set(),
            "Все форматы сброшены. Изменения применятся при следующем "
            "сканировании.",
        )

    def _select_only_vector(self) -> None:
        self._set_format_selection(
            {VECTOR},
            "Выбраны только векторные форматы. Изменения применятся при "
            "следующем сканировании.",
        )

    def _select_only_raster(self) -> None:
        self._set_format_selection(
            {RASTER},
            "Выбраны только растровые форматы. Изменения применятся при "
            "следующем сканировании.",
        )

    def _set_format_selection(
        self, categories: Optional[Set[str]], status: str
    ) -> None:
        groups = get_format_groups()
        enabled = {
            group.name
            for group in groups
            if categories is None or group.category in categories
        }
        for name, checkbox in self._format_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(name in enabled)
            checkbox.blockSignals(False)

        self._disabled_formats = {
            group.name for group in groups if group.name not in enabled
        }
        self._save_disabled_formats()
        self._set_status(status)

    def _enabled_format_names(self) -> Set[str]:
        return {
            group.name
            for group in get_format_groups()
            if group.name not in self._disabled_formats
        }

    def _build_brand(self) -> QHBoxLayout:
        brand = QHBoxLayout()
        brand.setSpacing(9)

        logo = QLabel()
        logo.setFixedSize(34, 34)
        logo.setPixmap(QIcon(str(ICON_PATH)).pixmap(34, 34))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)

        title = QLabel("ZGeo")
        self._set_font(title, 5, bold=True)
        titles.addWidget(title)

        subtitle = QLabel("Каталог пространственных данных")
        subtitle.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(subtitle, -1)
        self._set_muted(subtitle)
        titles.addWidget(subtitle)

        brand.addLayout(titles, 1)

        version = get_plugin_version()
        self.version_label = QLabel("Версия {}".format(version))
        self.version_label.setToolTip(
            "Версия плагина ZGeo: {}".format(version)
        )
        self.version_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )
        self._set_font(self.version_label, -1)
        self._set_muted(self.version_label)
        brand.addWidget(
            self.version_label,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        return brand

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(8)
        page_layout.addStretch(1)

        empty_icon = QLabel()
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setPixmap(QIcon(str(ICON_PATH)).pixmap(52, 52))
        page_layout.addWidget(empty_icon)

        self.empty_title_label = QLabel()
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title_label.setWordWrap(True)
        self.empty_title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.empty_title_label, 1, bold=True)
        page_layout.addWidget(self.empty_title_label)

        self.empty_hint_label = QLabel()
        self.empty_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint_label.setWordWrap(True)
        self.empty_hint_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.empty_hint_label, -1)
        self._set_muted(self.empty_hint_label)
        page_layout.addWidget(self.empty_hint_label)
        page_layout.addStretch(1)
        return page

    def _build_scan_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(8)
        page_layout.addStretch(1)

        scan_icon = QLabel()
        scan_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_icon.setPixmap(QIcon(str(ICON_PATH)).pixmap(52, 52))
        page_layout.addWidget(scan_icon)

        scan_title = QLabel("Сканирование папки…")
        scan_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_font(scan_title, 1, bold=True)
        page_layout.addWidget(scan_title)

        scan_hint = QLabel(
            "Просматриваем файлы, включая вложенные папки."
        )
        scan_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_hint.setWordWrap(True)
        self._set_font(scan_hint, -1)
        self._set_muted(scan_hint)
        page_layout.addWidget(scan_hint)

        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedHeight(8)
        page_layout.addWidget(self.scan_progress)

        file_caption = QLabel("Имя файла")
        self._set_font(file_caption, -1, bold=True)
        self._set_muted(file_caption)
        page_layout.addWidget(file_caption)

        self.scan_file_label = QLabel("—")
        self.scan_file_label.setWordWrap(True)
        self.scan_file_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.scan_file_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._set_font(self.scan_file_label, 0, bold=True)
        page_layout.addWidget(self.scan_file_label)

        found_caption = QLabel("Найдено")
        self._set_font(found_caption, -1, bold=True)
        self._set_muted(found_caption)
        page_layout.addWidget(found_caption)

        self.scan_found_label = QLabel("0")
        self._set_font(self.scan_found_label, 3, bold=True)
        page_layout.addWidget(self.scan_found_label)

        self.scan_cancel_button = QPushButton("Прервать")
        self.scan_cancel_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogCancelButton
            )
        )
        self.scan_cancel_button.setMinimumHeight(32)
        self.scan_cancel_button.setMinimumWidth(150)
        self.scan_cancel_button.setEnabled(False)
        self.scan_cancel_button.clicked.connect(self._cancel_scan)
        page_layout.addWidget(
            self.scan_cancel_button,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        page_layout.addStretch(1)
        return page

    def _build_stats_empty_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(8)
        page_layout.addStretch(1)

        empty_icon = QLabel()
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setPixmap(QIcon(str(ICON_PATH)).pixmap(52, 52))
        page_layout.addWidget(empty_icon)

        self.stats_empty_title_label = QLabel()
        self.stats_empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_empty_title_label.setWordWrap(True)
        self.stats_empty_title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.stats_empty_title_label, 1, bold=True)
        page_layout.addWidget(self.stats_empty_title_label)

        self.stats_empty_hint_label = QLabel()
        self.stats_empty_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_empty_hint_label.setWordWrap(True)
        self.stats_empty_hint_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.stats_empty_hint_label, -1)
        self._set_muted(self.stats_empty_hint_label)
        page_layout.addWidget(self.stats_empty_hint_label)
        page_layout.addStretch(1)
        return page

    def _build_stats_content(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.stats_summary_label = QLabel("Файлов: 0 · 0 Б")
        self._set_font(self.stats_summary_label, 1, bold=True)
        layout.addWidget(self.stats_summary_label)

        note = QLabel("Диаграммы построены по всем найденным файлам.")
        note.setWordWrap(True)
        note.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(note, -1)
        self._set_muted(note)
        layout.addWidget(note)

        size_group = QGroupBox("По размеру")
        size_layout = QVBoxLayout(size_group)
        size_layout.setContentsMargins(10, 8, 10, 10)
        size_layout.setSpacing(4)

        size_note = QLabel(
            "Количество файлов в диапазонах размера; справа — суммарный объём."
        )
        size_note.setWordWrap(True)
        size_note.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(size_note, -1)
        self._set_muted(size_note)
        size_layout.addWidget(size_note)

        self.size_chart = BarChart()
        size_layout.addWidget(self.size_chart)
        layout.addWidget(size_group)

        type_group = QGroupBox("По типу")
        type_layout = QVBoxLayout(type_group)
        type_layout.setContentsMargins(10, 8, 10, 10)
        type_layout.setSpacing(4)

        type_note = QLabel(
            "Количество файлов по формату; справа — суммарный объём. "
            "Показаны основные форматы, остальные объединены "
            "в «Другие форматы»."
        )
        type_note.setWordWrap(True)
        type_note.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(type_note, -1)
        self._set_muted(type_note)
        type_layout.addWidget(type_note)

        self.type_chart = BarChart()
        type_layout.addWidget(self.type_chart)
        layout.addWidget(type_group)

        format_group = QGroupBox("Статистика по форматам")
        format_layout = QVBoxLayout(format_group)
        format_layout.setContentsMargins(10, 8, 10, 10)
        format_layout.setSpacing(4)

        format_note = QLabel(
            "Полная статистика по каждому формату. "
            "Объём учитывает сопутствующие файлы наборов данных."
        )
        format_note.setWordWrap(True)
        format_note.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(format_note, -1)
        self._set_muted(format_note)
        format_layout.addWidget(format_note)

        self.format_table = QTableWidget(0, 3)
        self.format_table.setHorizontalHeaderLabels(
            ["Формат", "Кол-во", "Полный объем"]
        )
        self.format_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.format_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.format_table.setAlternatingRowColors(True)
        self.format_table.setWordWrap(False)
        self.format_table.verticalHeader().setVisible(False)
        self.format_table.setAccessibleName("Статистика по форматам")
        self.format_table.setMinimumHeight(110)

        format_header = self.format_table.horizontalHeader()
        format_header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        format_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        format_header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )

        format_layout.addWidget(self.format_table)

        export_row = QHBoxLayout()
        export_row.addStretch(1)
        self.export_formats_button = QPushButton("Экспорт в Excel")
        self.export_formats_button.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogSaveButton
            )
        )
        self.export_formats_button.setMinimumHeight(30)
        self.export_formats_button.clicked.connect(
            self._export_format_table
        )
        self.export_formats_button.setEnabled(False)
        export_row.addWidget(self.export_formats_button)
        format_layout.addLayout(export_row)
        layout.addWidget(format_group)

        self._fit_format_table_height()

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _fit_format_table_height(self) -> None:
        rows = self.format_table.rowCount()
        header_height = self.format_table.horizontalHeader().sizeHint().height()
        row_height = self.format_table.verticalHeader().defaultSectionSize()
        height = header_height + max(1, rows) * row_height + 6
        self.format_table.setFixedHeight(min(300, max(110, height)))

    def _build_tree(self) -> QTreeWidget:
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(
            [
                "Файл",
                "Формат",
                "Система координат",
                "Элементов",
                "Размер",
            ]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tree.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.tree.setAccessibleName("Найденные пространственные файлы")

        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(64)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(1, 135)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(2, 175)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        return self.tree

    # ------------------------------------------------------------------
    # Выбор папки и сканирование
    # ------------------------------------------------------------------

    def choose_folder(self) -> None:
        last_folder = self._settings.value(LAST_FOLDER_KEY, "", type=str)
        if last_folder and Path(last_folder).is_dir():
            start_folder = last_folder
        elif self._folder is not None:
            start_folder = str(self._folder)
        else:
            start_folder = str(Path.home())

        self._set_status("Выбор папки…")
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выбрать папку с геоданными",
            start_folder,
            QFileDialog.Option.ShowDirsOnly,
        )
        if selected:
            self.set_folder(Path(selected))
        else:
            self._set_status("Выбор папки отменён")

    def set_folder(self, folder: Path) -> None:
        folder = Path(folder)
        if not folder.is_dir():
            QMessageBox.warning(
                self,
                "ZGeo",
                "Выбранная папка недоступна:\n{}".format(folder),
            )
            return

        self._folder = folder
        self.folder_name_label.setText(folder.name or str(folder))
        self.folder_path_label.setText(str(folder))
        self.folder_name_label.setToolTip(str(folder))
        self.folder_path_label.setToolTip(str(folder))

        self._settings.setValue(LAST_FOLDER_KEY, str(folder))
        self._settings.sync()

        self.filter_edit.blockSignals(True)
        self.filter_edit.clear()
        self.filter_edit.blockSignals(False)

        self.refresh()

    def refresh(self) -> None:
        if self._folder is None or self._busy:
            return

        self._cancel_attribute_check()
        self._cancel_details()

        if not self._folder.is_dir():
            self._files = []
            self._entries = []
            self._file_by_path = {}
            self.tree.clear()
            self.summary_label.setText(
                self._format_summary("Файлов: 0", 0)
            )
            self._set_empty(
                "Папка недоступна",
                "Каталог был перемещён или удалён. Выберите другую папку.",
            )
            self._clear_statistics(
                "Нет данных",
                "Каталог был перемещён или удалён. Выберите другую папку.",
            )
            self._update_controls()
            self._set_status("Папка недоступна")
            return

        self._set_busy(True)
        task = ScanTask(
            self._folder,
            enabled_formats=self._enabled_format_names(),
        )
        self._scan_task = task
        task.signals.progress.connect(self._on_scan_progress)
        task.signals.finished.connect(self._on_scan_finished)
        QThreadPool.globalInstance().start(task)

    def _on_scan_progress(
        self, current_path: str, found_count: int
    ) -> None:
        path = Path(current_path)
        self.scan_file_label.setText(path.name or current_path)
        self.scan_file_label.setToolTip(current_path)
        self.scan_found_label.setText(str(found_count))
        self._set_status(
            "Сканирование… найдено: {}".format(found_count)
        )

    def _on_scan_finished(
        self, files: object, error: object, cancelled: bool
    ) -> None:
        task = self._scan_task
        self._scan_task = None
        if task is not None:
            try:
                task.signals.progress.disconnect(self._on_scan_progress)
                task.signals.finished.disconnect(self._on_scan_finished)
            except (TypeError, RuntimeError):
                pass

        if error is not None:
            self._files = []
            self._entries = []
            self._file_by_path = {}
            self.tree.clear()
            self.summary_label.setText(
                self._format_summary("Файлов: 0", 0)
            )
            self._set_empty("Не удалось прочитать папку", str(error))
            self._clear_statistics("Нет данных", str(error))
            self._set_busy(False)
            self._set_status(
                "Не удалось прочитать папку: {}".format(error)
            )
            return

        result = list(files) if files is not None else []
        self._files = result
        self._set_busy(False)

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._populate(result)
        finally:
            QApplication.restoreOverrideCursor()

        if cancelled:
            self._show_cancelled_scan(result)
            self._set_status(
                "Сканирование прервано. Найдено: {}".format(len(result))
            )
        else:
            self._set_status(
                "Сканирование завершено. Найдено: {}".format(len(result))
            )

    def _show_cancelled_scan(self, files: List[GeoFile]) -> None:
        if files:
            total_size = sum(geo_file.size for geo_file in files)
            self.summary_label.setText(
                self._format_summary(
                    "Прервано · найдено: {}".format(len(files)),
                    total_size,
                )
            )
            return

        self.summary_label.setText(
            self._format_summary("Прервано · найдено: 0", 0)
        )
        self._set_empty(
            "Сканирование прервано",
            "Поиск остановлен пользователем. Поддерживаемые файлы "
            "не найдены.",
        )
        self._clear_statistics(
            "Сканирование прервано",
            "Поиск остановлен пользователем.",
        )

    def _cancel_scan(self) -> None:
        task = self._scan_task
        if task is None:
            return

        task.cancel()
        self.scan_cancel_button.setEnabled(False)
        self.scan_cancel_button.setText("Прерывание…")
        self._set_status("Прерывание сканирования…")

    def shutdown(self) -> None:
        """Остановить фоновые задачи перед удалением панели."""

        self._cancel_attribute_check()
        self._cancel_details()

        task = self._scan_task
        self._scan_task = None
        if task is not None:
            try:
                task.signals.progress.disconnect(self._on_scan_progress)
                task.signals.finished.disconnect(self._on_scan_finished)
            except (TypeError, RuntimeError):
                pass
            task.cancel()

    def closeEvent(self, event) -> None:
        self._cancel_scan()
        super().closeEvent(event)

    def _populate(self, files: List[GeoFile]) -> None:
        self._cancel_attribute_check()
        self._cancel_details()
        self._files = files
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self._entries = []
        self._item_by_path = {}
        self._element_counts = {}
        self._file_index_by_path = {
            str(geo_file.path): index
            for index, geo_file in enumerate(files)
        }
        self._size_index_cache = {}
        self._file_by_path = {
            str(geo_file.path): geo_file for geo_file in files
        }

        try:
            for geo_file in files:
                item = self._make_item(geo_file)
                self.tree.addTopLevelItem(item)
                self._item_by_path[str(geo_file.path)] = item
                search_text = " ".join(
                    (
                        geo_file.relative_posix,
                        geo_file.path.name,
                        geo_file.format.name,
                        CATEGORY_LABELS.get(geo_file.category, ""),
                    )
                ).casefold()
                self._entries.append((item, search_text))
        finally:
            self.tree.setUpdatesEnabled(True)

        self._update_statistics(files)

        if not files:
            self.summary_label.setText(
                self._format_summary("Файлов: 0", 0)
            )
            self._set_empty(
                "Файлы не найдены",
                "В выбранной папке нет поддерживаемых пространственных файлов.",
            )
            self._update_controls()
            return

        self._apply_filter()
        self._start_details(files)

    def _make_item(self, geo_file: GeoFile) -> QTreeWidgetItem:
        values = [
            geo_file.relative_posix,
            geo_file.format.name,
            "…",
            "…",
            format_size(geo_file.size),
        ]
        if self.tree.columnCount() > 5:
            values.append("—")
        item = QTreeWidgetItem(values)
        item.setIcon(0, self._icon_for(geo_file))
        item.setData(
            0, Qt.ItemDataRole.UserRole, str(geo_file.path)
        )
        item.setToolTip(0, str(geo_file.path))
        item.setToolTip(
            1,
            CATEGORY_LABELS.get(geo_file.category, geo_file.format.name),
        )
        item.setToolTip(2, "Система координат читается…")
        item.setToolTip(3, "Количество элементов читается…")
        item.setToolTip(4, "{} Б".format(geo_file.size))
        item.setTextAlignment(
            3,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        item.setTextAlignment(
            4,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        if self.tree.columnCount() > 5:
            item.setTextAlignment(
                5,
                Qt.AlignmentFlag.AlignCenter
                | Qt.AlignmentFlag.AlignVCenter,
            )
            item.setToolTip(
                5,
                "Атрибуты не проверены. Нажмите «Проверить атрибуты».",
            )
        return item

    def _icon_for(self, geo_file: GeoFile) -> QIcon:
        cache_key = geo_file.extension or "_file"
        if cache_key not in self._icon_cache:
            self._icon_cache[cache_key] = self._icon_provider.icon(
                QFileInfo(str(geo_file.path))
            )
        return self._icon_cache[cache_key]

    # ------------------------------------------------------------------
    # Действия с выбранными файлами
    # ------------------------------------------------------------------

    def _selected_files(self) -> List[GeoFile]:
        selected: List[GeoFile] = []
        for item in self.tree.selectedItems():
            if item.isHidden():
                continue
            path = item.data(0, Qt.ItemDataRole.UserRole)
            geo_file = self._file_by_path.get(str(path))
            if geo_file is not None:
                selected.append(geo_file)
        return selected

    def _visible_files(self) -> List[GeoFile]:
        files: List[GeoFile] = []
        for item, _search_text in self._entries:
            if item.isHidden():
                continue
            path = item.data(0, Qt.ItemDataRole.UserRole)
            geo_file = self._file_by_path.get(str(path))
            if geo_file is not None:
                files.append(geo_file)
        return files

    def _has_visible_files(self) -> bool:
        return any(
            not item.isHidden() for item, _search_text in self._entries
        )

    @staticmethod
    def _format_summary(label: str, total_size: int) -> str:
        return "{} · Общий объем: {}".format(
            label, format_size(total_size)
        )

    def _set_status(self, message: str) -> None:
        self.status_message_label.setText(message)
        self.status_message_label.setToolTip(message)

    def _update_selection_status(self) -> None:
        total = 0 if self._busy else len(self._entries)
        selected = 0 if self._busy else len(self._selected_files())
        self.selection_label.setText(
            "Выбрано: {} из {}".format(selected, total)
        )

    def _update_file_actions(self) -> None:
        selected = self._selected_files()
        enabled = not self._busy
        self.info_button.setEnabled(len(selected) == 1 and enabled)
        self.explorer_button.setEnabled(bool(selected) and enabled)
        self.export_list_button.setEnabled(
            self._has_visible_files() and enabled
        )
        self.check_attributes_button.setEnabled(
            bool(self._files) and enabled and not self._attribute_running
        )
        self._update_selection_status()

    def _show_file_info(self) -> None:
        selected = self._selected_files()
        if len(selected) != 1:
            return

        file_name = selected[0].path.name
        self._set_status("Получение информации: {}".format(file_name))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        error_message = None
        try:
            file_info = inspect_geofile(selected[0])
        except Exception as error:
            error_message = str(error)
        finally:
            QApplication.restoreOverrideCursor()

        if error_message is not None:
            self._set_status(
                "Не удалось получить информацию: {}".format(file_name)
            )
            QMessageBox.critical(
                self,
                "ZGeo",
                "Не удалось получить информацию о файле:\n{}".format(
                    error_message
                ),
            )
            return

        self._set_status("Информация: {}".format(file_name))
        FileInfoDialog(file_info, self).exec()

    def _open_in_explorer(self) -> None:
        selected = self._selected_files()
        if not selected:
            return

        self._set_status(
            "Открываю проводник: {}".format(len(selected))
        )
        errors = reveal_files(
            geo_file.path for geo_file in selected
        )
        if errors:
            self._set_status("Не удалось открыть проводник")
            QMessageBox.warning(
                self,
                "ZGeo",
                "Не удалось открыть проводник:\n\n{}".format(
                    "\n".join(errors)
                ),
            )
            return

        self._set_status(
            "Проводник открыт: {}".format(len(selected))
        )

    def _statistics_sheet_data(self):
        """Подготовить лист со статистикой по форматам для экспорта списка."""

        stats = build_type_distribution(self._files)
        rows = [
            [stat.name, stat.count, format_size(stat.total_size)]
            for stat in stats
        ]
        if rows:
            total_size = sum(geo_file.size for geo_file in self._files)
            rows.append(["", "", ""])
            rows.append(
                ["Итого", len(self._files), format_size(total_size)]
            )
        return (
            "Статистика",
            ["Формат", "Кол-во", "Полный объем"],
            rows,
        )

    def _export_file_list(self) -> None:
        files = self._visible_files()
        if not files:
            return

        include_attributes = self._has_attribute_column()
        headers = [
            "Файл",
            "Формат",
            "Система координат",
            "Элементов",
            "Размер",
        ]
        if include_attributes:
            headers.append("Проблемы с атрибутами")

        rows = []
        for geo_file in files:
            item = self._item_by_path.get(str(geo_file.path))
            row = [
                geo_file.relative_posix,
                geo_file.format.name,
                item.text(2) if item is not None else "…",
                item.text(3) if item is not None else "…",
                format_size(geo_file.size),
            ]
            if include_attributes:
                row.append(item.text(5) if item is not None else "—")
            rows.append(row)

        total_size = sum(geo_file.size for geo_file in files)
        element_counts = [
            self._element_counts.get(str(geo_file.path))
            for geo_file in files
        ]
        if any(count is None for count in element_counts):
            total_elements = "—"
        else:
            total_elements = sum(
                count for count in element_counts if count is not None
            )
        total_row = [
            "Итого файлов: {}".format(len(files)),
            "",
            "",
            total_elements,
            format_size(total_size),
        ]
        if include_attributes:
            total_row.append("")
        rows.append([""] * len(headers))
        rows.append(total_row)

        folder_name = self._folder.name if self._folder else "zgeo"
        self._set_status("Экспорт списка в Excel…")
        exported = export_rows_with_dialog(
            self,
            headers,
            rows,
            "{}_файлы.xlsx".format(folder_name or "zgeo"),
            "Файлы",
            extra_sheets=[self._statistics_sheet_data()],
        )
        if exported is not None:
            self._set_status(
                "Список экспортирован: {}".format(exported.name)
            )
        else:
            self._set_status("Экспорт списка отменён")

    # ------------------------------------------------------------------
    # Система координат, количество элементов и полный объем
    # ------------------------------------------------------------------

    def _start_details(self, files: List[GeoFile]) -> None:
        self._cancel_details()
        if not files:
            return

        self._details_queue = deque(files)
        self._details_total = len(files)
        self._details_processed = 0
        self._size_index_cache = {}
        self._set_status(
            "Чтение характеристик и объемов: 0 из {}".format(
                self._details_total
            )
        )
        self._details_timer.start(0)
        self._update_cancel_button()

    def _cancel_details(self) -> None:
        self._details_timer.stop()
        self._details_queue.clear()
        self._details_total = 0
        self._details_processed = 0
        self._details_paused = False
        self._size_index_cache = {}
        self._update_cancel_button()

    def _abort_details(self) -> None:
        if not self._details_queue and not self._details_timer.isActive():
            return
        processed = self._details_processed
        total = self._details_total
        self._cancel_details()
        self._update_controls()
        self._set_status(
            "Чтение характеристик прервано: {} из {}".format(
                processed, total
            )
        )

    def _pause_details(self) -> None:
        if not self._details_queue:
            return
        self._details_paused = True
        self._details_timer.stop()

    def _resume_details(self) -> None:
        if not self._details_paused:
            return
        self._details_paused = False
        if self._details_queue:
            self._details_timer.start(0)

    def _process_next_detail(self) -> None:
        if self._details_paused:
            return
        if not self._details_queue:
            if self._details_total:
                self._apply_filter()
                self._update_statistics(self._files)
                self._update_controls()
                self._set_status(
                    "Характеристики и объемы прочитаны. Файлов: {}".format(
                        self._details_total
                    )
                )
            return

        geo_file = self._details_queue.popleft()
        self._details_processed += 1

        try:
            summary = inspect_layer_summary(geo_file)
        except Exception:
            summary = LayerSummary("—", None)

        try:
            detail = measure_geo_file_cached(
                geo_file, self._size_index_cache
            )
            refined = replace(geo_file, size=detail.total_size)
        except Exception:
            refined = geo_file

        path_key = str(geo_file.path)
        if summary.element_count is None:
            self._element_counts.pop(path_key, None)
        else:
            self._element_counts[path_key] = summary.element_count

        index = self._file_index_by_path.get(path_key)
        if index is not None and 0 <= index < len(self._files):
            if str(self._files[index].path) == path_key:
                self._files[index] = refined
        self._file_by_path[path_key] = refined

        item = self._item_by_path.get(path_key)
        if item is not None:
            self._update_item_details(item, summary)
            self._update_item_size(item, refined.size)

        if self._details_queue:
            self._set_status(
                "Чтение характеристик и объемов: {} из {} · {}".format(
                    self._details_processed,
                    self._details_total,
                    geo_file.path.name,
                )
            )
            self._details_timer.start(0)
        else:
            self._apply_filter()
            self._update_statistics(self._files)
            self._update_controls()
            self._set_status(
                "Характеристики и объемы прочитаны. Файлов: {}".format(
                    self._details_total
                )
            )

    @staticmethod
    def _update_item_details(
        item: QTreeWidgetItem, summary: LayerSummary
    ) -> None:
        item.setText(2, summary.crs)
        item.setToolTip(2, "Система координат: {}".format(summary.crs))

        if summary.element_count is None:
            count_text = "—"
            count_tooltip = "Количество элементов не определено"
        else:
            count_text = "{:,}".format(summary.element_count).replace(
                ",", " "
            )
            count_tooltip = "Количество элементов: {}".format(
                summary.element_count
            )
        item.setText(3, count_text)
        item.setToolTip(3, count_tooltip)

    @staticmethod
    def _update_item_size(item: QTreeWidgetItem, size: int) -> None:
        item.setText(4, format_size(size))
        item.setToolTip(4, "Полный объем набора: {} Б".format(size))

    # ------------------------------------------------------------------
    # Проверка атрибутивных полей
    # ------------------------------------------------------------------

    def _has_attribute_column(self) -> bool:
        return self.tree.columnCount() > 5

    def _ensure_attribute_column(self) -> None:
        if self._has_attribute_column():
            return

        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(
            [
                "Файл",
                "Формат",
                "Система координат",
                "Элементов",
                "Размер",
                "Проблемы с атрибутами",
            ]
        )
        header = self.tree.header()
        header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        header_item = self.tree.headerItem()
        if header_item is not None:
            header_item.setToolTip(
                5,
                "Да — в именах полей есть нелатинские символы; "
                "Нет — проблем не найдено; — — векторных полей нет.",
            )
        for item, _search_text in self._entries:
            self._set_attribute_cell(
                item, "…", "Проверка атрибутов…"
            )

    @staticmethod
    def _set_attribute_cell(
        item: QTreeWidgetItem, text: str, tooltip: str
    ) -> None:
        item.setText(5, text)
        item.setToolTip(5, tooltip)
        item.setTextAlignment(
            5,
            Qt.AlignmentFlag.AlignCenter
            | Qt.AlignmentFlag.AlignVCenter,
        )

    @staticmethod
    def _can_check_attributes(geo_file: GeoFile) -> bool:
        return geo_file.category in (VECTOR, TABLE, OTHER)

    def _start_attribute_check(self) -> None:
        if self._attribute_running or not self._files:
            return

        self._attribute_checked = False
        self._set_problems_filter_available(False)
        self.problems_label.setText("Проблемных файлов: 0")
        self.problems_label.setToolTip("Идёт проверка атрибутов…")
        self.problems_label.setVisible(True)

        self._ensure_attribute_column()
        for item, _search_text in self._entries:
            self._set_attribute_cell(
                item, "…", "Проверка атрибутов…"
            )

        candidates = [
            geo_file
            for geo_file in self._files
            if self._can_check_attributes(geo_file)
        ]
        candidate_paths = {str(geo_file.path) for geo_file in candidates}
        for geo_file in self._files:
            if str(geo_file.path) in candidate_paths:
                continue
            item = self._item_by_path.get(str(geo_file.path))
            if item is not None:
                self._set_attribute_cell(
                    item,
                    "—",
                    "Векторные атрибутивные поля не найдены.",
                )

        if not candidates:
            self._attribute_checked = True
            self._update_problems_summary()
            self.problems_label.setToolTip("")
            self._set_problems_filter_available(True)
            self._apply_filter()
            self._set_status(
                "Нет векторных файлов для проверки атрибутов"
            )
            self._update_file_actions()
            self._update_cancel_button()
            return

        self._attribute_queue = deque(candidates)
        self._attribute_total = len(candidates)
        self._attribute_processed = 0
        self._attribute_issue_count = 0
        self._attribute_running = True
        self.check_attributes_button.setToolTip(
            "Проверка атрибутов выполняется…"
        )
        self._pause_details()
        self._apply_filter()
        self._update_file_actions()
        self._update_cancel_button()
        self._set_status(
            "Проверка атрибутов: 0 из {}".format(self._attribute_total)
        )
        self._attribute_timer.start(0)

    def _process_next_attribute_check(self) -> None:
        if not self._attribute_queue:
            self._finish_attribute_check()
            return

        geo_file = self._attribute_queue.popleft()
        self._attribute_processed += 1

        try:
            check = inspect_attribute_names(geo_file)
        except Exception:
            check = AttributeCheck((), ())

        item = self._item_by_path.get(str(geo_file.path))
        if item is not None:
            self._update_item_attributes(item, check)

        if check.has_issues:
            self._attribute_issue_count += 1
            self._update_problems_summary()

        if self._attribute_queue:
            self._set_status(
                "Проверка атрибутов: {} из {} · {}".format(
                    self._attribute_processed,
                    self._attribute_total,
                    geo_file.path.name,
                )
            )
            self._attribute_timer.start(0)
        else:
            self._finish_attribute_check()

    @staticmethod
    def _update_item_attributes(
        item: QTreeWidgetItem, check: AttributeCheck
    ) -> None:
        if check.non_latin_names:
            item.setText(5, "Да")
            item.setToolTip(
                5,
                "Нелатинские имена полей:\n{}".format(
                    "\n".join(check.non_latin_names)
                ),
            )
        elif check.field_names:
            item.setText(5, "Нет")
            item.setToolTip(5, "Проблем с именами полей не найдено.")
        else:
            item.setText(5, "—")
            item.setToolTip(
                5, "Векторные атрибутивные поля не найдены."
            )

    def _finish_attribute_check(self) -> None:
        total = self._attribute_total
        issues = self._attribute_issue_count
        self._attribute_running = False
        self._attribute_checked = True
        self._attribute_queue.clear()
        self.check_attributes_button.setToolTip(
            ATTRIBUTE_CHECK_TOOLTIP
        )
        self._update_problems_summary()
        self.problems_label.setToolTip("")
        self._set_problems_filter_available(True)
        self._update_file_actions()
        self._resume_details()
        self._update_cancel_button()
        self._apply_filter()

        if issues:
            self._set_status(
                "Атрибуты проверены: файлов {} · с проблемами {}".format(
                    total, issues
                )
            )
        else:
            self._set_status(
                "Атрибуты проверены: проблем не найдено. Файлов: {}".format(
                    total
                )
            )

    def _abort_attribute_check(self) -> None:
        if not self._attribute_running:
            return

        processed = self._attribute_processed
        total = self._attribute_total
        issues = self._attribute_issue_count
        self._attribute_timer.stop()
        self._attribute_queue.clear()
        self._attribute_running = False
        self._attribute_checked = processed > 0
        self.check_attributes_button.setToolTip(
            ATTRIBUTE_CHECK_TOOLTIP
        )
        self._update_problems_summary()
        if self._attribute_checked:
            self.problems_label.setToolTip(
                "Проверка прервана: обработано {} из {} файлов".format(
                    processed, total
                )
            )
        self._set_problems_filter_available(self._attribute_checked)
        self._resume_details()
        self._update_file_actions()
        self._update_cancel_button()
        self._apply_filter()
        self._set_status(
            "Проверка атрибутов прервана: обработано {} из {} · "
            "проблем {}".format(processed, total, issues)
        )

    def _cancel_attribute_check(self) -> None:
        self._attribute_timer.stop()
        self._attribute_queue.clear()
        self._attribute_running = False
        self._attribute_total = 0
        self._attribute_processed = 0
        self._attribute_issue_count = 0
        self._attribute_checked = False
        self._reset_problems_filter()
        if hasattr(self, "check_attributes_button"):
            self.check_attributes_button.setToolTip(
                ATTRIBUTE_CHECK_TOOLTIP
            )
        self._update_cancel_button()

    def _set_problems_filter_available(self, available: bool) -> None:
        if not hasattr(self, "problems_only_checkbox"):
            return
        self.problems_only_checkbox.setEnabled(available)
        if not available:
            self.problems_only_checkbox.blockSignals(True)
            self.problems_only_checkbox.setChecked(False)
            self.problems_only_checkbox.blockSignals(False)

    def _reset_problems_filter(self) -> None:
        self._attribute_checked = False
        if not hasattr(self, "problems_label"):
            return
        self._set_problems_filter_available(False)
        self.problems_label.setText("Проблемных файлов: 0")
        self.problems_label.setToolTip("")
        self.problems_label.setVisible(False)

    def _update_problems_summary(self) -> None:
        if not hasattr(self, "problems_label"):
            return
        self.problems_label.setText(
            "Проблемных файлов: {}".format(self._attribute_issue_count)
        )
        self.problems_label.setVisible(
            self._attribute_checked or self._attribute_running
        )

    def _update_cancel_button(self) -> None:
        if not hasattr(self, "cancel_task_button"):
            return
        active = not self._busy and (
            self._attribute_running
            or bool(self._details_queue)
            or self._details_timer.isActive()
        )
        self.cancel_task_button.setVisible(active)
        self.cancel_task_button.setEnabled(active)
        if not active:
            return
        if self._attribute_running:
            tooltip = "Прервать проверку атрибутов"
        else:
            tooltip = "Прервать чтение характеристик"
        self.cancel_task_button.setToolTip(tooltip)

    def _cancel_long_operation(self) -> None:
        if self._attribute_running:
            self._abort_attribute_check()
        elif self._details_queue or self._details_timer.isActive():
            self._abort_details()

    # ------------------------------------------------------------------
    # Статистика
    # ------------------------------------------------------------------

    def _update_statistics(self, files: List[GeoFile]) -> None:
        if not files:
            self._clear_statistics(
                "Файлы не найдены",
                "После сканирования диаграммы появятся здесь.",
            )
            return

        total_size = sum(geo_file.size for geo_file in files)
        total_count = len(files)
        self.stats_summary_label.setText(
            "Файлов: {} · {}".format(
                total_count, format_size(total_size)
            )
        )

        size_rows: List[BarDatum] = []
        for bucket in build_size_distribution(files):
            percent = 100.0 * bucket.count / total_count
            size_rows.append(
                BarDatum(
                    label=bucket.label,
                    value=float(bucket.count),
                    value_text="{} · {}".format(
                        bucket.count, format_size(bucket.total_size)
                    ),
                    color=SIZE_CHART_COLOR,
                    tooltip="{}: {} файлов ({:.0f}%), {}".format(
                        bucket.label,
                        bucket.count,
                        percent,
                        format_size(bucket.total_size),
                    ),
                )
            )
        self.size_chart.set_rows(size_rows)

        type_rows: List[BarDatum] = []
        for index, type_stat in enumerate(
            build_type_distribution(files, limit=8)
        ):
            percent = 100.0 * type_stat.count / total_count
            tooltip = "{}: {} файлов ({:.0f}%), {}".format(
                type_stat.name,
                type_stat.count,
                percent,
                format_size(type_stat.total_size),
            )
            if len(type_stat.formats) > 1:
                tooltip += "\n" + ", ".join(type_stat.formats)
            type_rows.append(
                BarDatum(
                    label=type_stat.name,
                    value=float(type_stat.count),
                    value_text="{} · {}".format(
                        type_stat.count,
                        format_size(type_stat.total_size),
                    ),
                    color=TYPE_CHART_COLORS[index % len(TYPE_CHART_COLORS)],
                    tooltip=tooltip,
                )
            )
        self.type_chart.set_rows(type_rows)

        all_type_stats = build_type_distribution(files)
        self.format_table.setRowCount(len(all_type_stats))
        for row, type_stat in enumerate(all_type_stats):
            format_item = QTableWidgetItem(type_stat.name)
            format_item.setToolTip(
                "{} · {}".format(
                    type_stat.name,
                    CATEGORY_LABELS.get(type_stat.category, ""),
                ).rstrip(" ·")
            )

            count_item = QTableWidgetItem(
                "{:,}".format(type_stat.count).replace(",", " ")
            )
            count_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            count_item.setToolTip("Файлов: {}".format(type_stat.count))
            count_item.setData(
                Qt.ItemDataRole.UserRole, type_stat.count
            )

            size_item = QTableWidgetItem(format_size(type_stat.total_size))
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            size_item.setToolTip("{} Б".format(type_stat.total_size))

            self.format_table.setItem(row, 0, format_item)
            self.format_table.setItem(row, 1, count_item)
            self.format_table.setItem(row, 2, size_item)
        self._fit_format_table_height()
        self.export_formats_button.setEnabled(bool(all_type_stats))

        self.stats_stack.setCurrentWidget(self.stats_content_widget)

    def _export_format_table(self) -> None:
        folder_name = self._folder.name if self._folder else "zgeo"
        total_count = len(self._files)
        total_size = sum(
            geo_file.size for geo_file in self._files
        )
        summary_rows = [
            ["", "", ""],
            ["Итого", total_count, format_size(total_size)],
        ]
        self._set_status("Экспорт статистики в Excel…")
        exported = export_table_with_dialog(
            self,
            self.format_table,
            "{}_форматы.xlsx".format(folder_name or "zgeo"),
            "Форматы",
            summary_rows=summary_rows,
        )
        if exported is not None:
            self._set_status(
                "Статистика экспортирована: {}".format(exported.name)
            )
        else:
            self._set_status("Экспорт статистики отменён")

    def _clear_statistics(self, title: str, hint: str) -> None:
        self.stats_summary_label.setText("Файлов: 0 · 0 Б")
        self.size_chart.set_rows([])
        self.type_chart.set_rows([])
        self.format_table.setRowCount(0)
        self._fit_format_table_height()
        self.export_formats_button.setEnabled(False)
        self._set_stats_empty(title, hint)

    def _set_stats_empty(self, title: str, hint: str) -> None:
        self.stats_empty_title_label.setText(title)
        self.stats_empty_hint_label.setText(hint)
        self.stats_stack.setCurrentWidget(self.stats_stack.widget(0))

    # ------------------------------------------------------------------
    # Фильтрация и состояния интерфейса
    # ------------------------------------------------------------------

    def _on_filter_changed(self, _text: str) -> None:
        self._apply_filter()
        self._update_filter_status()

    def _on_problems_filter_toggled(self, _checked: bool) -> None:
        self._apply_filter()
        self._update_filter_status()

    def _update_filter_status(self) -> None:
        if not self._entries:
            return
        visible = sum(
            1 for item, _search_text in self._entries if not item.isHidden()
        )
        query = self.filter_edit.text().strip()
        if query:
            self._set_status(
                "Фильтр: показано {} из {}".format(
                    visible, len(self._entries)
                )
            )
        elif self.problems_only_checkbox.isChecked():
            self._set_status(
                "Фильтр «Только проблемные»: показано {} из {}".format(
                    visible, len(self._entries)
                )
            )
        else:
            self._set_status("Фильтр очищен")

    def _apply_filter(self) -> None:
        if self._folder is None:
            return

        query = self.filter_edit.text().strip().casefold()
        problems_only = self.problems_only_checkbox.isChecked()
        visible = 0
        visible_size = 0

        for item, search_text in self._entries:
            hidden = bool(query) and query not in search_text
            if not hidden and problems_only:
                hidden = item.text(5) != "Да"
            item.setHidden(hidden)
            if not hidden:
                visible += 1
                path = item.data(0, Qt.ItemDataRole.UserRole)
                geo_file = self._file_by_path.get(str(path))
                if geo_file is not None:
                    visible_size += geo_file.size

        if not self._entries:
            self.summary_label.setText(
                self._format_summary("Файлов: 0", 0)
            )
            self.stack.setCurrentWidget(self.stack.widget(0))
            return

        if visible:
            self.stack.setCurrentWidget(self.tree)
        else:
            self._set_empty(
                "Ничего не найдено",
                "Измените запрос, снимите фильтр «Только проблемные» "
                "или очистите строку фильтра.",
            )

        if query or problems_only:
            self.summary_label.setText(
                self._format_summary(
                    "Показано: {} из {}".format(
                        visible, len(self._entries)
                    ),
                    visible_size,
                )
            )
        else:
            self.summary_label.setText(
                self._format_summary(
                    "Файлов: {}".format(len(self._entries)),
                    visible_size,
                )
            )

        self._update_file_actions()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.summary_label.setText("Сканирование…")
            self._set_status("Сканирование папки…")
            self.scan_file_label.setText("—")
            self.scan_file_label.setToolTip("")
            self.scan_found_label.setText("0")
            self.scan_progress.setRange(0, 0)
            self.scan_cancel_button.setText("Прервать")
            self.scan_cancel_button.setEnabled(True)
            self.stack.setCurrentWidget(self.scan_page)
            self._set_stats_empty(
                "Сканирование…",
                "Диаграммы обновятся после завершения поиска файлов.",
            )
        else:
            self.scan_cancel_button.setEnabled(False)
            self.scan_cancel_button.setText("Прервать")
        self._update_controls()
        if busy:
            QApplication.processEvents()

    def _update_controls(self) -> None:
        enabled = not self._busy
        self.choose_button.setEnabled(enabled)
        self.refresh_button.setEnabled(
            self._folder is not None and enabled
        )
        self.filter_edit.setEnabled(bool(self._files) and enabled)
        if hasattr(self, "problems_only_checkbox"):
            self.problems_only_checkbox.setEnabled(
                self._attribute_checked and enabled
            )
        self._update_file_actions()
        self._update_cancel_button()

    def _set_empty(self, title: str, hint: str) -> None:
        self.empty_title_label.setText(title)
        self.empty_hint_label.setText(hint)
        self.stack.setCurrentWidget(self.stack.widget(0))

    def _set_muted(self, widget: QWidget) -> None:
        palette = widget.palette()
        palette.setColor(
            QPalette.ColorRole.WindowText,
            palette.color(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.WindowText,
            ),
        )
        widget.setPalette(palette)

    @staticmethod
    def _set_font(widget: QWidget, size_delta: int, bold: bool = False) -> None:
        font = QFont(widget.font())
        point_size = widget.font().pointSizeF()
        if point_size <= 0:
            point_size = 10.0
        font.setPointSizeF(max(7.0, point_size + size_delta))
        font.setBold(bold)
        widget.setFont(font)

