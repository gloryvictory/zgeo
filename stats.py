"""Агрегация найденных файлов для вкладки статистики."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .i18n import tr
from .scanner import GeoFile

MIB = 1024 * 1024
GIB = 1024 * MIB

SIZE_BUCKETS: Tuple[Tuple[str, int, Optional[int]], ...] = (
    ("До 1 МБ", 0, MIB),
    ("1–10 МБ", MIB, 10 * MIB),
    ("10–100 МБ", 10 * MIB, 100 * MIB),
    ("100 МБ–1 ГБ", 100 * MIB, GIB),
    ("1 ГБ и более", GIB, None),
)


@dataclass(frozen=True)
class SizeBucketStat:
    label: str
    count: int
    total_size: int


@dataclass(frozen=True)
class TypeStat:
    name: str
    count: int
    total_size: int
    category: str
    formats: Tuple[str, ...] = ()


def build_size_distribution(files: Iterable[GeoFile]) -> List[SizeBucketStat]:
    """Распределить файлы по диапазонам размера."""

    counts = [0] * len(SIZE_BUCKETS)
    sizes = [0] * len(SIZE_BUCKETS)

    for geo_file in files:
        bucket_index = len(SIZE_BUCKETS) - 1
        for index, (_label, minimum, maximum) in enumerate(SIZE_BUCKETS):
            if geo_file.size >= minimum and (
                maximum is None or geo_file.size < maximum
            ):
                bucket_index = index
                break
        counts[bucket_index] += 1
        sizes[bucket_index] += geo_file.size

    return [
        SizeBucketStat(
            label=tr(label),
            count=counts[index],
            total_size=sizes[index],
        )
        for index, (label, _minimum, _maximum) in enumerate(SIZE_BUCKETS)
    ]


def build_type_distribution(
    files: Iterable[GeoFile], limit: Optional[int] = None
) -> List[TypeStat]:
    """Сгруппировать файлы по формату и отсортировать по количеству."""

    grouped: Dict[str, Dict[str, object]] = {}
    for geo_file in files:
        name = geo_file.format.name
        entry = grouped.get(name)
        if entry is None:
            entry = {
                "name": name,
                "count": 0,
                "total_size": 0,
                "category": geo_file.category,
            }
            grouped[name] = entry
        entry["count"] = int(entry["count"]) + 1
        entry["total_size"] = int(entry["total_size"]) + geo_file.size

    stats = [
        TypeStat(
            name=str(entry["name"]),
            count=int(entry["count"]),
            total_size=int(entry["total_size"]),
            category=str(entry["category"]),
            formats=(str(entry["name"]),),
        )
        for entry in grouped.values()
    ]
    stats.sort(key=lambda item: (-item.count, -item.total_size, item.name.casefold()))

    if limit is not None and limit > 0 and len(stats) > limit:
        top_count = max(0, limit - 1)
        top = stats[:top_count]
        rest = stats[top_count:]
        other = TypeStat(
            name=tr("Другие форматы"),
            count=sum(item.count for item in rest),
            total_size=sum(item.total_size for item in rest),
            category="other",
            formats=tuple(item.name for item in rest),
        )
        stats = top + [other]

    return stats
