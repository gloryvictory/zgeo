"""Определение объекта, который нужно показать для замечания качества."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .quality_check import QualityIssue

SIDECAR_SUFFIXES = (
    ".aux.xml",
    ".shp.xml",
    ".prj",
    ".cpg",
    ".dbf",
    ".tfw",
    ".tifw",
    ".wld",
    ".ovr",
)


@dataclass(frozen=True)
class NavigationTarget:
    """Куда перейти по замечанию: объект слоя, слой, файл или папка."""

    path: Path
    layer: str = ""
    feature_id: Optional[int] = None
    sidecar: Optional[Path] = None
    reveal_only: bool = False
    feature_ids_extra: Tuple[int, ...] = ()

    def feature_ids(self) -> Tuple[int, ...]:
        """Все объекты перехода: основной и дополнительные."""

        ids: List[int] = []
        for feature_id in (self.feature_id, *self.feature_ids_extra):
            if feature_id is None or feature_id in ids:
                continue
            ids.append(feature_id)
        return tuple(ids)

    @property
    def has_layer(self) -> bool:
        return bool(self.layer)

    @property
    def has_feature(self) -> bool:
        return bool(self.layer) and self.feature_id is not None


def navigation_target(
    path: Union[str, Path],
    issue: QualityIssue,
) -> NavigationTarget:
    """Определить, что открыть и выделить для одного замечания."""

    main_path = Path(path)
    sidecar = _sidecar_for(main_path, issue.location)
    if sidecar is not None:
        return NavigationTarget(main_path, sidecar=sidecar)
    if issue.layer:
        return NavigationTarget(
            main_path,
            layer=issue.layer,
            feature_id=issue.feature_id,
            feature_ids_extra=tuple(getattr(issue, "feature_ids", ()) or ()),
        )
    return NavigationTarget(main_path, reveal_only=True)


def _sidecar_for(main_path: Path, location: str) -> Optional[Path]:
    """Найти сопутствующий файл, о котором говорит замечание."""

    text = (location or "").strip()
    if not text:
        return None

    candidate_name = Path(text)
    folded_name = text.casefold()
    if (
        candidate_name.suffix
        and candidate_name.name == text
        and folded_name not in SIDECAR_SUFFIXES
        and any(
            folded_name.endswith(suffix) for suffix in SIDECAR_SUFFIXES
        )
    ):
        candidate = main_path.parent / text
        return candidate if candidate.exists() else None

    folded = text.casefold()
    for suffix in SIDECAR_SUFFIXES:
        if suffix in folded:
            candidate = _sibling_path(main_path, suffix)
            return candidate if candidate.exists() else None
    if folded == "dbf":
        candidate = _sibling_path(main_path, ".dbf")
        return candidate if candidate.exists() else None
    return None


def _sibling_path(main_path: Path, suffix: str) -> Path:
    """Собрать путь сопутствующего файла рядом с основным."""

    if suffix == ".aux.xml":
        return Path(str(main_path) + suffix)
    return main_path.with_suffix(suffix)
