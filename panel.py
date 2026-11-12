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
    pyqtSignal,
)
from qgis.PyQt.QtGui import QFont, QIcon, QPalette
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
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
from .check_dialog import (
    CHECK_CRS_QUALITY,
    CHECK_COUNT_QUALITY,
    CHECK_DATASET_INTEGRITY,
    CHECK_FIELD_NAMES,
    CHECK_GEOMETRY_COORDINATES,
    CHECK_JSON_GEOJSON,
    CHECK_SIZE,
    CHECK_SIZE_MIF_MID,
    CHECK_SIZE_SHP,
    LAYER_PROBLEM_CHECKS,
    PROBLEM_CHECKS,
    ChecksDialog,
)
from .attribute_check import has_non_latin_characters
from .dataset_size import DirectoryIndex, measure_geo_file_cached
from .explorer import reveal_files
from .geojson_check import JSON_EXTENSIONS, check_json_file
from .file_info import (
    LayerSummary,
    inspect_geofile,
    inspect_layer_summary,
)
from .formatting import format_size
from .geometry_check import inspect_geometry_and_coordinates
from .quality_check import (
    QualityIssue,
    completeness_issues,
    crs_issues,
    dbf_encoding_issues,
    directory_files,
    empty_layer_issues,
    field_name_issues,
    truncated_duplicate_issues,
)
from .i18n import (
    LANGUAGE_EN,
    LANGUAGE_KEY,
    LANGUAGE_RU,
    category_label,
    get_language,
    set_language,
    tr,
)
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

