"""Переход из отчёта о качестве к слою, объекту или файлу."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from .explorer import open_file, open_folder, reveal_files
from .i18n import tr
from .issue_navigation import NavigationTarget, navigation_target
from .project_loader import ensure_file_layer
from .quality_check import QualityIssue
from .scanner import GeoFile, get_format

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NavigationOutcome:
    """Результат перехода и сообщение для строки состояния."""

    ok: bool
    message: str


@dataclass
class _LayerGroup:
    """Слой и объекты, которые нужно показать в нём."""

    path: Path
    layer: str
    feature_ids: List[int] = field(default_factory=list)


def navigate_to_issue(
    path: Union[str, Path],
    issue: QualityIssue,
    iface: Optional[Any] = None,
    feature_ids: Optional[Sequence[int]] = None,
) -> NavigationOutcome:
    """Открыть и выделить объект замечания либо показать его файл."""

    target = navigation_target(path, issue)
    if target.sidecar is not None:
        return _open_sidecar(target.sidecar)

    ids = _feature_ids(target, feature_ids)
    if target.has_layer:
        layer, error = _ensure_layer(target.path, target.layer)
        if layer is None:
            outcome = _reveal(target.path)
            if outcome.ok:
                return outcome
            reason = error or outcome.message
            return NavigationOutcome(
                False,
                tr(
                    "Не удалось открыть слой «{}»: {}",
                    target.layer,
                    reason,
                ),
            )
        return _focus_layer(layer, ids, iface)

    return _reveal(target.path)


def load_and_show(
    entries: Iterable[Any],
    iface: Optional[Any] = None,
) -> NavigationOutcome:
    """Загрузить слои замечаний в проект и выделить только их объекты.

    На вход подаются записи с полями path и issue. Объекты из одной ячейки
    отчёта выделяются вместе: прежнее выделение слоя снимается, поэтому на
    карте остаются только проблемные объекты. Файловые замечания без
    объектов пропускаются: проводник и папки эта команда не открывает,
    единственное исключение — файл .prj, который открывается как документ.
    """

    groups: Dict[Any, _LayerGroup] = {}
    order: List[Any] = []
    shown_layers = 0
    selected = 0
    reopened = 0
    skipped = 0
    errors: List[str] = []

    for entry in entries:
        target = navigation_target(entry.path, entry.issue)
        if target.sidecar is not None:
            if _open_prj(target.sidecar):
                reopened += 1
            else:
                skipped += 1
            continue

        if not target.has_layer:
            skipped += 1
            continue

        key = (str(target.path), target.layer.casefold())
        group = groups.get(key)
        if group is None:
            group = _LayerGroup(path=target.path, layer=target.layer)
            groups[key] = group
            order.append(key)
        for feature_id in target.feature_ids():
            group.feature_ids.append(feature_id)

    for key in order:
        group = groups[key]
        layer, error = _ensure_layer(group.path, group.layer)
        if layer is None:
            errors.append(
                tr(
                    "Не удалось открыть слой «{}»: {}",
                    group.layer,
                    error or "",
                )
            )
            continue

        outcome = _focus_layer(layer, group.feature_ids, iface)
        if outcome.ok:
            shown_layers += 1
            selected += len(set(group.feature_ids))
        else:
            errors.append(outcome.message)

    if errors and not shown_layers and not reopened:
        return NavigationOutcome(False, errors[0])

    parts: List[str] = []
    if shown_layers:
        parts.append(
            tr(
                "Загружено слоёв: {} · выбрано объектов: {}",
                shown_layers,
                selected,
            )
        )
    if reopened:
        parts.append(tr("Открыто файлов: {}", reopened))
    if skipped:
        parts.append(
            tr("Пропущено замечаний без объектов: {}", skipped)
        )
    if errors:
        parts.append(tr("Ошибок: {}", len(errors)))
    if not parts:
        return NavigationOutcome(
            False, tr("В выбранной ячейке нет объектов для показа")
        )
    return NavigationOutcome(True, " · ".join(parts))


def _feature_ids(
    target: NavigationTarget,
    feature_ids: Optional[Sequence[int]],
) -> List[int]:
    """Собрать список объектов для выделения."""

    if feature_ids:
        return list(dict.fromkeys(feature_ids))
    return list(target.feature_ids())


def _ensure_layer(path: Path, layer_name: str) -> Any:
    """Загрузить слой файла, если он ещё не добавлен в проект."""

    format_info = get_format(path)
    if format_info is None:
        return None, ""
    geo_file = GeoFile(
        path=path,
        relative_path=Path(path.name),
        format=format_info,
        size=path.stat().st_size if path.exists() else 0,
    )
    return ensure_file_layer(geo_file, layer_name)


def select_only(layer: Any, feature_ids: Sequence[int]) -> int:
    """Выделить только перечисленные объекты, сняв прежнее выделение."""

    if not isinstance(layer, QgsVectorLayer):
        return 0
    ids = list(dict.fromkeys(feature_ids))
    try:
        layer.removeSelection()
        if not ids:
            return 0
        layer.selectByIds(ids)
        selected = set(layer.selectedFeatureIds())
    except Exception:
        return 0
    return len(selected & set(ids))


def _focus_layer(
    layer: Any,
    feature_ids: Union[int, Sequence[int], None] = None,
    iface: Optional[Any] = None,
) -> NavigationOutcome:
    """Выделить объекты, приблизить карту и открыть таблицу атрибутов."""

    if isinstance(feature_ids, int):
        ids = [feature_ids]
    elif feature_ids is None:
        ids = []
    else:
        ids = [feature_id for feature_id in feature_ids]

    active_iface = _resolve_iface(iface)
    _call_if_any(active_iface, "setActiveLayer", layer)

    selected = select_only(layer, ids) if ids else 0

    canvas = _map_canvas(active_iface)
    if canvas is not None:
        _ensure_canvas_layer(canvas, layer)
        _zoom_to_layer(canvas, layer, ids)

    if isinstance(layer, QgsVectorLayer):
        _call_if_any(active_iface, "showAttributeTable", layer)

    if selected:
        return NavigationOutcome(
            True,
            tr(
                "Открыт слой «{}», выбрано объектов: {}",
                layer.name(),
                selected,
            ),
        )
    if ids:
        return NavigationOutcome(
            True,
            tr(
                "Объекты не найдены, показан весь слой «{}»",
                layer.name(),
            ),
        )
    return NavigationOutcome(
        True,
        tr("Открыт слой «{}»", layer.name()),
    )


def _call_if_any(target: Any, name: str, *args) -> bool:
    """Вызвать метод интерфейса QGIS, если он есть и не падает."""

    if target is None:
        return False
    method = getattr(target, name, None)
    if not callable(method):
        return False
    try:
        method(*args)
    except Exception:
        return False
    return True


def _ensure_canvas_layer(canvas: Any, layer: Any) -> bool:
    """Показать слой на карте, если его нет в наборе слоёв карты.

    QgsProject.addMapLayer добавляет слой в дерево, но набор слоёв карты
    может остаться прежним, и тогда на карте ничего не появляется.
    """

    if canvas is None or layer is None:
        return False
    try:
        current = list(canvas.layers())
    except Exception:
        return False
    if layer in current:
        return True
    set_layers = getattr(canvas, "setLayers", None)
    if not callable(set_layers):
        return False
    try:
        set_layers(current + [layer])
    except Exception:
        return False
    return True

def _zoom_to_layer(
    canvas: Any,
    layer: Any,
    feature_ids: Sequence[int],
) -> bool:
    """Приблизить карту к объектам, учитывая систему координат проекта.

    Сначала используется встроенный zoomToFeatureIds — он сам пересчитывает
    охват в систему координат карты. Если его нет, охват переводится в СК
    карты вручную, иначе при несовпадении СК карта уезжает в пустое место.
    """

    zoomed = False
    if feature_ids:
        zoom_to_ids = getattr(canvas, "zoomToFeatureIds", None)
        if callable(zoom_to_ids):
            try:
                zoom_to_ids(layer, list(feature_ids))
                zoomed = True
            except Exception:
                zoomed = False

    if not zoomed:
        extent = None
        source_crs = None
        if feature_ids:
            extent = _features_extent(layer, feature_ids)
        if extent is None and isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
            try:
                layer_extent = layer.extent()
            except Exception:
                layer_extent = None
            if layer_extent is not None and not layer_extent.isEmpty():
                extent = QgsRectangle(layer_extent)
        if extent is not None:
            try:
                source_crs = layer.crs()
            except Exception:
                source_crs = None
            extent = _extent_in_canvas_crs(extent, source_crs, canvas)
            if extent is not None:
                try:
                    canvas.setExtent(extent)
                    zoomed = True
                except Exception:
                    zoomed = False

    refresh = getattr(canvas, "refresh", None)
    if callable(refresh):
        try:
            refresh()
        except Exception:
            _LOGGER.debug("Could not refresh the map canvas", exc_info=True)
    return zoomed


def _extent_in_canvas_crs(
    extent: Any,
    source_crs: Any,
    canvas: Any,
):
    """Пересчитать охват в систему координат карты."""

    try:
        settings = canvas.mapSettings()
        destination = settings.destinationCrs()
    except Exception:
        destination = None
    if destination is None or not destination.isValid():
        return extent
    if source_crs is None or not source_crs.isValid():
        return extent
    if source_crs == destination:
        return extent
    try:
        transform = QgsCoordinateTransform(
            source_crs,
            destination,
            QgsProject.instance().transformContext(),
        )
        return transform.transformBoundingBox(extent)
    except Exception:
        return extent


def _features_extent(layer: Any, feature_ids: Sequence[int]):
    """Собрать общий охват перечисленных объектов."""

    if not feature_ids or not isinstance(layer, QgsVectorLayer):
        return None
    try:
        bbox = layer.boundingBoxOfSelected()
    except Exception:
        bbox = None
    if bbox is not None and not bbox.isEmpty():
        return QgsRectangle(bbox)

    union = None
    try:
        request = QgsFeatureRequest().setFilterFids(list(feature_ids))
        for feature in layer.getFeatures(request):
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            feature_box = geometry.boundingBox()
            if union is None:
                union = QgsRectangle(feature_box)
            else:
                union.combineExtentWith(feature_box)
    except Exception:
        return None
    if union is not None and union.isEmpty():
        return None
    return union

def _map_canvas(iface: Optional[Any]) -> Optional[Any]:
    if iface is None:
        return None
    canvas_getter = getattr(iface, "mapCanvas", None)
    if not callable(canvas_getter):
        return None
    return canvas_getter()


def _resolve_iface(iface: Optional[Any]) -> Optional[Any]:
    """Взять переданный интерфейс или глобальный интерфейс QGIS."""

    if iface is not None:
        return iface
    try:
        from qgis.utils import iface as qgis_iface
    except Exception:
        return None
    return qgis_iface


def _open_prj(path: Path) -> bool:
    """Открыть .prj как документ; остальные файлы не трогать.

    Команда «Загрузить в текущий проект и показать на карте» не должна
    открывать проводник, поэтому сопутствующие файлы пропускаются.
    """

    if not path.name.casefold().endswith(".prj"):
        return False
    return not open_file(path)

def _open_sidecar(path: Path) -> NavigationOutcome:
    """Открыть .prj в программе по умолчанию, остальные — в проводнике."""

    if path.name.casefold().endswith(".prj"):
        errors = open_file(path)
        if not errors:
            return NavigationOutcome(
                True, tr("Открыт файл: {}", path.name)
            )
    return _reveal(path)


def _reveal(path: Path) -> NavigationOutcome:
    """Показать файл в проводнике или открыть его папку."""

    if path.exists() and path.is_file():
        errors = reveal_files([path])
        if not errors:
            return NavigationOutcome(
                True, tr("Файл показан в проводнике: {}", path.name)
            )
    folder = path if path.is_dir() else path.parent
    if not folder.exists():
        return NavigationOutcome(
            False, tr("Не удалось открыть: {}", path)
        )

    errors = open_folder(folder)
    if errors:
        return NavigationOutcome(False, tr("Не удалось открыть: {}", path))
    return NavigationOutcome(True, tr("Открыта папка: {}", folder))
