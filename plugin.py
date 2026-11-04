"""Регистрация ZGeo в интерфейсе QGIS."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

try:
    from qgis.PyQt.QtWidgets import QAction
except ImportError:  # Qt 6 / PyQt 6
    from qgis.PyQt.QtGui import QAction

from .panel import ZGeoPanel

PLUGIN_DIR = Path(__file__).resolve().parent
MENU_NAME = "&ZGeo"


class ZGeoPlugin:
    """QGIS-плагин ZGeo."""

    def __init__(self, iface) -> None:
        self.iface = iface
        self.action: Optional[QAction] = None
        self.panel: Optional[ZGeoPanel] = None

    def initGui(self) -> None:
        icon = QIcon(str(PLUGIN_DIR / "icon.svg"))

        self.action = QAction(icon, "ZGeo", self.iface.mainWindow())
        self.action.setObjectName("ZGeoAction")
        self.action.setCheckable(True)
        self.action.setToolTip("ZGeo — каталог пространственных данных")
        self.action.setStatusTip("Открыть плавающую панель ZGeo")
        self.action.triggered.connect(self._toggle_panel)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU_NAME, self.action)

    def unload(self) -> None:
        if self.panel is not None:
            try:
                self.panel.visibilityChanged.disconnect(
                    self._on_panel_visibility_changed
                )
            except (TypeError, RuntimeError):
                pass

            self.iface.mainWindow().removeDockWidget(self.panel)
            self.panel.close()
            self.panel.deleteLater()
            self.panel = None

        if self.action is not None:
            self.iface.removePluginMenu(MENU_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

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
