"""Плавающая панель ZGeo."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import QFileInfo, QSettings, QSize, Qt
from qgis.PyQt.QtGui import QFont, QIcon, QPalette
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .charts import BarChart, BarDatum
from .explorer import reveal_files
from .file_info import inspect_geofile
from .formatting import format_size
from .info_dialog import FileInfoDialog
from .scanner import OTHER, RASTER, TABLE, VECTOR, GeoFile, scan_folder
from .stats import build_size_distribution, build_type_distribution

CATEGORY_LABELS = {
    VECTOR: "Векторные данные",
    RASTER: "Растровые данные",
    TABLE: "Таблица",
    OTHER: "Прочие данные",
}

LAST_FOLDER_KEY = "zgeo/last_folder"
ICON_PATH = Path(__file__).with_name("icon.svg")
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
        self._busy = False
        self._settings = QSettings()
        self._icon_provider = QFileIconProvider()
        self._icon_cache: Dict[str, QIcon] = {}

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
        self.setMinimumWidth(420)
        self.resize(560, 700)

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
        self.tabs.setTabToolTip(
            0, "Найденные пространственные файлы"
        )
        self.tabs.setTabToolTip(
            1, "Диаграммы по размеру и типу файлов"
        )
        layout.addWidget(self.tabs, 1)

        self.setWidget(root)

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self.summary_label = QLabel("Файлов: 0")
        self._set_font(self.summary_label, 0, bold=True)
        layout.addWidget(self.summary_label)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр по имени, формату или пути")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_tree())
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

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tree(self) -> QTreeWidget:
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Файл", "Формат", "Размер"])
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
        header.resizeSection(1, 145)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
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

        selected = QFileDialog.getExistingDirectory(
            self,
            "Выбрать папку с геоданными",
            start_folder,
            QFileDialog.Option.ShowDirsOnly,
        )
        if selected:
            self.set_folder(Path(selected))

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

        if not self._folder.is_dir():
            self._files = []
            self._entries = []
            self.tree.clear()
            self.summary_label.setText("Файлов: 0")
            self._set_empty(
                "Папка недоступна",
                "Каталог был перемещён или удалён. Выберите другую папку.",
            )
            self._clear_statistics(
                "Нет данных",
                "Каталог был перемещён или удалён. Выберите другую папку.",
            )
            self._update_controls()
            return

        self._set_busy(True)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._files = scan_folder(self._folder)
        except OSError as error:
            self._files = []
            self._entries = []
            self.tree.clear()
            self.summary_label.setText("Файлов: 0")
            self._set_empty("Не удалось прочитать папку", str(error))
            self._clear_statistics("Нет данных", str(error))
        else:
            self._populate(self._files)
        finally:
            QApplication.restoreOverrideCursor()
            self._set_busy(False)

    def _populate(self, files: List[GeoFile]) -> None:
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self._entries = []
        self._file_by_path = {
            str(geo_file.path): geo_file for geo_file in files
        }

        try:
            for geo_file in files:
                item = self._make_item(geo_file)
                self.tree.addTopLevelItem(item)
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
            self.summary_label.setText("Файлов: 0")
            self._set_empty(
                "Файлы не найдены",
                "В выбранной папке нет поддерживаемых пространственных файлов.",
            )
            self._update_controls()
            return

        self._apply_filter()

    def _make_item(self, geo_file: GeoFile) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [
                geo_file.relative_posix,
                geo_file.format.name,
                format_size(geo_file.size),
            ]
        )
        item.setIcon(0, self._icon_for(geo_file))
        item.setData(
            0, Qt.ItemDataRole.UserRole, str(geo_file.path)
        )
        item.setToolTip(0, str(geo_file.path))
        item.setToolTip(
            1,
            CATEGORY_LABELS.get(geo_file.category, geo_file.format.name),
        )
        item.setToolTip(2, "{} Б".format(geo_file.size))
        item.setTextAlignment(
            2,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
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

    def _update_file_actions(self) -> None:
        selected = self._selected_files()
        self.info_button.setEnabled(
            len(selected) == 1 and not self._busy
        )
        self.explorer_button.setEnabled(
            bool(selected) and not self._busy
        )

    def _show_file_info(self) -> None:
        selected = self._selected_files()
        if len(selected) != 1:
            return

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
            QMessageBox.critical(
                self,
                "ZGeo",
                "Не удалось получить информацию о файле:\n{}".format(
                    error_message
                ),
            )
            return

        FileInfoDialog(file_info, self).exec()

    def _open_in_explorer(self) -> None:
        selected = self._selected_files()
        if not selected:
            return

        errors = reveal_files(
            geo_file.path for geo_file in selected
        )
        if errors:
            QMessageBox.warning(
                self,
                "ZGeo",
                "Не удалось открыть проводник:\n\n{}".format(
                    "\n".join(errors)
                ),
            )

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

        self.stats_stack.setCurrentWidget(self.stats_content_widget)

    def _clear_statistics(self, title: str, hint: str) -> None:
        self.stats_summary_label.setText("Файлов: 0 · 0 Б")
        self.size_chart.set_rows([])
        self.type_chart.set_rows([])
        self._set_stats_empty(title, hint)

    def _set_stats_empty(self, title: str, hint: str) -> None:
        self.stats_empty_title_label.setText(title)
        self.stats_empty_hint_label.setText(hint)
        self.stats_stack.setCurrentWidget(self.stats_stack.widget(0))

    # ------------------------------------------------------------------
    # Фильтрация и состояния интерфейса
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        if self._folder is None:
            return

        query = self.filter_edit.text().strip().casefold()
        visible = 0

        for item, search_text in self._entries:
            hidden = bool(query) and query not in search_text
            item.setHidden(hidden)
            if not hidden:
                visible += 1

        if not self._entries:
            self.summary_label.setText("Файлов: 0")
            self.stack.setCurrentWidget(self.stack.widget(0))
            return

        if visible:
            self.stack.setCurrentWidget(self.tree)
        else:
            self._set_empty(
                "Ничего не найдено",
                "Измените запрос или очистите строку фильтра.",
            )

        if query:
            self.summary_label.setText(
                "Показано: {} из {}".format(visible, len(self._entries))
            )
        else:
            self.summary_label.setText("Файлов: {}".format(len(self._entries)))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.summary_label.setText("Сканирование…")
            self._set_empty(
                "Сканирование папки…",
                "Ищем пространственные файлы, включая вложенные папки.",
            )
            self._set_stats_empty(
                "Сканирование…",
                "Диаграммы обновятся после завершения поиска файлов.",
            )
        self._update_controls()
        if busy:
            QApplication.processEvents()

    def _update_controls(self) -> None:
        self.choose_button.setEnabled(not self._busy)
        self.refresh_button.setEnabled(self._folder is not None and not self._busy)
        self.filter_edit.setEnabled(bool(self._files) and not self._busy)
        self._update_file_actions()

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