LAST_FOLDER_KEY = "zgeo/last_folder"
DISABLED_FORMATS_KEY = "zgeo/disabled_formats"
ICON_PATH = Path(__file__).with_name("icon.svg")
CHECKS_TOOLTIP = (
    "Проверки: уточнить размер (в том числе отдельно для SHP и MIF/MID), "
    "систему координат и количество элементов, проверить JSON, имена "
    "полей, набор данных, геометрии и координаты."
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

    language_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._settings = QSettings()
        set_language(self._settings.value(LANGUAGE_KEY, LANGUAGE_RU))
        self._folder: Optional[Path] = None
        self._files: List[GeoFile] = []
        self._file_by_path: Dict[str, GeoFile] = {}
        self._entries: List[Tuple[QTreeWidgetItem, str]] = []
        self._item_by_path: Dict[str, QTreeWidgetItem] = {}
        self._element_counts: Dict[str, int] = {}
        self._refined_crs_paths: Set[str] = set()
        self._refined_count_paths: Set[str] = set()
        self._refined_size_paths: Set[str] = set()
        self._json_running = False
        self._json_queue: Deque[GeoFile] = deque()
        self._json_total = 0
        self._json_processed = 0
        self._json_removed: List[str] = []
        self._json_after_checks: List[str] = []
        self._file_index_by_path: Dict[str, int] = {}
        self._size_index_cache: Dict[str, DirectoryIndex] = {}
        self._scan_task: Optional[ScanTask] = None
        self._busy = False
        self._format_checkboxes: Dict[str, QCheckBox] = {}
        self._category_group_boxes: Dict[str, QGroupBox] = {}
        self._disabled_formats = self._load_disabled_formats()
        self._icon_provider = QFileIconProvider()
        self._icon_cache: Dict[str, QIcon] = {}

        self._details_queue: Deque[GeoFile] = deque()
        self._details_total = 0
        self._details_processed = 0
        self._details_paused = False
        self._details_read_size = False
        self._details_read_crs = False
        self._details_read_count = False
        self._details_size_paths: Set[str] = set()
        self._details_action_source = "Уточнение данных"
        self._details_size_changed = False
        self._details_timer = QTimer(self)
        self._details_timer.setSingleShot(True)
        self._details_timer.setInterval(0)
        self._details_timer.timeout.connect(self._process_next_detail)

        self._problem_running = False
        self._problem_checked = False
        self._problem_queue: Deque[GeoFile] = deque()
        self._problem_total = 0
        self._problem_processed = 0
        self._problem_issue_count = 0
        self._problem_issues: Dict[str, Tuple[QualityIssue, ...]] = {}
        self._problem_checked_paths: Set[str] = set()
        self._problem_candidate_paths: Set[str] = set()
        self._problem_interrupted = False
        self._problem_selected: Tuple[str, ...] = ()
        self._problem_file_cache: Dict[str, Dict[str, Path]] = {}
        self._empty_title_source = "Геоданные не выбраны"
        self._empty_hint_source = (
            "Нажмите «Выбрать папку», чтобы найти шейпфайлы, GeoPackage "
            "и другие пространственные данные."
        )
        self._stats_empty_title_source = "Статистика пуста"
        self._stats_empty_hint_source = (
            "Выберите папку и выполните сканирование. Здесь появятся "
            "диаграммы по размеру и типу файлов."
        )
        self._problem_timer = QTimer(self)
        self._problem_timer.setSingleShot(True)
        self._problem_timer.setInterval(0)
        self._problem_timer.timeout.connect(
            self._process_next_problem_check
        )

        self._json_timer = QTimer(self)
        self._json_timer.setSingleShot(True)
        self._json_timer.setInterval(0)
        self._json_timer.timeout.connect(self._process_next_json_check)

        self.setObjectName("ZGeoPanel")
        self.setWindowTitle(tr("ZGeo — геоданные"))
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
            self._empty_title_source,
            self._empty_hint_source,
        )
        self._set_stats_empty(
            self._stats_empty_title_source,
            self._stats_empty_hint_source,
        )

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("zgeoRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 0)
        layout.setSpacing(9)

        layout.addLayout(self._build_brand())
        layout.addSpacing(3)

        self.folder_caption_label = QLabel(tr("ПАПКА"))
        self._set_font(self.folder_caption_label, -1, bold=True)
        self._set_muted(self.folder_caption_label)
        layout.addWidget(self.folder_caption_label)

        self.folder_name_label = QLabel(tr("Папка не выбрана"))
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

        self.folder_path_label = QLabel(tr("Выберите каталог на диске"))
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

        self.choose_button = QPushButton(tr("Выбрать папку"))
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
        self.refresh_button.setToolTip(tr("Пересканировать папку"))
        self.refresh_button.setAccessibleName(tr("Пересканировать папку"))
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_button)

        layout.addLayout(buttons)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_files_page(), tr("Файлы"))
        self.tabs.addTab(self._build_stats_page(), tr("Статистика"))
        self.tabs.addTab(self._build_settings_page(), tr("Настройки"))
        self.tabs.setTabToolTip(
            0, tr("Найденные пространственные файлы")
        )
        self.tabs.setTabToolTip(
            1, tr("Диаграммы по размеру и типу файлов")
        )
        self.tabs.setTabToolTip(
            2, tr("Форматы файлов, которые нужно искать")
        )
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self._build_status_bar())

        outer = QWidget(self)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(root, 1)
        self.progress_bar = self._build_progress_bar()
        outer_layout.addWidget(self.progress_bar)
        self.setWidget(outer)

    def _build_status_bar(self) -> QStatusBar:
        bar = QStatusBar()
        self.status_bar = bar
        bar.setObjectName("zgeoStatusBar")
        bar.setSizeGripEnabled(False)
        bar.setContentsMargins(0, 0, 0, 0)

        self.status_message_label = QLabel(tr("Готово"))
        self.status_message_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.status_message_label, -1)
        bar.addWidget(self.status_message_label, 1)

        self.selection_label = QLabel(tr("Выбрано: 0 из 0"))
        self.selection_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.selection_label.setMinimumWidth(150)
        self._set_font(self.selection_label, -1)
        bar.addPermanentWidget(self.selection_label)
        return bar

    def _build_progress_bar(self) -> QProgressBar:
        """Создать полосу прогресса во всю ширину внизу окна."""

        bar = QProgressBar()
        bar.setObjectName("zgeoBottomProgress")
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        bar.setFormat("%v / %m")
        bar.setFixedHeight(18)
        bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        bar.setAccessibleName(tr("Ход выполнения"))
        bar.setVisible(False)
        return bar

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self.summary_label = QLabel(tr("Файлов: 0 · Общий объем: 0 Б"))
        self._set_font(self.summary_label, 0, bold=True)
        layout.addWidget(self.summary_label)

        self.problems_label = QLabel(tr("Проблемных файлов: 0"))
        self._set_font(self.problems_label, -1)
        self.problems_label.setVisible(False)
        layout.addWidget(self.problems_label)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(
            tr("Фильтр по имени, формату или пути")
        )
        self.filter_edit.setAccessibleName(
            tr("Фильтр по имени, формату или пути")
        )
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_edit, 1)

        self.problems_only_checkbox = QCheckBox(tr("Только проблемные"))
        self.problems_only_checkbox.setToolTip(
            tr(
                "Показывать только файлы, у которых проверки нашли "
                "проблемы"
            )
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
        self.info_button.setToolTip(tr("Информация"))
        self.info_button.setAccessibleName(tr("Информация"))
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
        self.explorer_button.setToolTip(tr("Открыть в проводнике"))
        self.explorer_button.setAccessibleName(
            tr("Открыть в проводнике")
        )
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
        self.export_list_button.setToolTip(tr("Экспорт в Excel"))
        self.export_list_button.setAccessibleName(
            tr("Экспорт в Excel")
        )
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
            tr(CHECKS_TOOLTIP)
        )
        self.check_attributes_button.setAccessibleName(
            tr("Проверки")
        )
        self.check_attributes_button.clicked.connect(
            self._show_checks_dialog
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
        self.cancel_task_button.setToolTip(
            tr("Прервать длительную операцию")
        )
        self.cancel_task_button.setAccessibleName(
            tr("Прервать операцию")
        )
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
        self.select_all_button = QPushButton(tr("Выбрать все"))
        self.select_all_button.setToolTip(tr("Отметить все форматы"))
        self.select_all_button.clicked.connect(self._select_all_formats)
        self.clear_all_button = QPushButton(tr("Сбросить все"))
        self.clear_all_button.setToolTip(tr("Снять все отметки"))
        self.clear_all_button.clicked.connect(self._clear_all_formats)
        self.only_vector_button = QPushButton(tr("Только вектор"))
        self.only_vector_button.setToolTip(
            tr("Оставить только векторные форматы")
        )
        self.only_vector_button.clicked.connect(self._select_only_vector)
        self.only_raster_button = QPushButton(tr("Только растр"))
        self.only_raster_button.setToolTip(
            tr("Оставить только растровые форматы")
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

        self.settings_hint_label = QLabel(
            tr(
                "Отметьте форматы, которые должны попадать в каталог. "
                "Изменения применяются при следующем сканировании."
            )
        )
        self.settings_hint_label.setWordWrap(True)
        self._set_font(self.settings_hint_label, -1)
        self._set_muted(self.settings_hint_label)
        layout.addWidget(self.settings_hint_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        groups = get_format_groups()
        for category in (VECTOR, RASTER, TABLE, OTHER):
            category_groups = [
                group for group in groups
                if group.category == category
            ]
            if not category_groups:
                continue

            group_box = QGroupBox(category_label(category))
            self._category_group_boxes[category] = group_box
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
                    tr(
                        "Расширения: {}",
                        ", ".join(group.extensions),
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
            tr(
                "Настройки сохранены. Изменения применятся при следующем "
                "сканировании."
            )
        )

    def _select_all_formats(self) -> None:
        self._set_format_selection(
            None,
            tr(
                "Все форматы выбраны. Изменения применятся при следующем "
                "сканировании."
            ),
        )

    def _clear_all_formats(self) -> None:
        self._set_format_selection(
            set(),
            tr(
                "Все форматы сброшены. Изменения применятся при следующем "
                "сканировании."
            ),
        )

    def _select_only_vector(self) -> None:
        self._set_format_selection(
            {VECTOR},
            tr(
                "Выбраны только векторные форматы. Изменения применятся при "
                "следующем сканировании."
            ),
        )

    def _select_only_raster(self) -> None:
        self._set_format_selection(
            {RASTER},
            tr(
                "Выбраны только растровые форматы. Изменения применятся при "
                "следующем сканировании."
            ),
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

    @staticmethod
    def _tree_headers(include_attributes: bool = False) -> List[str]:
        headers = [
            tr("Файл"),
            tr("Формат"),
            tr("Система координат"),
            tr("Элементов"),
            tr("Размер"),
        ]
        if include_attributes:
            headers.append(tr("Проблемы"))
        return headers

    @staticmethod
    def _format_table_headers() -> List[str]:
        return [tr("Формат"), tr("Кол-во"), tr("Полный объем")]

    @staticmethod
    def _language_tooltip() -> str:
        if get_language() == LANGUAGE_RU:
            return tr("Переключить на английский")
        return tr("Переключить на русский")

    def _update_language_button(self) -> None:
        if not hasattr(self, "language_button"):
            return
        self.language_button.setText(
            "EN" if get_language() == LANGUAGE_RU else "RU"
        )
        self.language_button.setToolTip(self._language_tooltip())
        self.language_button.setAccessibleName(tr("Переключить язык"))

    def _toggle_language(self) -> None:
        new_language = (
            LANGUAGE_EN
            if get_language() == LANGUAGE_RU
            else LANGUAGE_RU
        )
        set_language(new_language)
        self._settings.setValue(LANGUAGE_KEY, new_language)
        self._settings.sync()
        self._retranslate_ui()
        self.language_changed.emit(new_language)

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

        self.brand_subtitle_label = QLabel(
            tr("Каталог пространственных данных")
        )
        self.brand_subtitle_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.brand_subtitle_label, -1)
        self._set_muted(self.brand_subtitle_label)
        titles.addWidget(self.brand_subtitle_label)

        brand.addLayout(titles, 1)

        version = get_plugin_version()
        self.version_label = QLabel(tr("Версия {}", version))
        self.version_label.setToolTip(
            tr("Версия плагина ZGeo: {}", version)
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

        self.language_button = QPushButton()
        self.language_button.setObjectName("zgeoLanguageButton")
        self.language_button.setFixedSize(44, 28)
        self.language_button.setToolTip(self._language_tooltip())
        self.language_button.setAccessibleName(tr("Переключить язык"))
        self.language_button.clicked.connect(self._toggle_language)
        self._update_language_button()
        brand.addWidget(
            self.language_button,
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

        self.scan_title_label = QLabel(tr("Сканирование папки…"))
        self.scan_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_font(self.scan_title_label, 1, bold=True)
        page_layout.addWidget(self.scan_title_label)

        self.scan_hint_label = QLabel(
            tr("Просматриваем файлы, включая вложенные папки.")
        )
        self.scan_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_hint_label.setWordWrap(True)
        self._set_font(self.scan_hint_label, -1)
        self._set_muted(self.scan_hint_label)
        page_layout.addWidget(self.scan_hint_label)

        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedHeight(8)
        page_layout.addWidget(self.scan_progress)

        self.scan_file_caption = QLabel(tr("Имя файла"))
        self._set_font(self.scan_file_caption, -1, bold=True)
        self._set_muted(self.scan_file_caption)
        page_layout.addWidget(self.scan_file_caption)

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

        self.scan_found_caption = QLabel(tr("Найдено"))
        self._set_font(self.scan_found_caption, -1, bold=True)
        self._set_muted(self.scan_found_caption)
        page_layout.addWidget(self.scan_found_caption)

        self.scan_found_label = QLabel("0")
        self._set_font(self.scan_found_label, 3, bold=True)
        page_layout.addWidget(self.scan_found_label)

        self.scan_cancel_button = QPushButton(tr("Прервать"))
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

        self.stats_summary_label = QLabel(tr("Файлов: 0 · 0 Б"))
        self._set_font(self.stats_summary_label, 1, bold=True)
        layout.addWidget(self.stats_summary_label)

        self.stats_note_label = QLabel(
            tr("Диаграммы построены по всем найденным файлам.")
        )
        self.stats_note_label.setWordWrap(True)
        self.stats_note_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.stats_note_label, -1)
        self._set_muted(self.stats_note_label)
        layout.addWidget(self.stats_note_label)

        self.size_group = QGroupBox(tr("По размеру"))
        size_layout = QVBoxLayout(self.size_group)
        size_layout.setContentsMargins(10, 8, 10, 10)
        size_layout.setSpacing(4)

        self.size_note_label = QLabel(
            tr(
                "Количество файлов в диапазонах размера; справа — "
                "суммарный объём."
            )
        )
        self.size_note_label.setWordWrap(True)
        self.size_note_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.size_note_label, -1)
        self._set_muted(self.size_note_label)
        size_layout.addWidget(self.size_note_label)

        self.size_chart = BarChart()
        self.size_chart.setAccessibleName(tr("Диаграмма по размеру"))
        size_layout.addWidget(self.size_chart)
        layout.addWidget(self.size_group)

        self.type_group = QGroupBox(tr("По типу"))
        type_layout = QVBoxLayout(self.type_group)
        type_layout.setContentsMargins(10, 8, 10, 10)
        type_layout.setSpacing(4)

        self.type_note_label = QLabel(
            tr(
                "Количество файлов по формату; справа — суммарный объём. "
                "Показаны основные форматы, остальные объединены "
                "в «Другие форматы»."
            )
        )
        self.type_note_label.setWordWrap(True)
        self.type_note_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.type_note_label, -1)
        self._set_muted(self.type_note_label)
        type_layout.addWidget(self.type_note_label)

        self.type_chart = BarChart()
        self.type_chart.setAccessibleName(tr("Диаграмма по типу"))
        type_layout.addWidget(self.type_chart)
        layout.addWidget(self.type_group)

        self.format_group = QGroupBox(tr("Статистика по форматам"))
        format_layout = QVBoxLayout(self.format_group)
        format_layout.setContentsMargins(10, 8, 10, 10)
        format_layout.setSpacing(4)

        self.format_note_label = QLabel(
            tr(
                "Полная статистика по каждому формату. "
                "Объём учитывает сопутствующие файлы наборов данных."
            )
        )
        self.format_note_label.setWordWrap(True)
        self.format_note_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._set_font(self.format_note_label, -1)
        self._set_muted(self.format_note_label)
        format_layout.addWidget(self.format_note_label)

        self.format_table = QTableWidget(0, 3)
        self.format_table.setHorizontalHeaderLabels(self._format_table_headers())
        self.format_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.format_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.format_table.setAlternatingRowColors(True)
        self.format_table.setWordWrap(False)
        self.format_table.verticalHeader().setVisible(False)
        self.format_table.setAccessibleName(
            tr("Статистика по форматам")
        )
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
        self.export_formats_button = QPushButton(tr("Экспорт в Excel"))
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
        layout.addWidget(self.format_group)

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
        self.tree.setHeaderLabels(self._tree_headers())
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
        self.tree.setAccessibleName(
            tr("Найденные пространственные файлы")
        )

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

        self._set_status(tr("Выбор папки…"))
        selected = QFileDialog.getExistingDirectory(
            self,
            tr("Выбрать папку с геоданными"),
            start_folder,
            QFileDialog.Option.ShowDirsOnly,
        )
        if selected:
            self.set_folder(Path(selected))
        else:
            self._set_status(tr("Выбор папки отменён"))

    def set_folder(self, folder: Path) -> None:
        folder = Path(folder)
        if not folder.is_dir():
            QMessageBox.warning(
                self,
                "ZGeo",
                tr("Выбранная папка недоступна:\n{}", folder),
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

        self._cancel_problem_check()
        self._cancel_details()
        self._cancel_json_check()

        if not self._folder.is_dir():
            self._files = []
            self._entries = []
            self._file_by_path = {}
            self.tree.clear()
            self.summary_label.setText(
                self._format_summary(tr("Файлов: 0"), 0)
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
            self._set_status(tr("Папка недоступна"))
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
        self._set_status(tr("Сканирование… найдено: {}", found_count))

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
                self._format_summary(tr("Файлов: 0"), 0)
            )
            self._set_empty("Не удалось прочитать папку", str(error))
            self._clear_statistics("Нет данных", str(error))
            self._set_busy(False)
            self._set_status(
                tr("Не удалось прочитать папку: {}", error)
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
                tr("Сканирование прервано. Найдено: {}", len(result))
            )
        else:
            self._set_status(
                tr("Сканирование завершено. Найдено: {}", len(result))
            )

    def _show_cancelled_scan(self, files: List[GeoFile]) -> None:
        if files:
            total_size = sum(geo_file.size for geo_file in files)
            self.summary_label.setText(
                self._format_summary(
                    tr("Прервано · найдено: {}", len(files)),
                    total_size,
                )
            )
            return

        self.summary_label.setText(
            self._format_summary(tr("Прервано · найдено: 0"), 0)
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
        self.scan_cancel_button.setText(tr("Прерывание…"))
        self._set_status(tr("Прерывание сканирования…"))

    def shutdown(self) -> None:
        """Остановить фоновые задачи перед удалением панели."""

        self._cancel_problem_check()
        self._cancel_details()
        self._cancel_json_check()

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
        self._cancel_problem_check()
        self._cancel_details()
        self._cancel_json_check()
        self._files = files
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self._entries = []
        self._item_by_path = {}
        self._element_counts = {}
        self._refined_crs_paths = set()
        self._refined_count_paths = set()
        self._refined_size_paths = set()
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
                self._entries.append(
                    (item, self._search_text_for(geo_file))
                )
        finally:
            self.tree.setUpdatesEnabled(True)

        self._update_statistics(files)

        if not files:
            self.summary_label.setText(
                self._format_summary(tr("Файлов: 0"), 0)
            )
            self._set_empty(
                "Файлы не найдены",
                "В выбранной папке нет поддерживаемых пространственных файлов.",
            )
            self._update_controls()
            return

        self._apply_filter()

    def _search_text_for(self, geo_file: GeoFile) -> str:
        return " ".join(
            (
                geo_file.relative_posix,
                geo_file.path.name,
                geo_file.format.name,
                category_label(geo_file.category),
            )
        ).casefold()

    def _make_item(self, geo_file: GeoFile) -> QTreeWidgetItem:
        values = [
            geo_file.relative_posix,
            geo_file.format.name,
            "—",
            "—",
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
            category_label(geo_file.category),
        )
        item.setToolTip(
            2,
            tr(
                "Система координат не уточнена. Нажмите «Проверки»."
            ),
        )
        item.setToolTip(
            3,
            tr(
                "Количество элементов не уточнено. Нажмите «Проверки»."
            ),
        )
        item.setToolTip(
            4,
            tr(
                "Размер основного файла: {} Б. Нажмите «Проверки», "
                "чтобы уточнить полный размер.",
                geo_file.size,
            ),
        )
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
                tr("Проверки не выполнялись. Нажмите «Проверки»."),
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
        return tr("{} · Общий объем: {}", label, format_size(total_size))

    def _set_status(self, message: str) -> None:
        self.status_message_label.setText(message)
        self.status_message_label.setToolTip(message)

    def _show_progress(self, processed: int, total: int) -> None:
        """Показать определённый прогресс операции в статусной строке."""

        if not hasattr(self, "progress_bar"):
            return
        if total <= 0:
            self._hide_progress()
            return
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(min(max(processed, 0), total))
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(True)

    def _show_indeterminate_progress(self) -> None:
        """Показать индикатор операции с неизвестной длительностью."""

        if not hasattr(self, "progress_bar"):
            return
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(True)

    def _hide_progress(self) -> None:
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(False)

    def _update_selection_status(self) -> None:
        total = 0 if self._busy else len(self._entries)
        selected = 0 if self._busy else len(self._selected_files())
        self.selection_label.setText(
            tr("Выбрано: {} из {}", selected, total)
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
            bool(self._files)
            and enabled
            and not self._problem_running
            and not self._json_running
        )
        self._update_selection_status()

    def _show_file_info(self) -> None:
        selected = self._selected_files()
        if len(selected) != 1:
            return

        file_name = selected[0].path.name
        self._set_status(tr("Получение информации: {}", file_name))
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
                tr("Не удалось получить информацию: {}", file_name)
            )
            QMessageBox.critical(
                self,
                "ZGeo",
                tr(
                    "Не удалось получить информацию о файле:\n{}",
                    error_message,
                ),
            )
            return

        self._set_status(tr("Информация: {}", file_name))
        FileInfoDialog(file_info, self).exec()

    def _open_in_explorer(self) -> None:
        selected = self._selected_files()
        if not selected:
            return

        self._set_status(
            tr("Открываю проводник: {}", len(selected))
        )
        errors = reveal_files(
            geo_file.path for geo_file in selected
        )
        if errors:
            self._set_status(tr("Не удалось открыть проводник"))
            QMessageBox.warning(
                self,
                "ZGeo",
                tr(
                    "Не удалось открыть проводник:\n\n{}",
                    "\n".join(errors),
                ),
            )
            return

        self._set_status(
            tr("Проводник открыт: {}", len(selected))
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
                [tr("Итого"), len(self._files), format_size(total_size)]
            )
        return (
            tr("Статистика"),
            self._format_table_headers(),
            rows,
        )

    def _export_file_list(self) -> None:
        files = self._visible_files()
        if not files:
            return

        include_attributes = self._has_problems_column()
        headers = self._tree_headers(include_attributes)

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
            tr("Итого файлов: {}", len(files)),
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
        self._set_status(tr("Экспорт списка в Excel…"))
        exported = export_rows_with_dialog(
            self,
            headers,
            rows,
            tr("{}_файлы.xlsx", folder_name or "zgeo"),
            tr("Файлы"),
            extra_sheets=[self._statistics_sheet_data()],
        )
        if exported is not None:
            self._set_status(
                tr("Список экспортирован: {}", exported.name)
            )
        else:
            self._set_status(tr("Экспорт списка отменён"))

    # ------------------------------------------------------------------
    # Система координат, количество элементов и полный объем
    # ------------------------------------------------------------------

    def _start_details(
        self,
        files: List[GeoFile],
        *,
        read_size: bool,
        read_crs: bool,
        read_count: bool,
        size_paths: Optional[Set[str]] = None,
        action: str = "Уточнение данных",
    ) -> None:
        self._cancel_details()
        if not files or not (read_size or read_crs or read_count):
            return

        self._details_queue = deque(files)
        self._details_total = len(files)
        self._details_processed = 0
        self._details_read_size = read_size
        self._details_read_crs = read_crs
        self._details_read_count = read_count
        self._details_size_paths = (
            {str(geo_file.path) for geo_file in files}
            if size_paths is None
            else set(size_paths)
        )
        self._details_action_source = action
        self._details_size_changed = False
        self._size_index_cache = {}
        self._set_status(
            tr(
                "{}: 0 из {}",
                tr(action),
                self._details_total,
            )
        )
        self._details_timer.start(0)
        self._show_progress(0, self._details_total)
        self._update_cancel_button()

    def _cancel_details(self) -> None:
        self._details_timer.stop()
        self._details_queue.clear()
        self._details_total = 0
        self._details_processed = 0
        self._details_paused = False
        self._details_read_size = False
        self._details_read_crs = False
        self._details_read_count = False
        self._details_size_paths = set()
        self._details_action_source = "Уточнение данных"
        self._details_size_changed = False
        self._size_index_cache = {}
        self._hide_progress()
        self._update_cancel_button()

    def _abort_details(self) -> None:
        if not self._details_queue and not self._details_timer.isActive():
            return
        processed = self._details_processed
        total = self._details_total
        action = self._details_action_source
        self._cancel_details()
        self._update_controls()
        self._set_status(
            tr(
                "{} прервано: {} из {}",
                tr(action),
                processed,
                total,
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
            self._show_progress(
                self._details_processed, self._details_total
            )
            self._details_timer.start(0)

    def _process_next_detail(self) -> None:
        if self._details_paused:
            return
        if not self._details_queue:
            if self._details_total:
                self._apply_filter()
                if self._details_size_changed:
                    self._update_statistics(self._files)
                self._update_controls()
                self._set_status(
                    tr(
                        "{} завершено. Файлов: {}",
                        tr(self._details_action_source),
                        self._details_total,
                    )
                )
            return

        geo_file = self._details_queue.popleft()
        self._details_processed += 1
        self._show_progress(
            self._details_processed, self._details_total
        )
        path_key = str(geo_file.path)

        summary: Optional[LayerSummary] = None
        if self._details_read_crs or self._details_read_count:
            try:
                summary = inspect_layer_summary(geo_file)
            except Exception:
                summary = LayerSummary("—", None)

        refined = geo_file
        if (
            self._details_read_size
            and path_key in self._details_size_paths
        ):
            try:
                detail = measure_geo_file_cached(
                    geo_file, self._size_index_cache
                )
                refined = replace(geo_file, size=detail.total_size)
                self._details_size_changed = True
                self._refined_size_paths.add(path_key)
            except Exception:
                refined = geo_file

        if summary is not None and self._details_read_crs:
            self._refined_crs_paths.add(path_key)
        if summary is not None and self._details_read_count:
            self._refined_count_paths.add(path_key)
            if summary.element_count is None:
                self._element_counts.pop(path_key, None)
            else:
                self._element_counts[path_key] = summary.element_count

        if refined is not geo_file:
            index = self._file_index_by_path.get(path_key)
            if index is not None and 0 <= index < len(self._files):
                if str(self._files[index].path) == path_key:
                    self._files[index] = refined
            self._file_by_path[path_key] = refined

        item = self._item_by_path.get(path_key)
        if item is not None:
            if summary is not None and self._details_read_crs:
                self._update_item_crs(item, summary.crs)
            if summary is not None and self._details_read_count:
                self._update_item_count(item, summary.element_count)
            if refined is not geo_file:
                self._update_item_size(item, refined.size)

        if self._details_queue:
            self._set_status(
                tr(
                    "{}: {} из {} · {}",
                    tr(self._details_action_source),
                    self._details_processed,
                    self._details_total,
                    geo_file.path.name,
                )
            )
            self._details_timer.start(0)
        else:
            self._apply_filter()
            if self._details_size_changed:
                self._update_statistics(self._files)
            self._update_controls()
            self._hide_progress()
            self._set_status(
                tr(
                    "{} завершено. Файлов: {}",
                    tr(self._details_action_source),
                    self._details_total,
                )
            )

    @staticmethod
    def _update_item_crs(item: QTreeWidgetItem, crs: str) -> None:
        item.setText(2, crs)
        if crs in ("—", "-"):
            item.setToolTip(2, tr("Система координат не определена"))
        else:
            item.setToolTip(2, tr("Система координат: {}", crs))

    @staticmethod
    def _update_item_count(
        item: QTreeWidgetItem, element_count: Optional[int]
    ) -> None:
        if element_count is None:
            count_text = "—"
            count_tooltip = tr("Количество элементов не определено")
        else:
            count_text = "{:,}".format(element_count).replace(",", " ")
            count_tooltip = tr(
                "Количество элементов: {}", element_count
            )
        item.setText(3, count_text)
        item.setToolTip(3, count_tooltip)

    @staticmethod
    def _update_item_size(item: QTreeWidgetItem, size: int) -> None:
        item.setText(4, format_size(size))
        item.setToolTip(4, tr("Полный объем набора: {} Б", size))

    # ------------------------------------------------------------------
    # Проверки проблем с атрибутами, наборами и слоями
    # ------------------------------------------------------------------

    def _has_problems_column(self) -> bool:
        return self.tree.columnCount() > 5

    def _ensure_problems_column(self) -> None:
        if self._has_problems_column():
            return

        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(self._tree_headers(True))
        header = self.tree.header()
        header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        header_item = self.tree.headerItem()
        if header_item is not None:
            header_item.setToolTip(
                5,
                tr(
                    "Да — найдены проблемы; Нет — проблем не найдено; "
                    "— — проверка не применима."
                ),
            )
        for item, _search_text in self._entries:
            self._set_problem_cell(
                item, "…", tr("Проверка выполняется…")
            )

    @staticmethod
    def _set_problem_cell(
        item: QTreeWidgetItem,
        text: str,
        tooltip: str,
        issue: Optional[bool] = None,
    ) -> None:
        item.setText(5, text)
        item.setToolTip(5, tooltip)
        item.setData(5, Qt.ItemDataRole.UserRole, issue)
        item.setTextAlignment(
            5,
            Qt.AlignmentFlag.AlignCenter
            | Qt.AlignmentFlag.AlignVCenter,
        )

    def _show_checks_dialog(self) -> None:
        """Открыть окно выбора проверок для найденных файлов."""

        if not self._files:
            return

        include_json_check = any(
            geo_file.extension in JSON_EXTENSIONS
            for geo_file in self._files
        )
        dialog = ChecksDialog(
            self, include_json_check=include_json_check
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._run_checks(dialog.selected_checks())

    def _run_checks(self, checks: List[str]) -> None:
        """Выполнить выбранные проверки."""

        if not checks:
            return

        remaining = [
            check for check in checks if check != CHECK_JSON_GEOJSON
        ]
        if CHECK_JSON_GEOJSON in checks:
            json_files = [
                geo_file
                for geo_file in self._files
                if geo_file.extension in JSON_EXTENSIONS
            ]
            if json_files:
                self._start_json_check(json_files, remaining)
                return
            if not remaining:
                self._set_status(
                    tr("Нет JSON-файлов для проверки")
                )
                return

        self._run_checks_after_json(remaining)

    def _run_checks_after_json(self, checks: List[str]) -> None:
        """Выполнить проверки, не требующие разбора JSON."""

        if not checks:
            self._update_controls()
            return

        read_size_all = CHECK_SIZE in checks
        read_size_shp = CHECK_SIZE_SHP in checks and not read_size_all
        read_size_mif_mid = (
            CHECK_SIZE_MIF_MID in checks and not read_size_all
        )

        size_paths: Set[str] = set()
        if read_size_all:
            size_paths = {
                str(geo_file.path) for geo_file in self._files
            }
        else:
            if read_size_shp:
                size_paths.update(
                    str(geo_file.path)
                    for geo_file in self._files
                    if geo_file.extension == ".shp"
                )
            if read_size_mif_mid:
                size_paths.update(
                    str(geo_file.path)
                    for geo_file in self._files
                    if geo_file.extension == ".mif"
                )

        read_size = bool(size_paths)
        if read_size_all:
            action = "Уточнение размера"
        elif read_size_shp and read_size_mif_mid:
            action = "Уточнение размера"
        elif read_size_shp:
            action = "Уточнение размера SHP"
        elif read_size_mif_mid:
            action = "Уточнение размера MIF/MID"
        else:
            action = "Уточнение размера"

        problem_checks = [
            check for check in checks if check in PROBLEM_CHECKS
        ]

        if read_size:
            detail_files = list(self._files)
            if (read_size_shp or read_size_mif_mid) and not read_size_all:
                detail_files = [
                    geo_file
                    for geo_file in detail_files
                    if str(geo_file.path) in size_paths
                ]
            self._start_details(
                detail_files,
                read_size=True,
                read_crs=False,
                read_count=False,
                size_paths=size_paths,
                action=action,
            )
        elif not problem_checks:
            self._set_status(
                tr("Нет файлов для выбранных проверок")
            )
            return

        if problem_checks:
            self._start_problem_check(problem_checks)

    # ------------------------------------------------------------------
    # Проверка JSON на соответствие GeoJSON
    # ------------------------------------------------------------------

    def _start_json_check(
        self, files: List[GeoFile], after_checks: List[str]
    ) -> None:
        if self._json_running or not files:
            return

        self._cancel_details()
        self._json_queue = deque(files)
        self._json_total = len(files)
        self._json_processed = 0
        self._json_removed = []
        self._json_after_checks = list(after_checks)
        self._json_running = True
        self._set_status(
            tr(
                "Проверка JSON на формат GeoJSON: 0 из {}",
                self._json_total,
            )
        )
        self._json_timer.start(0)
        self._show_progress(0, self._json_total)
        self._update_file_actions()
        self._update_cancel_button()

    def _process_next_json_check(self) -> None:
        if not self._json_running:
            return
        if not self._json_queue:
            self._finish_json_check()
            return

        geo_file = self._json_queue.popleft()
        self._json_processed += 1
        self._show_progress(self._json_processed, self._json_total)

        try:
            check = check_json_file(geo_file.path)
        except Exception:
            check = None

        if check is None or not check.is_geojson:
            self._json_removed.append(str(geo_file.path))

        if self._json_queue:
            self._set_status(
                tr(
                    "Проверка JSON: {} из {} · {}",
                    self._json_processed,
                    self._json_total,
                    geo_file.path.name,
                )
            )
            self._json_timer.start(0)
        else:
            self._finish_json_check()

    def _finish_json_check(self) -> None:
        total = self._json_total
        removed = len(self._json_removed)
        self._json_timer.stop()
        self._json_queue.clear()
        self._json_running = False
        self._hide_progress()

        if self._json_removed:
            self._remove_files(set(self._json_removed))
        self._json_removed = []

        if removed:
            self._set_status(
                tr(
                    "Проверка JSON завершена: проверено {} · исключено {}",
                    total,
                    removed,
                )
            )
        else:
            self._set_status(
                tr(
                    "Проверка JSON завершена: все файлы соответствуют "
                    "GeoJSON. Проверено: {}",
                    total,
                )
            )

        after_checks = self._json_after_checks
        self._json_after_checks = []
        self._update_file_actions()
        self._update_cancel_button()

        if after_checks and self._files:
            self._run_checks_after_json(after_checks)
        else:
            self._update_controls()

    def _abort_json_check(self) -> None:
        if not self._json_running:
            return

        processed = self._json_processed
        total = self._json_total
        removed = len(self._json_removed)
        self._json_timer.stop()
        self._json_queue.clear()
        self._json_running = False
        self._json_after_checks = []
        self._hide_progress()

        if self._json_removed:
            self._remove_files(set(self._json_removed))
        self._json_removed = []

        self._update_file_actions()
        self._update_cancel_button()
        self._set_status(
            tr(
                "Проверка JSON прервана: проверено {} из {} · исключено {}",
                processed,
                total,
                removed,
            )
        )

    def _cancel_json_check(self) -> None:
        self._json_timer.stop()
        self._json_queue.clear()
        self._json_running = False
        self._json_total = 0
        self._json_processed = 0
        self._json_removed = []
        self._json_after_checks = []
        self._hide_progress()
        if hasattr(self, "cancel_task_button"):
            self._update_cancel_button()

    def _remove_files(self, paths: Set[str]) -> None:
        """Исключить файлы из списка и обновить все сводные данные."""

        if not paths:
            return

        self.tree.setUpdatesEnabled(False)
        try:
            remaining: List[GeoFile] = []
            for geo_file in self._files:
                path_key = str(geo_file.path)
                if path_key not in paths:
                    remaining.append(geo_file)
                    continue

                item = self._item_by_path.pop(path_key, None)
                if item is not None:
                    index = self.tree.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.tree.takeTopLevelItem(index)
                self._file_by_path.pop(path_key, None)
                self._element_counts.pop(path_key, None)
                self._refined_crs_paths.discard(path_key)
                self._refined_count_paths.discard(path_key)
                self._refined_size_paths.discard(path_key)
                self._problem_issues.pop(path_key, None)
                self._problem_checked_paths.discard(path_key)
                self._problem_candidate_paths.discard(path_key)
            self._files = remaining
            self._entries = [
                (item, search_text)
                for item, search_text in self._entries
                if str(item.data(0, Qt.ItemDataRole.UserRole))
                not in paths
            ]
            self._file_index_by_path = {
                str(geo_file.path): index
                for index, geo_file in enumerate(self._files)
            }
        finally:
            self.tree.setUpdatesEnabled(True)

        self._problem_issue_count = sum(
            1
            for geo_file in self._files
            if self._problem_issues.get(str(geo_file.path))
        )

        if not self._files:
            self.summary_label.setText(
                self._format_summary(tr("Файлов: 0"), 0)
            )
            self._set_empty(
                "Файлы не найдены",
                "Все найденные файлы исключены проверками.",
            )
            self._clear_statistics(
                "Нет данных",
                "Нет файлов для построения диаграмм.",
            )
            self._reset_problems_filter()
        else:
            self._update_statistics(self._files)
            self._apply_filter()
            self._update_problems_summary()

        self._update_controls()

    def _start_problem_check(self, checks: List[str]) -> None:
        if self._problem_running or not self._files:
            return

        self._problem_checked = False
        self._problem_interrupted = False
        self._problem_issues.clear()
        self._problem_checked_paths.clear()
        self._problem_candidate_paths.clear()
        self._problem_selected = tuple(checks)
        self._problem_file_cache = {}
        self._set_problems_filter_available(False)
        self.problems_label.setText(tr("Проблемных файлов: 0"))
        self.problems_label.setToolTip(tr("Идёт проверка…"))
        self.problems_label.setVisible(True)

        self._ensure_problems_column()
        for item, _search_text in self._entries:
            self._set_problem_cell(
                item, "…", tr("Проверка выполняется…")
            )

        needs_layers = any(
            check in LAYER_PROBLEM_CHECKS for check in checks
        )
        if needs_layers:
            allowed = {VECTOR, TABLE, OTHER}
            if CHECK_CRS_QUALITY in checks:
                allowed.add(RASTER)
            candidates = [
                geo_file
                for geo_file in self._files
                if geo_file.category in allowed
            ]
        else:
            candidates = [
                geo_file
                for geo_file in self._files
                if CHECK_DATASET_INTEGRITY in checks
                and geo_file.extension in (".shp", ".mif", ".tab")
            ]

        candidate_paths = {
            str(geo_file.path) for geo_file in candidates
        }
        self._problem_candidate_paths = set(candidate_paths)
        for geo_file in self._files:
            if str(geo_file.path) in candidate_paths:
                continue
            item = self._item_by_path.get(str(geo_file.path))
            if item is not None:
                self._set_problem_cell(
                    item,
                    "—",
                    tr("Проверка не применима к этому файлу."),
                    False,
                )

        if not candidates:
            self._problem_checked = True
            self._hide_progress()
            self._update_problems_summary()
            self.problems_label.setToolTip("")
            self._set_problems_filter_available(True)
            self._apply_filter()
            self._set_status(
                tr("Нет файлов для выбранных проверок")
            )
            self._update_file_actions()
            self._update_cancel_button()
            return

        self._problem_queue = deque(candidates)
        self._problem_total = len(candidates)
        self._problem_processed = 0
        self._problem_issue_count = 0
        self._problem_running = True
        self._show_progress(0, self._problem_total)
        self.check_attributes_button.setToolTip(
            tr("Проверки выполняются…")
        )
        self._pause_details()
        self._apply_filter()
        self._update_file_actions()
        self._update_cancel_button()
        self._set_status(
            tr("Проверки: 0 из {}", self._problem_total)
        )
        self._problem_timer.start(0)

    def _process_next_problem_check(self) -> None:
        if not self._problem_queue:
            self._finish_problem_check()
            return

        geo_file = self._problem_queue.popleft()
        self._problem_processed += 1
        self._show_progress(
            self._problem_processed, self._problem_total
        )

        try:
            issues, applicable = self._inspect_problems(geo_file)
        except Exception:
            issues, applicable = [], False

        path_key = str(geo_file.path)
        self._problem_issues[path_key] = tuple(issues)
        if applicable:
            self._problem_checked_paths.add(path_key)
        item = self._item_by_path.get(path_key)
        if item is not None:
            self._update_item_problems(item, issues, applicable)

        if issues:
            self._problem_issue_count += 1
            self._update_problems_summary()

        if self._problem_queue:
            self._set_status(
                tr(
                    "Проверки: {} из {} · {}",
                    self._problem_processed,
                    self._problem_total,
                    geo_file.path.name,
                )
            )
            self._problem_timer.start(0)
        else:
            self._finish_problem_check()

    def _inspect_problems(
        self, geo_file: GeoFile
    ) -> Tuple[List[QualityIssue], bool]:
        checks = self._problem_selected
        issues: List[QualityIssue] = []
        applicable = False

        files = directory_files(
            geo_file.path.parent, self._problem_file_cache
        )

        if CHECK_DATASET_INTEGRITY in checks:
            if geo_file.extension in (".shp", ".mif", ".tab"):
                applicable = True
                issues.extend(
                    completeness_issues(geo_file, files)
                )
            if geo_file.extension == ".shp":
                dbf_name = geo_file.path.stem.casefold() + ".dbf"
                if dbf_name in files:
                    applicable = True
                    issues.extend(
                        dbf_encoding_issues(geo_file, files)
                    )

        needs_layers = any(
            check in LAYER_PROBLEM_CHECKS for check in checks
        )
        if not needs_layers:
            return issues, applicable

        try:
            file_info = inspect_geofile(geo_file)
        except Exception:
            return issues, applicable

        vector_layers = file_info.vector_layers
        raster_layers = file_info.raster_layers
        layer_fields = [
            (
                layer.name,
                tuple(field.name for field in layer.fields),
            )
            for layer in vector_layers
        ]
        layer_counts = [
            (layer.name, layer.feature_count)
            for layer in vector_layers
        ]
        crs_values = [layer.crs for layer in vector_layers]
        crs_values.extend(layer.crs for layer in raster_layers)

        if CHECK_FIELD_NAMES in checks and vector_layers:
            applicable = True
            non_latin = [
                name
                for _layer_name, names in layer_fields
                for name in names
                if has_non_latin_characters(name)
            ]
            if non_latin:
                issues.append(
                    QualityIssue(
                        CHECK_FIELD_NAMES,
                        "Нелатинские имена полей:\n{}",
                        ("\n".join(dict.fromkeys(non_latin)),),
                    )
                )
            issues.extend(field_name_issues(layer_fields))
            issues.extend(truncated_duplicate_issues(layer_fields))

        if CHECK_CRS_QUALITY in checks and (
            vector_layers or raster_layers
        ):
            applicable = True
            issues.extend(crs_issues(crs_values))
            self._apply_crs_summary(geo_file, crs_values)

        if CHECK_COUNT_QUALITY in checks and vector_layers:
            applicable = True
            issues.extend(empty_layer_issues(layer_counts))
            self._apply_count_summary(geo_file, layer_counts)

        if CHECK_GEOMETRY_COORDINATES in checks and vector_layers:
            geometry_issues, geometry_applicable = (
                inspect_geometry_and_coordinates(
                    geo_file,
                    check_geometry=True,
                    check_coordinates=True,
                )
            )
            if geometry_applicable:
                applicable = True
            issues.extend(geometry_issues)

        return issues, applicable

    def _apply_crs_summary(
        self, geo_file: GeoFile, values: List[str]
    ) -> None:
        unique = {value for value in values if value}
        if not unique:
            text = "—"
        elif len(unique) == 1:
            text = next(iter(unique))
        else:
            text = tr("Разные")

        path_key = str(geo_file.path)
        self._refined_crs_paths.add(path_key)
        item = self._item_by_path.get(path_key)
        if item is not None:
            self._update_item_crs(item, text)

    def _apply_count_summary(
        self, geo_file: GeoFile, layer_counts: List[Tuple[str, int]]
    ) -> None:
        counts = [count for _name, count in layer_counts]
        if not counts or any(count < 0 for count in counts):
            total = None
        else:
            total = sum(counts)

        path_key = str(geo_file.path)
        self._refined_count_paths.add(path_key)
        if total is None:
            self._element_counts.pop(path_key, None)
        else:
            self._element_counts[path_key] = total

        item = self._item_by_path.get(path_key)
        if item is not None:
            self._update_item_count(item, total)

    @staticmethod
    def _update_item_problems(
        item: QTreeWidgetItem,
        issues: List[QualityIssue],
        applicable: bool,
    ) -> None:
        if issues:
            item.setText(5, tr("Да"))
            item.setToolTip(
                5,
                "\n".join(
                    tr(issue.message, *issue.args)
                    for issue in issues
                ),
            )
            item.setData(5, Qt.ItemDataRole.UserRole, True)
        elif applicable:
            item.setText(5, tr("Нет"))
            item.setToolTip(5, tr("Проблем не найдено."))
            item.setData(5, Qt.ItemDataRole.UserRole, False)
        else:
            item.setText(5, "—")
            item.setToolTip(
                5, tr("Проверка не применима к этому файлу.")
            )
            item.setData(5, Qt.ItemDataRole.UserRole, False)

    def _finish_problem_check(self) -> None:
        total = self._problem_total
        issues = self._problem_issue_count
        self._problem_running = False
        self._problem_checked = True
        self._problem_interrupted = False
        self._problem_queue.clear()
        self.check_attributes_button.setToolTip(
            tr(CHECKS_TOOLTIP)
        )
        self._update_problems_summary()
        self._set_problems_filter_available(True)
        self._update_file_actions()
        self._hide_progress()
        self._resume_details()
        self._update_cancel_button()
        self._apply_filter()

        if issues:
            self._set_status(
                tr(
                    "Проверки завершены: файлов {} · с проблемами {}",
                    total,
                    issues,
                )
            )
        else:
            self._set_status(
                tr(
                    "Проверки завершены: проблем не найдено. "
                    "Файлов: {}",
                    total,
                )
            )

    def _abort_problem_check(self) -> None:
        if not self._problem_running:
            return

        processed = self._problem_processed
        total = self._problem_total
        issues = self._problem_issue_count
        self._problem_timer.stop()
        self._problem_queue.clear()
        self._problem_running = False
        self._problem_checked = processed > 0
        self._problem_interrupted = self._problem_checked
        self.check_attributes_button.setToolTip(
            tr(CHECKS_TOOLTIP)
        )
        self._update_problems_summary()
        self._set_problems_filter_available(self._problem_checked)
        self._hide_progress()
        self._resume_details()
        self._update_file_actions()
        self._update_cancel_button()
        self._apply_filter()
        self._set_status(
            tr(
                "Проверки прерваны: обработано {} из {} · проблем {}",
                processed,
                total,
                issues,
            )
        )

    def _cancel_problem_check(self) -> None:
        self._problem_timer.stop()
        self._problem_queue.clear()
        self._problem_running = False
        self._problem_total = 0
        self._problem_processed = 0
        self._problem_issue_count = 0
        self._problem_checked = False
        self._problem_interrupted = False
        self._problem_issues.clear()
        self._problem_checked_paths.clear()
        self._problem_candidate_paths.clear()
        self._problem_selected = ()
        self._problem_file_cache = {}
        self._reset_problems_filter()
        self._hide_progress()
        if hasattr(self, "check_attributes_button"):
            self.check_attributes_button.setToolTip(
                tr(CHECKS_TOOLTIP)
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
        self._problem_checked = False
        if not hasattr(self, "problems_label"):
            return
        self._set_problems_filter_available(False)
        self.problems_label.setText(tr("Проблемных файлов: 0"))
        self.problems_label.setToolTip("")
        self.problems_label.setVisible(False)

    def _update_problems_summary(self) -> None:
        if not hasattr(self, "problems_label"):
            return
        self.problems_label.setText(
            tr("Проблемных файлов: {}", self._problem_issue_count)
        )
        if (
            self._problem_interrupted
            and self._problem_processed < self._problem_total
        ):
            self.problems_label.setToolTip(
                tr(
                    "Проверка прервана: обработано {} из {} файлов",
                    self._problem_processed,
                    self._problem_total,
                )
            )
        else:
            self.problems_label.setToolTip("")
        self.problems_label.setVisible(
            self._problem_checked or self._problem_running
        )

    def _update_cancel_button(self) -> None:
        if not hasattr(self, "cancel_task_button"):
            return
        active = not self._busy and (
            self._problem_running
            or self._json_running
            or bool(self._details_queue)
            or self._details_timer.isActive()
        )
        self.cancel_task_button.setVisible(active)
        self.cancel_task_button.setEnabled(active)
        if not active:
            return
        if self._json_running:
            tooltip = tr("Прервать проверку JSON")
        elif self._problem_running:
            tooltip = tr("Прервать проверки")
        else:
            tooltip = tr("Прервать уточнение данных")
        self.cancel_task_button.setToolTip(tooltip)

    def _cancel_long_operation(self) -> None:
        if self._json_running:
            self._abort_json_check()
        elif self._problem_running:
            self._abort_problem_check()
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
            tr(
                "Файлов: {} · {}",
                total_count,
                format_size(total_size),
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
                    tooltip=tr(
                        "{}: {} файлов ({:.0f}%), {}",
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
            tooltip = tr(
                "{}: {} файлов ({:.0f}%), {}",
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
                    category_label(type_stat.category),
                ).rstrip(" ·")
            )

            count_item = QTableWidgetItem(
                "{:,}".format(type_stat.count).replace(",", " ")
            )
            count_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            count_item.setToolTip(
                tr("Файлов: {}", type_stat.count)
            )
            count_item.setData(
                Qt.ItemDataRole.UserRole, type_stat.count
            )

            size_item = QTableWidgetItem(format_size(type_stat.total_size))
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            size_item.setToolTip(
                tr("{} Б", type_stat.total_size)
            )

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
            [tr("Итого"), total_count, format_size(total_size)],
        ]
        self._set_status(tr("Экспорт статистики в Excel…"))
        exported = export_table_with_dialog(
            self,
            self.format_table,
            tr("{}_форматы.xlsx", folder_name or "zgeo"),
            tr("Форматы"),
            summary_rows=summary_rows,
        )
        if exported is not None:
            self._set_status(
                tr("Статистика экспортирована: {}", exported.name)
            )
        else:
            self._set_status(tr("Экспорт статистики отменён"))

    def _clear_statistics(self, title: str, hint: str) -> None:
        self.stats_summary_label.setText(tr("Файлов: 0 · 0 Б"))
        self.size_chart.set_rows([])
        self.type_chart.set_rows([])
        self.format_table.setRowCount(0)
        self._fit_format_table_height()
        self.export_formats_button.setEnabled(False)
        self._set_stats_empty(title, hint)

    def _set_stats_empty(self, title: str, hint: str) -> None:
        self._stats_empty_title_source = title
        self._stats_empty_hint_source = hint
        self.stats_empty_title_label.setText(tr(title))
        self.stats_empty_hint_label.setText(tr(hint))
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
                tr(
                    "Фильтр: показано {} из {}",
                    visible,
                    len(self._entries),
                )
            )
        elif self.problems_only_checkbox.isChecked():
            self._set_status(
                tr(
                    "Фильтр «Только проблемные»: показано {} из {}",
                    visible,
                    len(self._entries),
                )
            )
        else:
            self._set_status(tr("Фильтр очищен"))

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
                hidden = (
                    item.data(5, Qt.ItemDataRole.UserRole) is not True
                )
            item.setHidden(hidden)
            if not hidden:
                visible += 1
                path = item.data(0, Qt.ItemDataRole.UserRole)
                geo_file = self._file_by_path.get(str(path))
                if geo_file is not None:
                    visible_size += geo_file.size

        if not self._entries:
            self.summary_label.setText(
                self._format_summary(tr("Файлов: 0"), 0)
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
                    tr(
                        "Показано: {} из {}",
                        visible,
                        len(self._entries),
                    ),
                    visible_size,
                )
            )
        else:
            self.summary_label.setText(
                self._format_summary(
                    tr("Файлов: {}", len(self._entries)),
                    visible_size,
                )
            )

        self._update_file_actions()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.summary_label.setText(tr("Сканирование…"))
            self._set_status(tr("Сканирование папки…"))
            self.scan_file_label.setText("—")
            self.scan_file_label.setToolTip("")
            self.scan_found_label.setText("0")
            self.scan_progress.setRange(0, 0)
            self._show_indeterminate_progress()
            self.scan_cancel_button.setText(tr("Прервать"))
            self.scan_cancel_button.setEnabled(True)
            self.stack.setCurrentWidget(self.scan_page)
            self._set_stats_empty(
                "Сканирование…",
                "Диаграммы обновятся после завершения поиска файлов.",
            )
        else:
            self.scan_cancel_button.setEnabled(False)
            self.scan_cancel_button.setText(tr("Прервать"))
            self._hide_progress()
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
                self._problem_checked and enabled
            )
        self._update_file_actions()
        self._update_cancel_button()

    def _retranslate_ui(self) -> None:
        """Обновить все подписи интерфейса без пересоздания панели."""

        self.setWindowTitle(tr("ZGeo — геоданные"))
        self._update_language_button()

        self.brand_subtitle_label.setText(
            tr("Каталог пространственных данных")
        )
        version = get_plugin_version()
        self.version_label.setText(tr("Версия {}", version))
        self.version_label.setToolTip(
            tr("Версия плагина ZGeo: {}", version)
        )
        self.folder_caption_label.setText(tr("ПАПКА"))
        if self._folder is None:
            self.folder_name_label.setText(tr("Папка не выбрана"))
            self.folder_path_label.setText(
                tr("Выберите каталог на диске")
            )
        self.choose_button.setText(tr("Выбрать папку"))
        self.refresh_button.setToolTip(tr("Пересканировать папку"))
        self.refresh_button.setAccessibleName(tr("Пересканировать папку"))

        self.tabs.setTabText(0, tr("Файлы"))
        self.tabs.setTabText(1, tr("Статистика"))
        self.tabs.setTabText(2, tr("Настройки"))
        self.tabs.setTabToolTip(
            0, tr("Найденные пространственные файлы")
        )
        self.tabs.setTabToolTip(
            1, tr("Диаграммы по размеру и типу файлов")
        )
        self.tabs.setTabToolTip(
            2, tr("Форматы файлов, которые нужно искать")
        )

        self.filter_edit.setPlaceholderText(
            tr("Фильтр по имени, формату или пути")
        )
        self.filter_edit.setAccessibleName(
            tr("Фильтр по имени, формату или пути")
        )
        self.problems_only_checkbox.setText(tr("Только проблемные"))
        self.problems_only_checkbox.setToolTip(
            tr(
                "Показывать только файлы, у которых проверки нашли "
                "проблемы"
            )
        )

        self.info_button.setToolTip(tr("Информация"))
        self.info_button.setAccessibleName(tr("Информация"))
        self.explorer_button.setToolTip(tr("Открыть в проводнике"))
        self.explorer_button.setAccessibleName(
            tr("Открыть в проводнике")
        )
        self.export_list_button.setToolTip(tr("Экспорт в Excel"))
        self.export_list_button.setAccessibleName(
            tr("Экспорт в Excel")
        )
        self.check_attributes_button.setAccessibleName(
            tr("Проверки")
        )
        if self._json_running:
            self.check_attributes_button.setToolTip(
                tr("Проверка JSON выполняется…")
            )
        elif not self._problem_running:
            self.check_attributes_button.setToolTip(
                tr(CHECKS_TOOLTIP)
            )
        else:
            self.check_attributes_button.setToolTip(
                tr("Проверки выполняются…")
            )
        self.cancel_task_button.setToolTip(
            tr("Прервать длительную операцию")
        )
        self.cancel_task_button.setAccessibleName(
            tr("Прервать операцию")
        )
        self.progress_bar.setAccessibleName(tr("Ход выполнения"))

        self._retranslate_scan_page()
        self._retranslate_stats_page()
        self._retranslate_settings_page()
        self._retranslate_tree()
        self._retranslate_status()

        if self._busy:
            self.summary_label.setText(tr("Сканирование…"))
        elif self._files:
            self._update_statistics(self._files)
            self._apply_filter()
        elif self._folder is not None:
            self.summary_label.setText(
                self._format_summary(tr("Файлов: 0"), 0)
            )
            self._clear_statistics(
                "Файлы не найдены",
                "После сканирования диаграммы появятся здесь.",
            )
        else:
            self.summary_label.setText(
                tr("Файлов: 0 · Общий объем: 0 Б")
            )
            self._set_stats_empty(
                "Статистика пуста",
                "Выберите папку и выполните сканирование. Здесь появятся "
                "диаграммы по размеру и типу файлов.",
            )

        self._retranslate_empty_pages()
        self._update_problems_summary()
        self._update_selection_status()
        self._update_file_actions()
        self._update_cancel_button()

    def _retranslate_scan_page(self) -> None:
        self.scan_title_label.setText(tr("Сканирование папки…"))
        self.scan_hint_label.setText(
            tr("Просматриваем файлы, включая вложенные папки.")
        )
        self.scan_file_caption.setText(tr("Имя файла"))
        self.scan_found_caption.setText(tr("Найдено"))
        if self._busy and not self.scan_cancel_button.isEnabled():
            self.scan_cancel_button.setText(tr("Прерывание…"))
        else:
            self.scan_cancel_button.setText(tr("Прервать"))

    def _retranslate_stats_page(self) -> None:
        self.stats_note_label.setText(
            tr("Диаграммы построены по всем найденным файлам.")
        )
        self.size_group.setTitle(tr("По размеру"))
        self.size_chart.setAccessibleName(tr("Диаграмма по размеру"))
        self.size_note_label.setText(
            tr(
                "Количество файлов в диапазонах размера; справа — "
                "суммарный объём."
            )
        )
        self.type_group.setTitle(tr("По типу"))
        self.type_chart.setAccessibleName(tr("Диаграмма по типу"))
        self.type_note_label.setText(
            tr(
                "Количество файлов по формату; справа — суммарный объём. "
                "Показаны основные форматы, остальные объединены "
                "в «Другие форматы»."
            )
        )
        self.format_group.setTitle(tr("Статистика по форматам"))
        self.format_note_label.setText(
            tr(
                "Полная статистика по каждому формату. "
                "Объём учитывает сопутствующие файлы наборов данных."
            )
        )
        self.format_table.setHorizontalHeaderLabels(
            self._format_table_headers()
        )
        self.format_table.setAccessibleName(
            tr("Статистика по форматам")
        )
        self.export_formats_button.setText(tr("Экспорт в Excel"))

    def _retranslate_settings_page(self) -> None:
        self.select_all_button.setText(tr("Выбрать все"))
        self.select_all_button.setToolTip(tr("Отметить все форматы"))
        self.clear_all_button.setText(tr("Сбросить все"))
        self.clear_all_button.setToolTip(tr("Снять все отметки"))
        self.only_vector_button.setText(tr("Только вектор"))
        self.only_vector_button.setToolTip(
            tr("Оставить только векторные форматы")
        )
        self.only_raster_button.setText(tr("Только растр"))
        self.only_raster_button.setToolTip(
            tr("Оставить только растровые форматы")
        )
        self.settings_hint_label.setText(
            tr(
                "Отметьте форматы, которые должны попадать в каталог. "
                "Изменения применяются при следующем сканировании."
            )
        )
        for category, group_box in self._category_group_boxes.items():
            group_box.setTitle(category_label(category))
        for group in get_format_groups():
            checkbox = self._format_checkboxes.get(group.name)
            if checkbox is None:
                continue
            checkbox.setText(self._format_checkbox_text(group))
            checkbox.setToolTip(
                tr("Расширения: {}", ", ".join(group.extensions))
            )

    def _retranslate_tree(self) -> None:
        include_problems = self._has_problems_column()
        self.tree.setHeaderLabels(
            self._tree_headers(include_problems)
        )
        self.tree.setAccessibleName(
            tr("Найденные пространственные файлы")
        )
        if include_problems:
            header_item = self.tree.headerItem()
            if header_item is not None:
                header_item.setToolTip(
                    5,
                    tr(
                        "Да — найдены проблемы; Нет — проблем не найдено; "
                        "— — проверка не применима."
                    ),
                )

        new_entries = []
        for item, _search_text in self._entries:
            path_key = item.data(0, Qt.ItemDataRole.UserRole)
            geo_file = self._file_by_path.get(str(path_key))
            if geo_file is None:
                continue
            item.setToolTip(1, category_label(geo_file.category))

            crs_text = item.text(2)
            if crs_text in ("Разные", "Mixed"):
                crs_text = tr("Разные")
            elif crs_text in ("Не определена", "Undefined"):
                crs_text = tr("Не определена")
            item.setText(2, crs_text)
            if crs_text == "…":
                item.setToolTip(
                    2, tr("Система координат читается…")
                )
            elif str(path_key) not in self._refined_crs_paths:
                item.setToolTip(
                    2,
                    tr(
                        "Система координат не уточнена. "
                        "Нажмите «Проверки»."
                    ),
                )
            elif crs_text in ("—", "-"):
                item.setToolTip(
                    2, tr("Система координат не определена")
                )
            else:
                item.setToolTip(
                    2, tr("Система координат: {}", crs_text)
                )

            count_text = item.text(3)
            if count_text == "…":
                item.setToolTip(
                    3, tr("Количество элементов читается…")
                )
            elif str(path_key) not in self._refined_count_paths:
                item.setToolTip(
                    3,
                    tr(
                        "Количество элементов не уточнено. "
                        "Нажмите «Проверки»."
                    ),
                )
            elif count_text == "—":
                item.setToolTip(
                    3, tr("Количество элементов не определено")
                )
            else:
                item.setToolTip(
                    3,
                    tr("Количество элементов: {}", count_text),
                )

            item.setText(4, format_size(geo_file.size))
            if str(path_key) in self._refined_size_paths:
                item.setToolTip(
                    4, tr("Полный объем набора: {} Б", geo_file.size)
                )
            else:
                item.setToolTip(
                    4,
                    tr(
                        "Размер основного файла: {} Б. Нажмите "
                        "«Проверки», чтобы уточнить полный размер.",
                        geo_file.size,
                    ),
                )
            if include_problems:
                path_text = str(geo_file.path)
                issues = self._problem_issues.get(path_text)
                if issues:
                    self._update_item_problems(
                        item, list(issues), True
                    )
                elif path_text in self._problem_checked_paths:
                    self._update_item_problems(item, [], True)
                elif path_text in self._problem_candidate_paths:
                    if path_text in self._problem_issues:
                        self._update_item_problems(item, [], False)
                    elif self._problem_running:
                        self._set_problem_cell(
                            item,
                            "…",
                            tr("Проверка выполняется…"),
                        )
                    else:
                        self._update_item_problems(item, [], False)
                elif self._problem_checked or self._problem_running:
                    self._update_item_problems(item, [], False)
                else:
                    self._set_problem_cell(
                        item,
                        "—",
                        tr(
                            "Проверки не выполнялись. "
                            "Нажмите «Проверки»."
                        ),
                        False,
                    )
            new_entries.append(
                (item, self._search_text_for(geo_file))
            )
        self._entries = new_entries

    def _retranslate_status(self) -> None:
        if self._busy:
            self._set_status(
                tr(
                    "Сканирование… найдено: {}",
                    self.scan_found_label.text(),
                )
            )
        elif self._json_running:
            self._set_status(
                tr(
                    "Проверка JSON: {} из {}",
                    self._json_processed,
                    self._json_total,
                )
            )
        elif self._problem_running:
            self._set_status(
                tr(
                    "Проверки: {} из {}",
                    self._problem_processed,
                    self._problem_total,
                )
            )
        elif self._details_queue or self._details_timer.isActive():
            self._set_status(
                tr(
                    "{}: {} из {}",
                    tr(self._details_action_source),
                    self._details_processed,
                    self._details_total,
                )
            )
        else:
            self._set_status(tr("Готово"))

    def _retranslate_empty_pages(self) -> None:
        self.empty_title_label.setText(tr(self._empty_title_source))
        self.empty_hint_label.setText(tr(self._empty_hint_source))
        self.stats_empty_title_label.setText(
            tr(self._stats_empty_title_source)
        )
        self.stats_empty_hint_label.setText(
            tr(self._stats_empty_hint_source)
        )

    def _set_empty(self, title: str, hint: str) -> None:
        self._empty_title_source = title
        self._empty_hint_source = hint
        self.empty_title_label.setText(tr(title))
        self.empty_hint_label.setText(tr(hint))
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

