"""Регистрация ZGeo в интерфейсе QGIS."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtGui import QIcon

try:
    from qgis.PyQt.QtWidgets import QAction, QToolBar
except ImportError:  # Qt 6 / PyQt 6
    from qgis.PyQt.QtGui import QAction
    from qgis.PyQt.QtWidgets import QToolBar

from .panel import ZGeoPanel

PLUGIN_DIR = Path(__file__).resolve().parent
MENU_NAME = "&ZGeo"
TOOLBAR_NAME = "ZGeo"


class ZGeoPlugin:
    """QGIS-плагин ZGeo."""

    def __init__(self, iface) -> None:
        self.iface = iface
        self.action: Optional[QAction] = None
        self.toolbar: Optional[QToolBar] = None
        self.panel: Optional[ZGeoPanel] = None

    def initGui(self) -> None:
        icon = QIcon(str(PLUGIN_DIR / "icon.svg"))

        self._remove_stale_toolbar()

        self.action = QAction(
            icon, "ZGeo-Каталог", self.iface.mainWindow()
        )
        self.action.setObjectName("ZGeoAction")
        self.action.setCheckable(True)
        self.action.setToolTip(
            "ZGeo-Каталог — каталог пространственных данных"
        )
        self.action.setStatusTip(
            "Открыть плавающую панель ZGeo-Каталог"
        )
        self.action.triggered.connect(self._toggle_panel)

        self.toolbar = QToolBar(TOOLBAR_NAME, self.iface.mainWindow())
        self.toolbar.setObjectName("ZGeoToolbar")
        self.toolbar.addAction(self.action)
        self._add_toolbar()

        self.iface.addPluginToMenu(MENU_NAME, self.action)
        add_toolbar_icon = getattr(self.iface, "addToolBarIcon", None)
        if callable(add_toolbar_icon):
            add_toolbar_icon(self.action)

        # QGIS восстанавливает состояние главного окна после загрузки
        # плагинов и может скрыть только что созданную панель.
        QTimer.singleShot(0, self._ensure_toolbar_visible)
        QTimer.singleShot(750, self._ensure_toolbar_visible)
        QTimer.singleShot(2500, self._ensure_toolbar_visible)

    def unload(self) -> None:
        if self.panel is not None:
            try:
                self.panel.visibilityChanged.disconnect(
                    self._on_panel_visibility_changed
                )
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

    def _remove_stale_toolbar(self) -> None:
        """Убрать панель, оставшуюся после перезагрузки плагина."""

        main_window = self.iface.mainWindow()
        stale = main_window.findChild(QToolBar, "ZGeoToolbar")
        if stale is not None and stale is not self.toolbar:
            main_window.removeToolBar(stale)
            stale.deleteLater()

    def _ensure_toolbar_visible(self) -> None:
        if self.toolbar is None:
            return
        try:
            if self.toolbar.parentWidget() is None:
                self._add_toolbar()
            self.toolbar.show()
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

    def _on_panel_visibility_changed(self, visible: bool) -> None:
        if self.action is not None and self.action.isChecked() != visible:
            self.action.setChecked(visible)

    def _on_panel_destroyed(self, _object=None) -> None:
        self.panel = None
        if self.action is not None:
            self.action.setChecked(False)
