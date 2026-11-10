"""Простые диаграммы для вкладки статистики.

QGIS не гарантирует наличие QtCharts, поэтому столбчатые диаграммы
рисуются стандартным QPainter и не требуют дополнительных зависимостей.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from qgis.PyQt.QtCore import QRectF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette
from qgis.PyQt.QtWidgets import QSizePolicy, QWidget

from .i18n import tr

ROW_HEIGHT = 40
BAR_HEIGHT = 8


@dataclass(frozen=True)
class BarDatum:
    label: str
    value: float
    value_text: str
    color: str
    tooltip: str = ""


class BarChart(QWidget):
    """Горизонтальная столбчатая диаграмма с подписями строк."""

    def __init__(
        self,
        rows: Optional[Iterable[BarDatum]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._rows: List[BarDatum] = []
        self._max_value = 0.0
        self._hover_row = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(tr("Столбчатая диаграмма"))
        if rows is not None:
            self.set_rows(rows)

    def set_rows(self, rows: Iterable[BarDatum]) -> None:
        self._rows = list(rows)
        self._max_value = max((row.value for row in self._rows), default=0.0)
        self._hover_row = -1
        self.setToolTip("")
        self.setFixedHeight(max(1, len(self._rows) * ROW_HEIGHT))
        self.setAccessibleDescription(
            "; ".join(
                "{}: {}".format(row.label, row.value_text)
                for row in self._rows
            )
        )
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(320, max(1, len(self._rows) * ROW_HEIGHT))

    def minimumSizeHint(self) -> QSize:
        return QSize(180, max(1, len(self._rows) * ROW_HEIGHT))

    def mouseMoveEvent(self, event) -> None:
        row_index = int(event.position().y()) // ROW_HEIGHT
        if row_index != self._hover_row:
            self._hover_row = row_index
            if 0 <= row_index < len(self._rows):
                self.setToolTip(self._rows[row_index].tooltip)
            else:
                self.setToolTip("")
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_row = -1
        self.setToolTip("")
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:
        if not self._rows:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        palette = self.palette()
        text_color = palette.color(QPalette.ColorRole.WindowText)
        track_color = palette.color(QPalette.ColorRole.Midlight)

        label_font = QFont(self.font())
        value_font = QFont(self.font())
        value_font.setBold(True)

        label_metrics = QFontMetrics(label_font)
        value_metrics = QFontMetrics(value_font)
        text_flags = int(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        right_flags = int(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        for index, row in enumerate(self._rows):
            row_top = float(index * ROW_HEIGHT)
            value_width = float(value_metrics.horizontalAdvance(row.value_text) + 12)
            label_width = max(0.0, float(self.width()) - value_width - 12.0)

            painter.setFont(label_font)
            painter.setPen(text_color)
            label_text = label_metrics.elidedText(
                row.label,
                Qt.TextElideMode.ElideRight,
                int(label_width),
            )
            painter.drawText(
                QRectF(0.0, row_top + 1.0, label_width, 18.0),
                text_flags,
                label_text,
            )

            painter.setFont(value_font)
            painter.drawText(
                QRectF(
                    float(self.width()) - value_width,
                    row_top + 1.0,
                    value_width,
                    18.0,
                ),
                right_flags,
                row.value_text,
            )

            bar_top = row_top + 25.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(track_color)
            painter.drawRoundedRect(
                QRectF(0.0, bar_top, float(self.width()), BAR_HEIGHT),
                4.0,
                4.0,
            )

            if self._max_value > 0 and row.value > 0:
                bar_width = float(self.width()) * min(1.0, row.value / self._max_value)
                painter.setBrush(QColor(row.color))
                painter.drawRoundedRect(
                    QRectF(0.0, bar_top, bar_width, BAR_HEIGHT),
                    4.0,
                    4.0,
                )

        painter.end()
