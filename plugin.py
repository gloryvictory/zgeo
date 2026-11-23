"""Регистрация ZGeo в интерфейсе QGIS."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Tuple

from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTimer, Qt
from qgis.PyQt.QtGui import QIcon

try:
    from qgis.PyQt.QtWidgets import QAction, QToolBar
except ImportError:  # Qt 6 / PyQt 6
    from qgis.PyQt.QtGui import QAction
    from qgis.PyQt.QtWidgets import QToolBar

from .i18n import LANGUAGE_KEY, set_language, tr
from .panel import ZGeoPanel

PLUGIN_DIR = Path(__file__).resolve().parent
MENU_NAME = "&ZGeo"
TOOLBAR_NAME = "ZGeo"
TOOLBAR_OBJECT_NAME = "ZGeoToolbar"
STARTUP_CHECKS_MS = (0, 400, 1200, 2500, 5000, 9000, 15000, 30000)
TOOLBAR_VISIBLE_KEY = "zgeo/toolbar_visible"
STARTUP_GRACE_SECONDS = 10.0
DETACHED_OBJECT_NAME = ""


def _find_live_toolbar(main_window) -> Optional[QToolBar]:
    """Найти панель ZGeo, которую восстановил QGIS при запуске."""

    for candidate in main_window.findChildren(QToolBar):
        try:
            if candidate.objectName() != TOOLBAR_OBJECT_NAME:
                continue
            if candidate.parentWidget() is None:
                continue
        except RuntimeError:
            continue
        return candidate
    return None

class ZGeoPlugin:
    """QGIS-плагин ZGeo."""

    def __init__(self, iface) -> None:
        self.iface = iface
        self._settings = QSettings()
        set_language(self._settings.value(LANGUAGE_KEY, "ru"))
        self.action: Optional[QAction] = None
        self.toolbar: Optional[QToolBar] = None
        self.panel: Optional[ZGeoPanel] = None
        self._startup_signals: List[Tuple[object, object]] = []
        self._shutting_down = False
        self._quit_connected = False
        self._startup_grace_until = 0.0

    def initGui(self) -> None:
        icon = QIcon(str(PLUGIN_DIR / "icon.svg"))

        self._shutting_down = False
        self._startup_grace_until = time.monotonic() + STARTUP_GRACE_SECONDS
        self._connect_quit_signal()

        self.action = QAction(
            icon, tr("ZGeo-Каталог"), self.iface.mainWindow()
        )
        self.action.setObjectName("ZGeoAction")
        self.action.setCheckable(True)
        self.action.setToolTip(
            tr("ZGeo-Каталог — каталог пространственных данных")
        )
        self.action.setStatusTip(
            tr("Открыть плавающую панель ZGeo-Каталог")
        )
        self.action.triggered.connect(self._toggle_panel)

        self.toolbar = self._build_toolbar()
        self._add_toolbar()
        self._restore_toolbar_visibility()

        self.iface.addPluginToMenu(MENU_NAME, self.action)
        add_toolbar_icon = getattr(self.iface, "addToolBarIcon", None)
        if callable(add_toolbar_icon):
            add_toolbar_icon(self.action)

        # QGIS восстанавливает состояние главного окна и загружает проект
        # уже после initGui, поэтому панель инструментов может исчезнуть.
        # Проверяем её несколько раз и по сигналам готовности QGIS.
        self._schedule_startup_checks()
        self._connect_startup_signals()

    def unload(self) -> None:
        self._disconnect_startup_signals()
        self._disconnect_quit_signal()
        self._shutting_down = True
        if self.toolbar is not None:
            try:
                self.toolbar.visibilityChanged.disconnect(
                    self._on_toolbar_visibility_changed
                )
            except (TypeError, RuntimeError):
                pass
        if self.panel is not None:
            for signal, slot in (
                (
                    self.panel.visibilityChanged,
                    self._on_panel_visibility_changed,
                ),
                (self.panel.language_changed, self._on_language_changed),
            ):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass

            try:
                self.iface.mainWindow().removeDockWidget(self.panel)
            except (TypeError, RuntimeError):
                pass
            try:
                self.panel.shutdown()
                self.panel.close()
                self.panel.deleteLater()
            except (TypeError, RuntimeError):
                pass
            self.panel = None

        if self.toolbar is not None:
            try:
                self._remove_toolbar()
            except (TypeError, RuntimeError):
                pass
            try:
                # Имя снимается, чтобы следующий initGui не подхватил
                # панель, уже запланированную к удалению.
                self.toolbar.setObjectName(DETACHED_OBJECT_NAME)
            except RuntimeError:
                pass
            self.toolbar.deleteLater()
            self.toolbar = None

        if self.action is not None:
            remove_toolbar_icon = getattr(
                self.iface, "removeToolBarIcon", None
            )
            if callable(remove_toolbar_icon):
                try:
                    remove_toolbar_icon(self.action)
                except (TypeError, RuntimeError):
                    pass
            try:
                self.iface.removePluginMenu(MENU_NAME, self.action)
            except (TypeError, RuntimeError):
                pass
            try:
                self.action.deleteLater()
            except (TypeError, RuntimeError):
                pass
            self.action = None

    def _connect_quit_signal(self) -> None:
        """Отметить начало завершения QGIS, чтобы не портить настройки."""

        if self._quit_connected:
            return
        application = QCoreApplication.instance()
        quit_signal = getattr(application, "aboutToQuit", None)
        connect = getattr(quit_signal, "connect", None)
        if not callable(connect):
            return
        try:
            connect(self._on_about_to_quit)
        except (TypeError, RuntimeError):
            return
        self._quit_connected = True

    def _disconnect_quit_signal(self) -> None:
        if not self._quit_connected:
            return
        application = QCoreApplication.instance()
        quit_signal = getattr(application, "aboutToQuit", None)
        disconnect = getattr(quit_signal, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect(self._on_about_to_quit)
            except (TypeError, RuntimeError):
                pass
        self._quit_connected = False

    def _on_about_to_quit(self) -> None:
        """QGIS закрывается: скрытие панели при выгрузке не сохраняем."""

        self._shutting_down = True
    def _schedule_startup_checks(self) -> None:
        """Проверить панель инструментов после запуска QGIS."""

        for delay in STARTUP_CHECKS_MS:
            QTimer.singleShot(delay, self._ensure_toolbar_visible)

    def _connect_startup_signals(self) -> None:
        """Повторно показать панель, когда QGIS завершит запуск."""

        candidates = []
        initialization = getattr(
            self.iface, "initializationCompleted", None
        )
        if initialization is not None:
            candidates.append(initialization)
        try:
            from qgis.core import QgsProject

            candidates.append(QgsProject.instance().projectRead)
        except Exception:
            pass

        for signal in candidates:
            connect = getattr(signal, "connect", None)
            if not callable(connect):
                continue
            try:
                connect(self._ensure_toolbar_visible)
            except (TypeError, RuntimeError):
                continue
            self._startup_signals.append((signal, self._ensure_toolbar_visible))

    def _disconnect_startup_signals(self) -> None:
        for signal, slot in self._startup_signals:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._startup_signals = []

    def _add_toolbar(self) -> None:
        add_toolbar = getattr(self.iface, "addToolBar", None)
        if callable(add_toolbar):
            add_toolbar(self.toolbar)
        else:
            self.iface.mainWindow().addToolBar(self.toolbar)
        self.toolbar.show()

    def _remove_toolbar(self) -> None:
        if self.toolbar is None:
            return
        remove_toolbar = getattr(self.iface, "removeToolBar", None)
        if callable(remove_toolbar):
            remove_toolbar(self.toolbar)
        else:
            self.iface.mainWindow().removeToolBar(self.toolbar)

    def _build_toolbar(self) -> QToolBar:
        """Создать панель или заполнить восстановленную QGIS.

        При запуске QGIS восстанавливает раскладку главного окна и создаёт
        панель с нашим именем объекта. Её нельзя удалять: удаление оставляет
        пустое место и сбивает восстановление, поэтому панель переиспользуется.
        """

        main_window = self.iface.mainWindow()
        toolbar = _find_live_toolbar(main_window)
        if toolbar is None:
            toolbar = QToolBar(TOOLBAR_NAME, main_window)
            toolbar.setObjectName(TOOLBAR_OBJECT_NAME)
        toolbar.setAllowedAreas(
            Qt.ToolBarArea.TopToolBarArea
            | Qt.ToolBarArea.BottomToolBarArea
            | Qt.ToolBarArea.LeftToolBarArea
            | Qt.ToolBarArea.RightToolBarArea
        )
        try:
            toolbar.clear()
            toolbar.addAction(self.action)
        except RuntimeError:
            pass
        try:
            toolbar.visibilityChanged.connect(
                self._on_toolbar_visibility_changed
            )
        except (TypeError, RuntimeError):
            pass
        return toolbar

    def _toolbar_preference(self) -> bool:
        """Показывать ли панель по сохранённой настройке."""

        value = self._settings.value(TOOLBAR_VISIBLE_KEY, True)
        if isinstance(value, str):
            return value.strip().casefold() not in ("", "false", "0")
        return bool(value)

    def _restore_toolbar_visibility(self) -> None:
        """Применить сохранённое предпочтение видимости панели."""

        if self.toolbar is None:
            return
        try:
            self.toolbar.setVisible(self._toolbar_preference())
        except RuntimeError:
            pass

    def _on_toolbar_visibility_changed(self, visible: bool) -> None:
        """Запомнить выбор пользователя, но не скрытие при выходе."""

        if self._shutting_down:
            return
        if time.monotonic() < self._startup_grace_until:
            # QGIS восстанавливает раскладку и прячет панель сам — это не
            # выбор пользователя, сохранять его нельзя.
            return
        self._settings.setValue(TOOLBAR_VISIBLE_KEY, bool(visible))

    def _ensure_toolbar_visible(self) -> None:
        """Вернуть панель инструментов на место, если QGIS её скрыл."""

        if self.toolbar is None or self._shutting_down:
            return
        if not self._toolbar_preference():
            return
        try:
            if self.toolbar.parentWidget() is None:
                self._add_toolbar()
            if self.toolbar.isHidden():
                self.toolbar.show()
            if self.action is not None and not self.action.isVisible():
                self.action.setVisible(True)
        except RuntimeError:
            # Виджет уже удалён при выгрузке плагина.
            pass

    def _toggle_panel(self, checked: bool) -> None:
        if checked:
            self._show_panel()
        elif self.panel is not None:
            self.panel.hide()

    def _show_panel(self) -> None:
        if self.panel is None:
            self.panel = ZGeoPanel(self.iface.mainWindow())
            self.panel.visibilityChanged.connect(
                self._on_panel_visibility_changed
            )
            self.panel.language_changed.connect(
                self._on_language_changed
            )
            self.panel.destroyed.connect(self._on_panel_destroyed)
            self.iface.mainWindow().addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self.panel
            )
            self.panel.setFloating(True)

        if self.panel.isMinimized():
            self.panel.showNormal()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

        if self.action is not None:
            self.action.setChecked(True)

    def _on_language_changed(self, _language: str) -> None:
        if self.action is None:
            return
        self.action.setText(tr("ZGeo-Каталог"))
        self.action.setToolTip(
            tr("ZGeo-Каталог — каталог пространственных данных")
        )
        self.action.setStatusTip(
            tr("Открыть плавающую панель ZGeo-Каталог")
        )

    def _on_panel_visibility_changed(self, visible: bool) -> None:
        if self.action is not None and self.action.isChecked() != visible:
            self.action.setChecked(visible)

    def _on_panel_destroyed(self, _object=None) -> None:
        self.panel = None
        if self.action is not None:
            self.action.setChecked(False)
